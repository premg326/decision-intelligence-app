from typing import Any, Optional, Literal

from pydantic import BaseModel, Field


# ============================================================
# DECISION INPUT
# ============================================================

class DecisionRequest(BaseModel):
    decision: str = Field(min_length=5, max_length=10000)
    objective: Optional[str] = None
    domain: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, float] = Field(default_factory=dict)


# ============================================================
# PARSING
# ============================================================

class Entity(BaseModel):
    id: str
    name: str
    kind: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class Assumption(BaseModel):
    id: str
    statement: str
    value: Any = None
    confidence: float = 0.5
    sensitivity: float = 0.5


class ParsedDecision(BaseModel):
    action: str
    objective: Optional[str] = None
    domain: Optional[str] = None
    entities: list[Entity] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    variables: dict[str, float] = Field(default_factory=dict)


# ============================================================
# GRAPH
# ============================================================

class GraphNode(BaseModel):
    id: str
    label: str
    kind: str
    value: float = 0
    unit: str = ""
    risk: float = 0
    confidence: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    weight: float
    delay: float = 0
    confidence: float = 0.5


class ScenarioGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ============================================================
# SIMULATION INPUT
# ============================================================

class ScenarioRequest(BaseModel):
    parsed: ParsedDecision
    variable_overrides: dict[str, float] = Field(default_factory=dict)
    shocks: dict[str, float] = Field(default_factory=dict)


# ============================================================
# METRICS
# ============================================================

class ScenarioMetric(BaseModel):
    name: str
    value: float
    unit: str = ""
    direction: Literal["positive", "negative", "neutral"] = "neutral"
    confidence: float = 0.5


# ============================================================
# STRESS TESTING
# ============================================================

class StressTest(BaseModel):
    id: str
    title: str
    changed_assumptions: dict[str, Any] = Field(default_factory=dict)
    impact_score: float
    critical_path: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


# ============================================================
# INTERVENTIONS
# ============================================================

class Intervention(BaseModel):
    id: str
    title: str
    rationale: str
    estimated_impact_reduction: float
    estimated_cost: float
    feasibility: float
    constraint_fit: float
    score: float


# ============================================================
# PERSPECTIVES
# ============================================================

class Perspective(BaseModel):
    name: str
    score: float
    findings: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


# ============================================================
# SIMULATION RESULT
# ============================================================

class SimulationResult(BaseModel):
    scenario_id: str
    graph: ScenarioGraph
    metrics: list[ScenarioMetric] = Field(default_factory=list)

    impact_score: float
    risk_score: float

    uncertainty: dict[str, float] = Field(default_factory=dict)

    cascade_depth: int
    affected_entities: int

    critical_paths: list[list[str]] = Field(default_factory=list)

    stress_tests: list[StressTest] = Field(default_factory=list)
    perspectives: list[Perspective] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)

    explanation: str


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================
#
# Existing engine code imports ScenarioResult.
# Keep SimulationResult as the canonical model while exposing
# ScenarioResult for compatibility.
#

ScenarioResult = SimulationResult


# ============================================================
# COMPARISON
# ============================================================

class CompareRequest(BaseModel):
    scenarios: list[ScenarioRequest] = Field(default_factory=list)


# ============================================================
# FEEDBACK
# ============================================================

class FeedbackRequest(BaseModel):
    scenario_id: str
    predicted: dict[str, float] = Field(default_factory=dict)
    actual: dict[str, float] = Field(default_factory=dict)
    notes: str = ""