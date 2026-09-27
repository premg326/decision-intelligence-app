from __future__ import annotations

import hashlib
import math
import re
from typing import Any

import networkx as nx

from app.models.schemas import (
    Entity,
    GraphEdge,
    GraphNode,
    ParsedDecision,
    ScenarioGraph,
)


MIN_RISK = 0.02
MAX_RISK = 0.95

MIN_WEIGHT = 0.20
MAX_WEIGHT = 0.95


# ============================================================
# HELPERS
# ============================================================

def _stable_id(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:12]


def _clamp(
    value: float,
    low: float,
    high: float,
) -> float:
    return max(
        low,
        min(high, float(value)),
    )


def _tokens(text: str) -> set[str]:
    return set(
        re.findall(
            r"[a-z0-9]+",
            str(text).lower(),
        )
    )


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        value = float(value)

        if math.isfinite(value):
            return value

    return None


def _kind(entity: Entity) -> str:
    return (
        str(entity.kind or "")
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _text(entity: Entity) -> str:
    return (
        f"{entity.name} "
        f"{entity.kind}"
    ).lower()


# ============================================================
# ENTITY VALUE
# ============================================================

def _entity_value(
    entity: Entity,
    variables: dict[str, float],
) -> float:

    if entity.id in variables:
        return float(
            variables[entity.id]
        )

    if entity.name in variables:
        return float(
            variables[entity.name]
        )

    numbers = []

    for value in entity.attributes.values():
        number = _number(value)

        if number is not None:
            numbers.append(number)

    if numbers:
        return sum(numbers) / len(numbers)

    return 0.0


# ============================================================
# CONFIDENCE
# ============================================================

def _confidence(
    entity: Entity,
) -> float:

    value = _number(
        entity.attributes.get(
            "confidence"
        )
    )

    if value is None:
        return 0.60

    if value > 1:
        value /= 100.0

    return _clamp(
        value,
        0.10,
        1.0,
    )


# ============================================================
# RISK
# ============================================================

def _node_risk(
    entity: Entity,
    variables: dict[str, float],
    shocks: dict[str, float],
) -> float:

    confidence = _confidence(entity)

    # Prefer explicit uncertainty supplied by the parser/AI.
    uncertainty = _number(
        entity.attributes.get("uncertainty")
    )

    if uncertainty is None:
        uncertainty = 1.0 - confidence
    else:
        if uncertainty > 1:
            uncertainty /= 100.0
        uncertainty = _clamp(uncertainty, 0.0, 1.0)

    shock = _number(
        shocks.get(entity.id)
    ) or 0.0

    shock = abs(shock)

    if shock > 1:
        shock /= 100.0

    value = abs(
        _entity_value(
            entity,
            variables,
        )
    )

    magnitude = _clamp(
        value / 100.0,
        0.0,
        0.30,
    )

    risk = (
        0.10
        + uncertainty * 0.55
        + shock * 0.25
        + magnitude * 0.10
    )

    return round(
        _clamp(
            risk,
            MIN_RISK,
            MAX_RISK,
        ),
        3,
    )
    


# ============================================================
# ENTITY TYPES
# ============================================================

def _is_decision(entity: Entity) -> bool:
    """Identify decision nodes robustly, including parser-generic entities."""
    kind = _kind(entity)

    if kind == "decision":
        return True

    attrs = entity.attributes or {}
    for key in ("type", "entity_type", "role", "category"):
        value = str(attrs.get(key, "")).strip().lower()
        if value in {"decision", "decision_node"}:
            return True

    name = str(entity.name or "").strip().lower()
    decision_phrases = (
        "i am considering", "i'm considering", "considering ",
        "we are considering", "we're considering", "should i ",
        "should we ", "i plan to ", "we plan to ", "planning to ",
        "deciding whether", "decision to ", "decide to ",
        "want to open", "want to launch", "want to start",
    )
    return any(phrase in name for phrase in decision_phrases)


def _is_business(entity: Entity) -> bool:

    kind = _kind(entity)
    tokens = _tokens(_text(entity))

    return (
        kind in {
            "business",
            "operational",
            "organization",
        }
        or bool(
            tokens
            & {
                "business",
                "shop",
                "store",
                "branch",
                "company",
            }
        )
    )


def _is_demand(entity: Entity) -> bool:

    kind = _kind(entity)
    tokens = _tokens(_text(entity))

    return (
        kind == "demand"
        or bool(
            tokens
            & {
                "demand",
                "traffic",
                "market",
            }
        )
    )


def _is_customer(entity: Entity) -> bool:

    kind = _kind(entity)
    tokens = _tokens(_text(entity))

    return (
        kind == "customer"
        or bool(
            tokens
            & {
                "customer",
                "customers",
                "client",
                "clients",
            }
        )
    )


def _is_financial(entity: Entity) -> bool:

    # Rent/cost/expense nodes are financial in a broad sense,
    # but they are treated as COST nodes for causal modeling.
    if _is_cost(entity):
        return False

    kind = _kind(entity)
    tokens = _tokens(_text(entity))

    return (
        kind == "financial"
        or bool(
            tokens
            & {
                "revenue",
                "sales",
                "income",
                "profit",
                "margin",
                "financial",
            }
        )
    )


def _is_resource(entity: Entity) -> bool:

    kind = _kind(entity)
    tokens = _tokens(_text(entity))

    return (
        kind in {
            "resource",
            "workforce",
            "operational_resource",
        }
        or bool(
            tokens
            & {
                "resource",
                "staff",
                "employee",
                "employees",
                "inventory",
                "capacity",
            }
        )
    )


def _is_cost(entity: Entity) -> bool:

    tokens = _tokens(_text(entity))

    return bool(
        tokens
        & {
            "rent",
            "cost",
            "costs",
            "expense",
            "expenses",
        }
    )


def _is_risk(entity: Entity) -> bool:

    kind = _kind(entity)
    tokens = _tokens(_text(entity))

    return (
        kind == "risk"
        or bool(
            tokens
            & {
                "risk",
                "uncertainty",
                "uncertain",
                "volatility",
                "exposure",
            }
        )
    )


def _display_kind(entity: Entity) -> str:
    """Return a stable, meaningful UI kind instead of parser-generic labels."""
    if _is_decision(entity):
        return "decision"
    if _is_risk(entity):
        return "risk"
    if _is_business(entity):
        return "business"
    if _is_demand(entity):
        return "demand"
    if _is_customer(entity):
        return "customer"
    if _is_cost(entity):
        return "financial"
    if _is_financial(entity):
        return "financial"
    if _is_resource(entity):
        return "resource"

    raw = _kind(entity)
    return raw if raw else "entity"


# ============================================================
# EXPLICIT RELATIONSHIPS
# ============================================================

def _relationship_allowed(
    source: Entity,
    target: Entity,
    relation: str,
) -> bool:
    """
    Validate parser/AI supplied relationships against the same
    controlled causal model used by semantic relationships.

    The parser may suggest relationships, but it must never be
    allowed to create arbitrary graph edges.
    """

    # Decision -> business/resource
    if _is_decision(source):
        return (
            relation == "applies_to"
            and (
                _is_business(target)
                or _is_resource(target)
            )
        )

    # Business -> demand/customer
    if _is_business(source):
        return (
            relation == "influences"
            and (
                _is_demand(target)
                or _is_customer(target)
            )
        )

    # Demand -> financial/customer/risk
    if _is_demand(source):
        if relation == "influences":
            return (
                _is_financial(target)
                or _is_customer(target)
            )

        if relation == "increases_exposure":
            return _is_risk(target)

        return False

    # Customer -> financial
    if _is_customer(source):
        return (
            relation == "contributes_to"
            and _is_financial(target)
        )

    # Cost/rent -> risk
    if _is_cost(source):
        return (
            relation == "increases_exposure"
            and _is_risk(target)
        )

    # Resource -> financial/risk
    if _is_resource(source):
        if relation == "influences":
            return _is_financial(target)

        if relation == "increases_exposure":
            return _is_risk(target)

        return False

    return False


def _explicit_relation(
    source: Entity,
    target: Entity,
) -> tuple[str, float] | None:

    attrs = source.attributes or {}

    mapping = {
        "depends_on": "depends_on",
        "dependency": "depends_on",
        "dependencies": "depends_on",
        "influences": "influences",
        "contributes_to": "contributes_to",
        "enables": "enables",
        "constrains": "constrains",
        "causes": "causes",
        "mitigates": "mitigates",
        "exposes": "increases_exposure",
        "exposed_to": "increases_exposure",
    }

    target_id = target.id.lower()
    target_name = target.name.lower()

    for key, relation in mapping.items():

        raw = attrs.get(key)

        if raw is None:
            continue

        values = (
            [raw]
            if isinstance(raw, str)
            else raw
            if isinstance(raw, list)
            else []
        )

        for value in values:

            text = str(value).lower()

            if (
                target_id not in text
                and target_name not in text
            ):
                continue

            # IMPORTANT:
            # AI relationships must also pass the controlled
            # causal model. Invalid AI edges are rejected.
            semantic = _semantic_relation(
                source,
                target,
            )

            # The controlled causal model is authoritative.
            # AI/parser metadata can only confirm an allowed edge;
            # it can never create or relabel one.
            if semantic is None:
                continue

            allowed_relation, confidence = semantic

            if relation != allowed_relation:
                continue

            return (
                allowed_relation,
                min(0.90, confidence),
            )

    return None


# ============================================================
# CONTROLLED CAUSAL MODEL
#
# IMPORTANT:
# We deliberately DO NOT connect every possible pair.
# ============================================================

def _semantic_relation(
    source: Entity,
    target: Entity,
) -> tuple[str, float] | None:

    if source.id == target.id:
        return None

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if _is_decision(source):

        # Decision -> business/resource only.
        if _is_business(target):
            return (
                "applies_to",
                0.95,
            )

        if _is_resource(target):
            return (
                "applies_to",
                0.90,
            )

        return None

    # --------------------------------------------------------
    # BUSINESS
    # --------------------------------------------------------

    if _is_business(source):

        # Business -> demand.
        if _is_demand(target):
            return (
                "influences",
                0.90,
            )

        # Business -> customers.
        if _is_customer(target):
            return (
                "influences",
                0.82,
            )

        return None

    # --------------------------------------------------------
    # DEMAND
    # --------------------------------------------------------

    if _is_demand(source):

        # Demand -> revenue.
        if _is_financial(target) and not _is_cost(target):
            return (
                "influences",
                0.90,
            )

        # Demand -> customers.
        if _is_customer(target):
            return (
                "influences",
                0.85,
            )

        # Demand -> uncertainty.
        if _is_risk(target):
            return (
                "increases_exposure",
                0.82,
            )

        return None

    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    if _is_customer(source):

        if _is_financial(target) and not _is_cost(target):
            return (
                "contributes_to",
                0.88,
            )

        return None

    # --------------------------------------------------------
    # COST / RENT
    # --------------------------------------------------------

    if _is_cost(source):

        # Cost pressure increases uncertainty.
        if _is_risk(target):
            return (
                "increases_exposure",
                0.82,
            )

        return None

    # --------------------------------------------------------
    # RESOURCE
    # --------------------------------------------------------

    if _is_resource(source):

        if _is_financial(target) and not _is_cost(target):
            return (
                "influences",
                0.82,
            )

        if _is_risk(target):
            return (
                "increases_exposure",
                0.78,
            )

        return None

    # --------------------------------------------------------
    # FINANCIAL
    #
    # Financial nodes are terminal outcomes in this graph.
    # Do not automatically connect them to other nodes.
    # --------------------------------------------------------

    if _is_financial(source):
        return None

    return None


# ============================================================

# EDGE WEIGHT
# ============================================================

def _edge_weight(
    source: Entity,
    target: Entity,
    variables: dict[str, float],
    shocks: dict[str, float],
    confidence: float,
) -> float:

    source_confidence = _confidence(
        source
    )

    target_confidence = _confidence(
        target
    )

    shock = _number(
        shocks.get(target.id)
    ) or 0.0

    shock = abs(shock)

    if shock > 1:
        shock /= 100.0

    magnitude = _clamp(
        abs(
            _entity_value(
                source,
                variables,
            )
        ) / 100.0,
        0.0,
        0.20,
    )

    weight = (
        confidence * 0.70
        + (
            (
                source_confidence
                + target_confidence
            )
            / 2.0
        ) * 0.20
        + shock * 0.07
        + magnitude * 0.03
    )

    return round(
        _clamp(
            weight,
            MIN_WEIGHT,
            MAX_WEIGHT,
        ),
        4,
    )


# ============================================================
# NODES
# ============================================================

def _build_nodes(
    parsed: ParsedDecision,
    variables: dict[str, float],
    shocks: dict[str, float],
) -> list[GraphNode]:

    nodes = []

    for entity in parsed.entities:

        value = _entity_value(
            entity,
            variables,
        )

        confidence = _confidence(
            entity
        )

        risk = _node_risk(
            entity,
            variables,
            shocks,
        )

        metadata = {
            **(
                entity.attributes
                or {}
            ),
            "source": "parsed_decision",
            "graph_model": "controlled_causal_dag",
        }

        nodes.append(
            GraphNode(
                id=entity.id,
                label=entity.name,
                # Never expose parser-generic kinds such as "entity" in the UI.
                kind=_display_kind(entity),
                value=round(
                    value,
                    3,
                ),
                unit=str(
                    entity.attributes.get(
                        "unit",
                        "",
                    )
                ),
                risk=round(
                    risk,
                    3,
                ),
                confidence=round(
                    confidence,
                    3,
                ),
                metadata=metadata,
            )
        )

    return nodes


# ============================================================
# EDGES
# ============================================================

def _build_edges(
    entities: list[Entity],
    variables: dict[str, float],
    shocks: dict[str, float],
) -> list[GraphEdge]:

    edges: list[GraphEdge] = []
    existing: set[tuple[str, str]] = set()

    for source in entities:
        for target in entities:

            if source.id == target.id:
                continue

            pair = (source.id, target.id)

            if pair in existing:
                continue

            # HARD SAFETY INVARIANT: a decision may only point to the
            # operational thing it acts on. Never connect it directly
            # to revenue, demand, rent, risk, uncertainty, etc.
            if _is_decision(source) and not (
                _is_business(target) or _is_resource(target)
            ):
                continue

            # ONLY the controlled causal model decides
            # whether an edge is allowed.
            relation = _semantic_relation(
                source,
                target,
            )

            if relation is None:
                continue

            relation_name, confidence = relation

            weight = _edge_weight(
                source,
                target,
                variables,
                shocks,
                confidence,
            )

            edge_key = (
                f"{source.id}:"
                f"{target.id}:"
                f"{relation_name}"
            )

            edges.append(
                GraphEdge(
                    id=_stable_id(edge_key),
                    source=source.id,
                    target=target.id,
                    relation=relation_name,
                    weight=weight,
                    delay=1.0,
                    confidence=round(
                        confidence,
                        3,
                    ),
                )
            )

            existing.add(pair)

    return edges


# ============================================================
# PUBLIC API
# ============================================================

def build_graph(
    parsed: ParsedDecision,
    variables: dict[str, float] | None = None,
    shocks: dict[str, float] | None = None,
) -> ScenarioGraph:

    variables = variables or {}
    shocks = shocks or {}

    nodes = _build_nodes(
        parsed,
        variables,
        shocks,
    )

    edges = _build_edges(
        parsed.entities,
        variables,
        shocks,
    )

    return ScenarioGraph(
        nodes=nodes,
        edges=edges,
    )


# ============================================================
# NETWORKX
# ============================================================

def nx_graph(
    graph: ScenarioGraph,
) -> nx.DiGraph:

    graph_nx = nx.DiGraph()

    for node in graph.nodes:
        graph_nx.add_node(
            node.id,
            node=node,
        )

    for edge in graph.edges:
        graph_nx.add_edge(
            edge.source,
            edge.target,
            weight=edge.weight,
            edge=edge,
        )

    return graph_nx