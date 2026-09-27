import uuid, json
from datetime import datetime
from sqlalchemy import create_engine, text
from app.core.config import settings

_engine=create_engine(settings.database_url.replace("+aiosqlite",""),future=True)
def init():
    with _engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS feedback(
            id TEXT PRIMARY KEY, scenario_id TEXT, predicted TEXT, actual TEXT, notes TEXT, created_at TEXT)"""))
def save_feedback(scenario_id,predicted,actual,notes):
    with _engine.begin() as c:
        c.execute(text("INSERT INTO feedback VALUES (:id,:sid,:p,:a,:n,:t)"),
                  {"id":str(uuid.uuid4()),"sid":scenario_id,"p":json.dumps(predicted),"a":json.dumps(actual),"n":notes,"t":datetime.utcnow().isoformat()})
