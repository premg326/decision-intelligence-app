from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import settings


# ============================================================
# SHADOW — DECISION PARSER
# ============================================================

SYSTEM_PROMPT = """
You are SHADOW, a decision-intelligence engine.

Convert the user's decision into a SMALL, SEMANTIC dependency model.

Return ONLY valid JSON.

FORMAT:

{
  "action": "string",
  "objective": "string or null",
  "domain": "string or null",

  "entities": [
    {
      "id": "stable_id",
      "name": "meaningful concept",
      "kind": "semantic type",
      "attributes": {
        "source": "decision|context|objective|inferred",
        "confidence": 0.0,
        "uncertainty": 0.0
      }
    }
  ],

  "relationships": [
    {
      "source": "entity_id",
      "target": "entity_id",
      "relation": "causes|influences|increases|decreases|depends_on|constrains|exposes|supports|affects",
      "weight": 0.0,
      "confidence": 0.0
    }
  ],

  "assumptions": [
    {
      "id": "assumption_id",
      "statement": "assumption",
      "value": null,
      "confidence": 0.0,
      "sensitivity": 0.0
    }
  ],

  "constraints": [],
  "variables": {}
}

RULES:

1. NEVER split sentences into individual words.

BAD:
considering -> opening -> second -> branch -> coffee -> shop

GOOD:
Open second coffee shop branch
Coffee shop
Customer demand
Revenue
Rent

2. The primary decision MUST be one entity.

3. Only create entities that are explicitly present or strongly implied
by the supplied decision/context.

4. Do NOT invent:
- prices
- percentages
- locations
- employee counts
- revenue
- probabilities
- dates
- market sizes

unless supplied by the user.

5. Numeric variables may ONLY be extracted when explicitly supplied.

6. Relationships must describe REAL semantic relationships in the
supplied scenario.

7. Do NOT create relationships simply because two entities exist.

8. Do NOT connect every entity to every other entity.

9. Prefer 3-8 useful entities.

10. Relationship direction matters.

Example:

Opening a second branch
    -> affects -> Customer demand

Customer demand
    -> influences -> Revenue

Rent
    -> increases_exposure -> Revenue

11. Use relationship weight between 0.1 and 1.0.

12. Confidence represents how strongly the supplied text supports
the relationship.

13. If a relationship is uncertain, lower confidence rather than
inventing certainty.

14. Unknown information remains unknown.

15. Keep assumptions separate from facts.

16. Return ONLY JSON.
"""


# ============================================================
# TEXT HELPERS
# ============================================================

def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        parts = []

        for key, item in value.items():
            if item is None:
                continue

            if isinstance(item, (dict, list)):
                parts.append(
                    f"{key}: {json.dumps(item, ensure_ascii=False)}"
                )
            else:
                parts.append(f"{key}: {item}")

        return " ".join(parts).strip()

    if isinstance(value, list):
        return " ".join(str(x) for x in value).strip()

    return str(value).strip()


def _clean_json(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    text = value.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        text = text[start:end + 1]

    return text.strip()


def _slug(value: str) -> str:
    value = value.lower().strip()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    value = re.sub(
        r"_+",
        "_",
        value,
    )

    return value.strip("_")[:60] or "entity"


def _normalise_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def _clamp(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return minimum

    return max(
        minimum,
        min(maximum, number),
    )


# ============================================================
# ENTITY NORMALISATION
# ============================================================

def _normalise_entities(
    entities: Any,
) -> list[dict[str, Any]]:

    if not isinstance(entities, list):
        return []

    result = []
    seen = set()
    used_ids = set()

    for index, raw in enumerate(entities):

        if not isinstance(raw, dict):
            continue

        name = _normalise_name(
            raw.get("name")
        )

        if not name:
            continue

        if len(name) > 100:
            name = name[:97].rstrip() + "..."

        key = re.sub(
            r"\s+",
            " ",
            name.lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        kind = _normalise_name(
            raw.get("kind")
        ).lower()

        if not kind:
            kind = "concept"

        entity_id = _normalise_name(
            raw.get("id")
        )

        if not entity_id:
            entity_id = _slug(name)

        base_id = entity_id
        counter = 2

        while entity_id in used_ids:
            entity_id = f"{base_id}_{counter}"
            counter += 1

        used_ids.add(entity_id)

        attributes = raw.get("attributes")

        if not isinstance(attributes, dict):
            attributes = {}

        attributes = dict(attributes)

        attributes["confidence"] = _clamp(
            attributes.get("confidence", 0.7)
        )

        attributes["uncertainty"] = _clamp(
            attributes.get("uncertainty", 0.3)
        )

        result.append(
            {
                "id": entity_id,
                "name": name,
                "kind": kind,
                "attributes": attributes,
            }
        )

    return result


# ============================================================
# RELATIONSHIP NORMALISATION
# ============================================================

VALID_RELATIONS = {
    "causes",
    "influences",
    "increases",
    "decreases",
    "depends_on",
    "constrains",
    "exposes",
    "supports",
    "affects",
}


def _normalise_relationships(
    relationships: Any,
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not isinstance(relationships, list):
        return []

    valid_ids = {
        entity["id"]
        for entity in entities
    }

    result = []
    seen = set()

    for raw in relationships:

        if not isinstance(raw, dict):
            continue

        source = _normalise_name(
            raw.get("source")
        )

        target = _normalise_name(
            raw.get("target")
        )

        relation = _normalise_name(
            raw.get("relation")
        ).lower()

        if (
            not source
            or not target
            or source == target
            or source not in valid_ids
            or target not in valid_ids
        ):
            continue

        if relation not in VALID_RELATIONS:
            continue

        key = (
            source,
            target,
            relation,
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "weight": round(
                    _clamp(
                        raw.get("weight", 0.5),
                        0.1,
                        1.0,
                    ),
                    3,
                ),
                "confidence": round(
                    _clamp(
                        raw.get("confidence", 0.6)
                    ),
                    3,
                ),
            }
        )

    return result


# ============================================================
# ASSUMPTIONS
# ============================================================

def _normalise_assumptions(
    assumptions: Any,
) -> list[dict[str, Any]]:

    if not isinstance(assumptions, list):
        return []

    result = []

    for index, raw in enumerate(assumptions):

        if not isinstance(raw, dict):
            continue

        statement = _normalise_name(
            raw.get("statement")
        )

        if not statement:
            continue

        result.append(
            {
                "id": (
                    _normalise_name(raw.get("id"))
                    or f"assumption_{index + 1}"
                ),
                "statement": statement,
                "value": raw.get("value"),
                "confidence": round(
                    _clamp(
                        raw.get("confidence", 0.5)
                    ),
                    3,
                ),
                "sensitivity": round(
                    _clamp(
                        raw.get("sensitivity", 0.5)
                    ),
                    3,
                ),
            }
        )

    return result


# ============================================================
# VARIABLES
# ============================================================

def _normalise_variables(
    variables: Any,
) -> dict[str, float]:

    if not isinstance(variables, dict):
        return {}

    result = {}

    for key, value in variables.items():

        clean_key = _slug(
            str(key)
        )

        if not clean_key:
            continue

        try:
            number = float(value)
        except (TypeError, ValueError):
            continue

        if not (-1e15 < number < 1e15):
            continue

        result[clean_key] = number

    return result


# ============================================================
# CONSTRAINTS
# ============================================================

def _normalise_constraints(
    constraints: Any,
) -> list[str]:

    if not isinstance(constraints, list):
        return []

    result = []
    seen = set()

    for value in constraints:

        text = _normalise_name(value)

        if not text:
            continue

        key = text.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    return result


# ============================================================
# AI RESULT NORMALISATION
# ============================================================

def _normalise_ai_result(
    raw: Any,
    req: Any,
) -> dict[str, Any] | None:

    if not isinstance(raw, dict):
        return None

    action = _normalise_name(
        raw.get("action")
    )

    if not action:
        action = _text(
            getattr(req, "decision", "")
        )

    objective = raw.get("objective")

    if objective is not None:
        objective = (
            _normalise_name(objective)
            or None
        )

    domain = raw.get("domain")

    if domain is not None:
        domain = (
            _normalise_name(domain)
            or None
        )

    entities = _normalise_entities(
        raw.get("entities")
    )

    if not entities:
        return None

    relationships = _normalise_relationships(
        raw.get("relationships"),
        entities,
    )

    assumptions = _normalise_assumptions(
        raw.get("assumptions")
    )

    constraints = _normalise_constraints(
        raw.get("constraints")
    )

    variables = _normalise_variables(
        raw.get("variables")
    )

    # Preserve variables explicitly supplied by the user.
    request_variables = getattr(
        req,
        "variables",
        {},
    )

    if isinstance(request_variables, dict):

        for key, value in request_variables.items():

            try:
                variables[_slug(str(key))] = float(value)
            except (TypeError, ValueError):
                pass

    # --------------------------------------------------------
    # Store relationships inside entity attributes.
    #
    # Current schemas.py does not yet have a top-level
    # relationships field, so this keeps the response compatible.
    # --------------------------------------------------------

    relation_map = {
        entity["id"]: []
        for entity in entities
    }

    for relationship in relationships:

        relation_map[
            relationship["source"]
        ].append(
            {
                "target": relationship["target"],
                "relation": relationship["relation"],
                "weight": relationship["weight"],
                "confidence": relationship["confidence"],
            }
        )

    for entity in entities:

        entity["attributes"] = {
            **entity.get("attributes", {}),
            "relationships": relation_map.get(
                entity["id"],
                [],
            ),
        }

    return {
        "action": action,
        "objective": objective,
        "domain": domain,
        "entities": entities,
        "assumptions": assumptions,
        "constraints": constraints,
        "variables": variables,
    }


# ============================================================
# AI REQUEST
# ============================================================

async def parse_ai(req):

    api_key = _text(
        getattr(
            settings,
            "ai_api_key",
            None,
        )
    )

    if not api_key:
        return None

    base_url = _text(
        getattr(
            settings,
            "ai_base_url",
            "",
        )
    )

    model = _text(
        getattr(
            settings,
            "ai_model",
            "",
        )
    )

    if not base_url or not model:
        return None

    request_payload = {
        "decision": _text(
            getattr(req, "decision", "")
        ),
        "objective": (
            _text(
                getattr(req, "objective", None)
            )
            or None
        ),
        "domain": (
            _text(
                getattr(req, "domain", None)
            )
            or None
        ),
        "context": (
            getattr(req, "context", {})
            or {}
        ),
        "constraints": (
            getattr(req, "constraints", [])
            or []
        ),
        "variables": (
            getattr(req, "variables", {})
            or {}
        ),
    }

    payload = {
        "model": model,
        "temperature": 0.05,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    request_payload,
                    ensure_ascii=False,
                ),
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=60.0,
                write=30.0,
                pool=10.0,
            )
        ) as client:

            response = await client.post(
                base_url.rstrip("/")
                + "/chat/completions",
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

            choices = data.get(
                "choices"
            )

            if (
                not isinstance(choices, list)
                or not choices
            ):
                return None

            message = choices[0].get(
                "message",
                {},
            )

            if not isinstance(
                message,
                dict,
            ):
                return None

            content = message.get(
                "content"
            )

            cleaned = _clean_json(
                content
            )

            if not cleaned:
                return None

            parsed = json.loads(
                cleaned
            )

            return _normalise_ai_result(
                parsed,
                req,
            )

    except (
        httpx.HTTPError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    except Exception:
        return None


# ============================================================
# FALLBACK — DECISION
# ============================================================

def _extract_action_entity(req):

    decision = _text(
        getattr(
            req,
            "decision",
            "",
        )
    )

    if not decision:

        return {
            "id": "decision_action",
            "name": "Decision",
            "kind": "decision",
            "attributes": {
                "source": "fallback",
                "confidence": 0.4,
                "uncertainty": 0.6,
            },
        }

    patterns = [
        r"\bconsidering\s+(.+?)(?:[.!?]|$)",
        r"\bthinking\s+about\s+(.+?)(?:[.!?]|$)",
        r"\bplanning\s+to\s+(.+?)(?:[.!?]|$)",
        r"\bplan\s+to\s+(.+?)(?:[.!?]|$)",
        r"\bdeciding\s+whether\s+to\s+(.+?)(?:[.!?]|$)",
        r"\bdecide\s+whether\s+to\s+(.+?)(?:[.!?]|$)",
        r"\bwant\s+to\s+(.+?)(?:[.!?]|$)",
    ]

    action = None

    for pattern in patterns:

        match = re.search(
            pattern,
            decision,
            flags=re.IGNORECASE,
        )

        if match:
            action = match.group(1)
            break

    if not action:
        action = decision

    action = re.sub(
        r"\s+",
        " ",
        action,
    ).strip()

    action = action.rstrip(
        ".!?"
    )

    if len(action) > 100:
        action = (
            action[:97].rstrip()
            + "..."
        )

    return {
        "id": "decision_action",
        "name": action,
        "kind": "decision",
        "attributes": {
            "source": "user_decision",
            "confidence": 1.0,
            "uncertainty": 0.0,
        },
    }


# ============================================================
# FALLBACK — SEMANTIC PATTERNS
# ============================================================

SEMANTIC_PATTERNS = [

    (
        r"\bcustomer\s+demand\b",
        "Customer demand",
        "demand",
    ),

    (
        r"\bconsumer\s+demand\b",
        "Customer demand",
        "demand",
    ),

    (
        r"\bdemand\b",
        "Demand",
        "demand",
    ),

    (
        r"\brevenue\b",
        "Revenue",
        "financial",
    ),

    (
        r"\bprofit\b",
        "Profit",
        "financial",
    ),

    (
        r"\bcash\s*flow\b",
        "Cash flow",
        "financial",
    ),

    (
        r"\boperating\s+costs?\b",
        "Operating costs",
        "financial",
    ),

    (
        r"\boperational\s+costs?\b",
        "Operating costs",
        "financial",
    ),

    (
        r"\bcosts?\b",
        "Operating costs",
        "financial",
    ),

    (
        r"\brent\b",
        "Rent",
        "financial",
    ),

    (
        r"\bfinancial\s+loss(?:es)?\b",
        "Financial losses",
        "financial",
    ),

    (
        r"\binvestment\b",
        "Investment",
        "resource",
    ),

    (
        r"\bcapital\b",
        "Capital",
        "resource",
    ),

    (
        r"\bemployees?\b",
        "Employees",
        "workforce",
    ),

    (
        r"\bstaff\b",
        "Staff",
        "workforce",
    ),

    (
        r"\bstaffing\s+costs?\b",
        "Staffing costs",
        "workforce",
    ),

    (
        r"\bcustomers?\b",
        "Customers",
        "customer",
    ),

    (
        r"\bsuppliers?\b",
        "Suppliers",
        "operational",
    ),

    (
        r"\binventory\b",
        "Inventory",
        "resource",
    ),

    (
        r"\blocation\b",
        "Location",
        "location",
    ),

    (
        r"\bmarket\b",
        "Market",
        "market",
    ),

    (
        r"\bcompetition\b",
        "Competition",
        "market",
    ),

    (
        r"\buncertain(?:ty)?\b",
        "Uncertainty",
        "risk",
    ),

    (
        r"\brisk\b",
        "Risk",
        "risk",
    ),
]


def _extract_context_entities(req):

    context = _text(
        getattr(
            req,
            "context",
            {},
        )
    )

    objective = _text(
        getattr(
            req,
            "objective",
            "",
        )
    )

    domain = _text(
        getattr(
            req,
            "domain",
            "",
        )
    )

    combined = " ".join(
        value
        for value in (
            context,
            objective,
            domain,
        )
        if value
    )

    entities = []
    seen = set()

    if domain:

        entities.append(
            {
                "id": "domain",
                "name": domain,
                "kind": "business",
                "attributes": {
                    "source": "user_input",
                    "confidence": 1.0,
                    "uncertainty": 0.0,
                },
            }
        )

    for pattern, name, kind in SEMANTIC_PATTERNS:

        if not re.search(
            pattern,
            combined,
            flags=re.IGNORECASE,
        ):
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        entities.append(
            {
                "id": f"context_{_slug(name)}",
                "name": name,
                "kind": kind,
                "attributes": {
                    "source": "user_context",
                    "confidence": 1.0,
                    "uncertainty": (
                        0.75
                        if kind == "risk"
                        else 0.25
                    ),
                },
            }
        )

    return entities


# ============================================================
# FALLBACK — TIME
# ============================================================

TIME_PATTERNS = [
    r"\b\d+\s*(?:day|days)\b",
    r"\b\d+\s*(?:week|weeks)\b",
    r"\b\d+\s*(?:month|months)\b",
    r"\b\d+\s*(?:year|years)\b",
    r"\bshort[- ]term\b",
    r"\blong[- ]term\b",
]


def _extract_time_entity(req):

    decision = _text(
        getattr(
            req,
            "decision",
            "",
        )
    )

    context = _text(
        getattr(
            req,
            "context",
            {},
        )
    )

    combined = (
        decision
        + " "
        + context
    )

    for pattern in TIME_PATTERNS:

        match = re.search(
            pattern,
            combined,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        value = match.group(0)

        return {
            "id": "time_horizon",
            "name": value,
            "kind": "time",
            "attributes": {
                "source": "user_input",
                "confidence": 1.0,
                "uncertainty": 0.0,
            },
        }

    return None


# ============================================================
# FALLBACK — RELATIONSHIPS
# ============================================================

def _fallback_relationships(
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    by_kind = {
        entity["kind"]: entity
        for entity in entities
    }

    by_name = {
        entity["name"].lower(): entity
        for entity in entities
    }

    relations = []

    def add(
        source,
        target,
        relation,
        weight,
        confidence,
    ):

        if not source or not target:
            return

        if source["id"] == target["id"]:
            return

        relations.append(
            {
                "source": source["id"],
                "target": target["id"],
                "relation": relation,
                "weight": weight,
                "confidence": confidence,
            }
        )

    decision = by_kind.get("decision")
    demand = (
        by_name.get("customer demand")
        or by_name.get("demand")
    )
    revenue = by_name.get("revenue")
    rent = by_name.get("rent")
    customers = by_name.get("customers")
    uncertainty = by_name.get("uncertainty")
    business = by_kind.get("business")

    if decision and business:
        add(
            decision,
            business,
            "affects",
            0.75,
            0.65,
        )

    if decision and demand:
        add(
            decision,
            demand,
            "influences",
            0.65,
            0.55,
        )

    if demand and revenue:
        add(
            demand,
            revenue,
            "influences",
            0.80,
            0.85,
        )

    if rent and revenue:
        add(
            rent,
            revenue,
            "increases",
            0.70,
            0.80,
        )

    if customers and revenue:
        add(
            customers,
            revenue,
            "influences",
            0.75,
            0.80,
        )

    if uncertainty:
        targets = [
            demand,
            revenue,
            rent,
        ]

        for target in targets:

            if target:
                add(
                    uncertainty,
                    target,
                    "exposes",
                    0.60,
                    0.65,
                )

    return relations


# ============================================================
# FALLBACK — ASSUMPTIONS
# ============================================================

def _fallback_assumptions(req):

    context = _text(
        getattr(
            req,
            "context",
            {},
        )
    )

    if context:

        return [
            {
                "id": "assumption_context",
                "statement": (
                    "The supplied context is treated "
                    "as available evidence."
                ),
                "value": None,
                "confidence": 0.55,
                "sensitivity": 0.75,
            }
        ]

    return [
        {
            "id": "assumption_missing_context",
            "statement": (
                "Important real-world information may "
                "be missing from the supplied decision."
            ),
            "value": None,
            "confidence": 0.35,
            "sensitivity": 0.90,
        }
    ]


# ============================================================
# FALLBACK PARSER
# ============================================================

def parse_fallback(req):

    entities = []

    # Primary decision
    entities.append(
        _extract_action_entity(req)
    )

    # Domain/context
    entities.extend(
        _extract_context_entities(req)
    )

    # Time
    time_entity = _extract_time_entity(req)

    if time_entity:
        entities.append(
            time_entity
        )

    # Deduplicate
    unique = []
    seen = set()

    for entity in entities:

        name = _normalise_name(
            entity.get("name")
        )

        if not name:
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(entity)

    # Stable IDs
    normalized = []
    used_ids = set()

    for index, entity in enumerate(unique):

        name = _normalise_name(
            entity.get("name")
        )

        entity_id = (
            _normalise_name(
                entity.get("id")
            )
            or _slug(name)
            or f"entity_{index}"
        )

        base_id = entity_id
        counter = 2

        while entity_id in used_ids:

            entity_id = (
                f"{base_id}_{counter}"
            )

            counter += 1

        used_ids.add(entity_id)

        normalized.append(
            {
                "id": entity_id,
                "name": name,
                "kind": (
                    _normalise_name(
                        entity.get("kind")
                    )
                    or "concept"
                ),
                "attributes": (
                    entity.get("attributes")
                    if isinstance(
                        entity.get("attributes"),
                        dict,
                    )
                    else {}
                ),
            }
        )

    if not normalized:

        normalized = [
            {
                "id": "decision_action",
                "name": "Decision",
                "kind": "decision",
                "attributes": {
                    "source": "fallback",
                    "confidence": 0.4,
                    "uncertainty": 0.6,
                },
            }
        ]

    relationships = _fallback_relationships(
        normalized
    )

    relation_map = {
        entity["id"]: []
        for entity in normalized
    }

    for relation in relationships:

        relation_map[
            relation["source"]
        ].append(
            {
                "target": relation["target"],
                "relation": relation["relation"],
                "weight": relation["weight"],
                "confidence": relation["confidence"],
            }
        )

    for entity in normalized:

        entity["attributes"][
            "relationships"
        ] = relation_map.get(
            entity["id"],
            [],
        )

    return {
        "action": _text(
            getattr(
                req,
                "decision",
                "",
            )
        ),
        "objective": (
            _text(
                getattr(
                    req,
                    "objective",
                    None,
                )
            )
            or None
        ),
        "domain": (
            _text(
                getattr(
                    req,
                    "domain",
                    None,
                )
            )
            or None
        ),
        "entities": normalized,
        "assumptions": _fallback_assumptions(
            req
        ),
        "constraints": (
            getattr(
                req,
                "constraints",
                [],
            )
            or []
        ),
        "variables": _normalise_variables(
            getattr(
                req,
                "variables",
                {},
            )
        ),
    }


# ============================================================
# PUBLIC API
# ============================================================

async def parse_decision(req):

    # Try AI first.
    ai_result = await parse_ai(req)

    if ai_result:

        if ai_result.get(
            "entities"
        ):

            return ai_result

    # Deterministic semantic fallback.
    return parse_fallback(req)


# ============================================================
# VALIDATION
# ============================================================

def validate_parsed_result(
    data: dict[str, Any],
) -> bool:

    if not isinstance(
        data,
        dict,
    ):
        return False

    required = {
        "action",
        "objective",
        "domain",
        "entities",
        "assumptions",
        "constraints",
        "variables",
    }

    if not required.issubset(
        data.keys()
    ):
        return False

    if not isinstance(
        data["entities"],
        list,
    ):
        return False

    if not isinstance(
        data["assumptions"],
        list,
    ):
        return False

    if not isinstance(
        data["constraints"],
        list,
    ):
        return False

    if not isinstance(
        data["variables"],
        dict,
    ):
        return False

    return True