from app.models.schemas import *
from app.engines.simulation import simulate
def test_generic_scenario():
    p=ParsedDecision(action="Change allocation",objective="Improve outcome",domain="test",
      entities=[Entity(id="a",name="A",kind="entity"),Entity(id="b",name="B",kind="entity")],
      assumptions=[],constraints=[],variables={})
    r=simulate(ScenarioRequest(parsed=p))
    assert r.affected_entities>=2
    assert 0<=r.risk_score<=100
    assert len(r.stress_tests)==4
