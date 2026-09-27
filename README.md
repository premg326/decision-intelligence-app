# SHADOW — Production Scenario-Based Decision Intelligence

SHADOW is a domain-agnostic decision intelligence platform. It does not contain a
hardcoded road, city, agency, company, or fixed scenario.

Core pipeline:

USER DECISION
→ AI DECISION PARSER
→ ENTITY + ASSUMPTION EXTRACTION
→ SCENARIO GRAPH
→ BASELINE SIMULATION
→ CASCADE ENGINE
→ ADVERSARIAL STRESS TEST
→ WHAT-IF / COUNTERFACTUALS
→ CONSTRAINT OPTIMIZATION
→ INTERVENTION OPTIMIZATION
→ MULTI-PERSPECTIVE REVIEW
→ UNCERTAINTY ANALYSIS
→ DECISION REPORT
→ HUMAN DECISION
→ ACTUAL OUTCOME
→ FEEDBACK / LEARNING

## Important design rule
The LLM interprets structured user intent and explains results. It is not trusted
to fabricate simulation outcomes. Numeric propagation, constraints, scenario
comparison and optimization are performed by deterministic backend engines.

## Run locally

### Backend
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

## AI
Set:
AI_API_KEY=...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=...

Any OpenAI-compatible endpoint can be used.

If no AI key is configured, SHADOW still operates using structured deterministic
scenario construction. No domain-specific example is embedded.

## Optional PostgreSQL
Set DATABASE_URL to a PostgreSQL URL. The included persistence layer uses SQLite
by default for local development and PostgreSQL in production.

## Production checklist
- HTTPS reverse proxy
- PostgreSQL
- Redis/background jobs for long simulations
- Object storage for uploaded datasets
- OAuth/OIDC authentication
- Secrets manager
- Rate limiting
- Audit logging
- OpenTelemetry/Sentry
- Verified domain datasets
- Human approval before operational execution
- Formal model validation for each deployed domain
