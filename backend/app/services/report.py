from app.models.schemas import SimulationResult
def report(result: SimulationResult):
    return {
        "title":"SHADOW Decision Report",
        "scenario_id":result.scenario_id,
        "summary":result.explanation,
        "metrics":[m.model_dump() for m in result.metrics],
        "uncertainty":result.uncertainty,
        "critical_paths":result.critical_paths,
        "stress_tests":[s.model_dump() for s in result.stress_tests],
        "perspectives":[p.model_dump() for p in result.perspectives],
        "interventions":[i.model_dump() for i in result.interventions],
        "human_review_required":True
    }
