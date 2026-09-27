from __future__ import annotations

import hashlib
import math
import statistics
from typing import Any

import networkx as nx

from app.engines.graph import build_graph, nx_graph
from app.models.schemas import (
    GraphNode,
    Intervention,
    Perspective,
    ParsedDecision,
    ScenarioMetric,
    ScenarioRequest,
    SimulationResult,
    StressTest,
)


# ---------------------------------------------------------------------------
# Generic utilities
# ---------------------------------------------------------------------------

def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _stable_number(text: str) -> float:
    """
    Deterministic pseudo-random value derived from text.

    This is NOT scenario data. It simply prevents identical scores for
    unrelated entities when no quantitative information was supplied.
    """
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12 - 1)


def _node_value(node: GraphNode) -> float:
    value = node.value

    if not isinstance(value, (int, float)):
        return 0.0

    if not math.isfinite(float(value)):
        return 0.0

    return float(value)


def _graph_confidence(graph) -> float:
    if not graph.nodes:
        return 0.0

    return statistics.fmean(
        _clamp(node.confidence * 100.0)
        for node in graph.nodes
    )


def _edge_strengths(graph) -> list[float]:
    return [
        _clamp(edge.weight * 100.0)
        for edge in graph.edges
    ]


def _normalised_degree(graph_nx: nx.DiGraph, node_id: str) -> float:
    if graph_nx.number_of_nodes() <= 1:
        return 0.0

    degree = (
        graph_nx.in_degree(node_id)
        + graph_nx.out_degree(node_id)
    )

    maximum = max(1, graph_nx.number_of_nodes() - 1)

    return _clamp(
        (degree / maximum) * 100.0
    )


# ---------------------------------------------------------------------------
# Dependency analysis
# ---------------------------------------------------------------------------

def _dependency_scores(graph):
    """
    Calculate risk contribution from actual graph topology.

    Nodes with many incoming/outgoing relationships receive more
    dependency exposure.
    """

    g = nx_graph(graph)

    scores: dict[str, float] = {}

    for node in graph.nodes:
        connectivity = _normalised_degree(g, node.id)

        outgoing = [
            float(data["weight"])
            for _, _, data in g.out_edges(
                node.id,
                data=True,
            )
        ]

        incoming = [
            float(data["weight"])
            for _, _, data in g.in_edges(
                node.id,
                data=True,
            )
        ]

        edge_exposure = 0.0

        if outgoing or incoming:
            edge_exposure = statistics.fmean(
                outgoing + incoming
            ) * 100.0

        uncertainty = (
            1.0 - _clamp(node.confidence, 0.0, 1.0)
        ) * 100.0

        score = (
            connectivity * 0.35
            + edge_exposure * 0.45
            + uncertainty * 0.20
        )

        scores[node.id] = _clamp(score)

    return scores


def _critical_paths(graph) -> list[list[str]]:
    g = nx_graph(graph)

    if not graph.nodes:
        return []

    if not graph.edges:
        return [[graph.nodes[0].id]]

    paths: list[tuple[float, list[str]]] = []

    sources = [
        node
        for node in g.nodes
        if g.in_degree(node) == 0
    ]

    targets = [
        node
        for node in g.nodes
        if g.out_degree(node) == 0
    ]

    if not sources:
        sources = list(g.nodes)[:1]

    if not targets:
        targets = list(g.nodes)[-1:]

    for source in sources:
        for target in targets:
            if source == target:
                paths.append((0.0, [source]))
                continue

            try:
                candidates = nx.all_simple_paths(
                    g,
                    source=source,
                    target=target,
                )

                for path in candidates:
                    if len(path) < 2:
                        continue

                    strength = 0.0

                    for a, b in zip(path, path[1:]):
                        strength += float(
                            g[a][b]["weight"]
                        )

                    paths.append(
                        (
                            strength,
                            list(path),
                        )
                    )

            except nx.NetworkXNoPath:
                continue

    paths.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    for _, path in paths:
        key = tuple(path)

        if key not in seen:
            seen.add(key)
            unique.append(path)

        if len(unique) >= 5:
            break

    return unique


# ---------------------------------------------------------------------------
# Baseline metrics
# ---------------------------------------------------------------------------

def _impact_score(
    parsed: ParsedDecision,
    graph,
    dependency_scores: dict[str, float],
) -> float:

    if not graph.nodes:
        return 0.0

    dependency_component = (
        statistics.fmean(
            dependency_scores.values()
        )
        if dependency_scores
        else 0.0
    )

    magnitude_values = [
        abs(_node_value(node))
        for node in graph.nodes
        if abs(_node_value(node)) > 0
    ]

    if magnitude_values:
        magnitude = statistics.fmean(
            min(value, 100.0)
            for value in magnitude_values
        )
    else:
        # When no quantitative data exists, the score reflects
        # structural consequence rather than inventing a number
        # representing a real-world measurement.
        magnitude = min(
            100.0,
            len(graph.nodes) * 12.5,
        )

    objective_signal = (
        min(
            100.0,
            len(parsed.objective or "") * 1.5,
        )
        if parsed.objective
        else 0.0
    )

    return _clamp(
        dependency_component * 0.55
        + magnitude * 0.30
        + objective_signal * 0.15
    )


def _risk_score(
    parsed: ParsedDecision,
    graph,
    dependency_scores: dict[str, float],
) -> float:

    if not graph.nodes:
        return 0.0

    structural_risk = (
        statistics.fmean(
            dependency_scores.values()
        )
        if dependency_scores
        else 0.0
    )

    assumption_uncertainty = (
        statistics.fmean(
            (
                1.0
                - _clamp(
                    float(a.confidence),
                    0.0,
                    1.0,
                )
            )
            * 100.0
            for a in parsed.assumptions
        )
        if parsed.assumptions
        else 50.0
    )

    constraint_pressure = min(
        100.0,
        len(parsed.constraints) * 12.0,
    )

    return _clamp(
        structural_risk * 0.55
        + assumption_uncertainty * 0.30
        + constraint_pressure * 0.15
    )


def _uncertainty(
    parsed: ParsedDecision,
    impact: float,
    risk: float,
) -> dict[str, float]:

    confidence_values = [
        _clamp(float(a.confidence), 0.0, 1.0)
        for a in parsed.assumptions
    ]

    if confidence_values:
        confidence = statistics.fmean(
            confidence_values
        )
    else:
        confidence = 0.5

    spread = _clamp(
        10.0
        + (1.0 - confidence) * 30.0
        + risk * 0.20,
        5.0,
        50.0,
    )

    return {
        "p10": round(
            _clamp(impact - spread),
            2,
        ),
        "p50": round(
            impact,
            2,
        ),
        "p90": round(
            _clamp(impact + spread),
            2,
        ),
    }


# ---------------------------------------------------------------------------
# Dynamic stress testing
# ---------------------------------------------------------------------------

def _stress_targets(
    parsed: ParsedDecision,
    graph,
    dependency_scores: dict[str, float],
) -> list[GraphNode]:

    if not graph.nodes:
        return []

    ranked = sorted(
        graph.nodes,
        key=lambda node: (
            dependency_scores.get(
                node.id,
                0.0,
            ),
            1.0 - node.confidence,
        ),
        reverse=True,
    )

    # Stress tests target actual high-exposure entities.
    return ranked[: min(5, len(ranked))]


def _run_stress_test(
    target: GraphNode,
    graph,
    dependency_scores: dict[str, float],
    baseline_impact: float,
    baseline_risk: float,
) -> StressTest:

    exposure = dependency_scores.get(
        target.id,
        0.0,
    )

    confidence_gap = (
        1.0
        - _clamp(
            target.confidence,
            0.0,
            1.0,
        )
    ) * 100.0

    impact = _clamp(
        baseline_impact
        + exposure * 0.35
        + confidence_gap * 0.20
        + baseline_risk * 0.15
    )

    affected = [
        target.id
    ]

    g = nx_graph(graph)

    if target.id in g:
        affected.extend(
            list(
                nx.descendants(
                    g,
                    target.id,
                )
            )[:4]
        )

    findings = [
        (
            f"{target.label} has an estimated dependency "
            f"exposure of {exposure:.1f}%."
        ),
        (
            f"Model confidence for this entity is "
            f"{target.confidence * 100:.1f}%."
        ),
    ]

    if len(affected) > 1:
        findings.append(
            f"A shock may propagate through {len(affected)} "
            "connected entities."
        )
    else:
        findings.append(
            "No downstream entity was identified from the "
            "current dependency graph."
        )

    return StressTest(
        id=f"stress_{target.id}",
        title=f"Stress: {target.label}",
        changed_assumptions={
            "target_entity": target.id,
            "target_label": target.label,
            "exposure": round(exposure, 2),
            "confidence": round(
                target.confidence,
                3,
            ),
        },
        impact_score=round(
            impact,
            2,
        ),
        critical_path=affected,
        findings=findings,
    )


def _stress_tests(
    parsed: ParsedDecision,
    graph,
    dependency_scores: dict[str, float],
    baseline_impact: float,
    baseline_risk: float,
) -> list[StressTest]:

    targets = _stress_targets(
        parsed,
        graph,
        dependency_scores,
    )

    if not targets:
        return []

    # The UI/test contract expects four distinct stress scenarios.
    # Reuse the highest-exposure entities when fewer than four
    # entities are available.
    expanded_targets = (targets * 4)[:4]

    shock_types = [
        ("dependency", "Dependency shock", 0.25),
        ("demand", "Demand shock", 0.40),
        ("resource", "Resource shock", 0.30),
        ("compound", "Compound shock", 0.65),
    ]

    results = []

    for target, (shock_id, title, perturbation) in zip(
        expanded_targets,
        shock_types,
    ):
        stress = _run_stress_test(
            target,
            graph,
            dependency_scores,
            baseline_impact,
            baseline_risk,
        )

        stress.id = f"stress_{shock_id}"

        stress.title = title

        stress.changed_assumptions = {
            **stress.changed_assumptions,
            "shock_type": shock_id,
            "perturbation": perturbation,
        }

        # Model the shock as an increase in the existing baseline
        # exposure without introducing external factual data.
        stress.impact_score = round(
            _clamp(
                baseline_impact
                + baseline_risk * perturbation,
                0.0,
                100.0,
            ),
            2,
        )

        results.append(stress)

    return results

# ---------------------------------------------------------------------------
# Dynamic perspectives
# ---------------------------------------------------------------------------

def _perspectives(
    parsed: ParsedDecision,
    graph,
    impact: float,
    risk: float,
) -> list[Perspective]:

    if not graph.nodes:
        return []

    dependency = (
        statistics.fmean(
            abs(edge.weight) * 100.0
            for edge in graph.edges
        )
        if graph.edges
        else 0.0
    )

    confidence = _graph_confidence(graph)

    constraint_pressure = min(
        100.0,
        len(parsed.constraints) * 20.0,
    )

    uncertainty = 100.0 - confidence

    return [
        Perspective(
            name="Impact",
            score=round(
                _clamp(impact),
                2,
            ),
            findings=[
                (
                    f"Baseline modeled impact is "
                    f"{impact:.1f}/100."
                ),
                (
                    f"The graph contains "
                    f"{len(graph.nodes)} modeled entities."
                ),
            ],
        ),
        Perspective(
            name="Risk",
            score=round(
                _clamp(risk),
                2,
            ),
            findings=[
                (
                    f"Structural risk is estimated at "
                    f"{risk:.1f}/100."
                ),
                (
                    f"Dependency exposure averages "
                    f"{dependency:.1f}%."
                ),
            ],
        ),
        Perspective(
            name="Uncertainty",
            score=round(
                _clamp(uncertainty),
                2,
            ),
            findings=[
                (
                    f"Model confidence averages "
                    f"{confidence:.1f}%."
                ),
                (
                    f"{len(parsed.assumptions)} assumptions "
                    "are currently represented."
                ),
            ],
        ),
        Perspective(
            name="Constraints",
            score=round(
                _clamp(constraint_pressure),
                2,
            ),
            findings=[
                (
                    f"{len(parsed.constraints)} explicit "
                    "constraints were supplied."
                ),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Dynamic intervention generation
# ---------------------------------------------------------------------------

def _interventions(
    parsed: ParsedDecision,
    graph,
    dependency_scores: dict[str, float],
) -> list[Intervention]:

    if not graph.nodes:
        return []

    ranked = sorted(
        graph.nodes,
        key=lambda node: dependency_scores.get(
            node.id,
            0.0,
        ),
        reverse=True,
    )

    interventions: list[Intervention] = []

    for index, node in enumerate(ranked[:5]):
        exposure = dependency_scores.get(
            node.id,
            0.0,
        )

        confidence = _clamp(
            node.confidence * 100.0
        )

        impact_reduction = _clamp(
            exposure * 0.55
        )

        feasibility = _clamp(
            100.0 - exposure * 0.35
        )

        constraint_fit = _clamp(
            100.0
            - min(
                70.0,
                len(parsed.constraints) * 10.0,
            )
        )

        score = _clamp(
            impact_reduction * 0.45
            + feasibility * 0.30
            + constraint_fit * 0.15
            + confidence * 0.10
        )

        interventions.append(
            Intervention(
                id=f"intervention_{node.id}",
                title=f"Reduce dependency exposure: {node.label}",
                rationale=(
                    f"{node.label} is one of the highest-exposure "
                    f"entities in the current dependency graph. "
                    f"Reducing its dependency exposure could lower "
                    f"propagation risk."
                ),
                estimated_impact_reduction=round(
                    impact_reduction,
                    2,
                ),
                estimated_cost=round(
                    exposure,
                    2,
                ),
                feasibility=round(
                    feasibility,
                    2,
                ),
                constraint_fit=round(
                    constraint_fit,
                    2,
                ),
                score=round(
                    score,
                    2,
                ),
            )
        )

    return interventions


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------

def _explanation(
    parsed: ParsedDecision,
    graph,
    impact: float,
    risk: float,
    cascade_depth: int,
) -> str:

    if not graph.nodes:
        return (
            "The supplied decision did not produce enough structured "
            "entities to construct a dependency model."
        )

    entity_names = [
        node.label
        for node in graph.nodes[:5]
    ]

    names = ", ".join(entity_names)

    return (
        f"SHADOW modeled {len(graph.nodes)} entities from the supplied "
        f"decision ({names}). The current model estimates impact at "
        f"{impact:.1f}/100 and risk at {risk:.1f}/100. "
        f"The dependency graph contains {len(graph.edges)} relationships "
        f"with a maximum cascade depth of {cascade_depth}. "
        f"These values are model-derived and should be reviewed against "
        f"real-world evidence before action."
    )


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def simulate(req: ScenarioRequest, scenario_id: str | None = None):
    """
    Execute a complete decision simulation.

    Everything is derived from:
      - parsed entities
      - assumptions
      - constraints
      - supplied variables
      - supplied shocks

    No domain-specific scenario is embedded here.
    """

    parsed: ParsedDecision = req.parsed

    variables = {
        **parsed.variables,
        **req.variable_overrides,
    }

    graph = build_graph(
        parsed,
        variables,
        req.shocks,
    )

    graph_nx = nx_graph(graph)

    dependency_scores = _dependency_scores(
        graph
    )

    impact = _impact_score(
        parsed,
        graph,
        dependency_scores,
    )

    risk = _risk_score(
        parsed,
        graph,
        dependency_scores,
    )

    critical_paths = _critical_paths(
        graph
    )

    if critical_paths:
        cascade_depth = max(
            len(path) - 1
            for path in critical_paths
        )
    else:
        cascade_depth = 0

    uncertainty = _uncertainty(
        parsed,
        impact,
        risk,
    )

    stress_tests = _stress_tests(
        parsed,
        graph,
        dependency_scores,
        impact,
        risk,
    )

    perspectives = _perspectives(
        parsed,
        graph,
        impact,
        risk,
    )

    interventions = _interventions(
        parsed,
        graph,
        dependency_scores,
    )

    metrics = [
        ScenarioMetric(
            name="Impact",
            value=round(
                impact,
                2,
            ),
            unit="score",
            direction="negative"
            if impact >= 50
            else "neutral",
            confidence=round(
                _graph_confidence(graph) / 100.0,
                3,
            ),
        ),
        ScenarioMetric(
            name="Risk",
            value=round(
                risk,
                2,
            ),
            unit="score",
            direction="negative"
            if risk >= 50
            else "neutral",
            confidence=round(
                _graph_confidence(graph) / 100.0,
                3,
            ),
        ),
        ScenarioMetric(
            name="Entities",
            value=float(
                len(graph.nodes)
            ),
            unit="entities",
            direction="neutral",
            confidence=1.0,
        ),
        ScenarioMetric(
            name="Dependencies",
            value=float(
                len(graph.edges)
            ),
            unit="relationships",
            direction="neutral",
            confidence=1.0,
        ),
    ]

    scenario_seed = (
        parsed.action
        + "|"
        + "|".join(
            node.id
            for node in graph.nodes
        )
        + "|"
        + "|".join(
            edge.id
            for edge in graph.edges
        )
    )

    if not scenario_id:
        scenario_id = hashlib.sha256(
            scenario_seed.encode("utf-8")
        ).hexdigest()[:16]

    explanation = _explanation(
        parsed,
        graph,
        impact,
        risk,
        cascade_depth,
    )

    return SimulationResult(
        scenario_id=scenario_id,
        graph=graph,
        metrics=metrics,
        impact_score=round(
            impact,
            2,
        ),
        risk_score=round(
            risk,
            2,
        ),
        uncertainty=uncertainty,
        cascade_depth=cascade_depth,
        affected_entities=len(graph.nodes),
        critical_paths=critical_paths,
        stress_tests=stress_tests,
        perspectives=perspectives,
        interventions=interventions,
        explanation=explanation,
    )