from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.schemas import *
from app.services.ai import parse_ai,parse_fallback
from app.engines.simulation import simulate
from app.services.report import report
from app.services.store import init,save_feedback

app=FastAPI(title="SHADOW Decision Intelligence",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.on_event("startup")
def startup(): init()

@app.get("/health")
def health(): return {"status":"ok","ai_configured":bool(settings.ai_api_key)}

@app.post("/api/parse",response_model=ParsedDecision)
async def parse(req:DecisionRequest):
    try:
        data=await parse_ai(req)
        if data: return ParsedDecision(**data)
    except Exception:
        pass
    return ParsedDecision(**parse_fallback(req))

@app.post("/api/simulate",response_model=SimulationResult)
def run(req:ScenarioRequest):
    return simulate(req,"scenario_live")

@app.post("/api/compare")
def compare(req:CompareRequest):
    results=[simulate(s,f"scenario_{i}") for i,s in enumerate(req.scenarios)]
    return {"scenarios":[r.model_dump() for r in results]}

@app.post("/api/report")
def make_report(req:ScenarioRequest):
    return report(simulate(req,"report"))

@app.post("/api/feedback")
def feedback(req:FeedbackRequest):
    save_feedback(req.scenario_id,req.predicted,req.actual,req.notes)
    return {"status":"recorded","scenario_id":req.scenario_id}
