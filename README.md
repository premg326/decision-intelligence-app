# SHADOW — Decision Intelligence Engine

> **Model a decision, not a demo.**

SHADOW is a decision-intelligence platform that helps users understand the potential consequences of real-world decisions before acting.

Instead of simply generating a recommendation, SHADOW models a decision as a dynamic dependency graph, simulates how changes propagate through the system, identifies uncertainty and critical paths, and allows users to explore stress scenarios, counterfactuals, and possible interventions.

---

## 🚀 What is SHADOW?

Real-world decisions rarely have a single consequence.

A decision such as:

> "Should I open a coffee shop near a college campus?"

can affect:

- Customer demand
- Revenue
- Rent
- Operating costs
- Staffing
- Capital requirements
- Competition
- Long-term profitability
- Risk

SHADOW converts this kind of natural-language scenario into a structured decision model.

### Core Pipeline

```text
User Decision
      ↓
AI-assisted Parsing
      ↓
Entities & Assumptions
      ↓
Dependency Graph
      ↓
Simulation
      ↓
Risk & Impact Analysis
      ↓
Stress Testing
      ↓
Counterfactuals
      ↓
Interventions
      ↓
Decision Report
✨ Features
1. Natural-Language Decision Input

Users can describe a decision in ordinary language.

Example:

I am considering opening a small coffee shop near a college campus.

Additional information can include:

Objective
Domain
Context
Available data
Constraints
Assumptions
2. AI-Assisted Decision Parsing

SHADOW extracts meaningful entities and relationships from the supplied scenario.

For example:

Coffee Shop
     ↓
Customer Demand
     ↓
Revenue
     ↓
Profitability

Other factors may include:

Rent
Operating Costs
Capital
Employees
Competition
Customers

The system keeps unknown information explicit rather than silently treating missing information as fact.

3. Dynamic Consequence Graph

SHADOW generates a dependency graph based on the supplied scenario.

Each node represents an entity or factor, while edges represent relationships between them.

Example:

             Customer Demand
                    ↓
                 Revenue
                ↙      ↘
             Costs     Profit
               ↓
           Employees

The graph is generated from the supplied scenario rather than relying only on a fixed predefined industry scenario.

4. Simulation Engine

The simulation engine propagates dependencies through the generated decision model.

It produces measurable outputs such as:

Impact
Risk
Affected nodes
Dependency depth
Uncertainty
Critical paths
5. Stress Testing

Users can explore how the decision behaves when important assumptions change.

Examples:

What if rent increases by 20%?

What if customer demand decreases?

What if ingredient costs increase?

What if competition becomes stronger?

This helps identify fragile assumptions and potential failure points.

6. Counterfactual Analysis

SHADOW allows users to explore alternative scenarios.

Instead of asking only:

"What happens if I make this decision?"

the system can examine:

"What happens if an important assumption changes?"

This makes it possible to compare different possible futures.

7. Intervention Analysis

The platform identifies possible intervention points in the dependency graph.

For example:

Reduce Rent
     ↓
Lower Operating Cost
     ↓
Lower Break-even Point
     ↓
Reduced Financial Risk

This helps users understand where changing one factor can influence downstream consequences.

8. Perspectives

The analysis can be examined from different perspectives rather than relying on a single output.

This helps users understand how a decision affects different parts of the modeled system.

9. Decision Report

SHADOW can generate a structured report containing the major findings of the analysis.

The report can include:

Decision summary
Major entities
Impact
Risk
Critical paths
Uncertainty
Important assumptions
Scenario results
Potential interventions
10. Feedback Loop

SHADOW includes a feedback mechanism for recording predicted versus actual outcomes.

This creates the foundation for improving decision models using real-world outcomes over time.

Prediction
    ↓
Real-world Outcome
    ↓
Feedback
    ↓
Future Model Improvement
🧠 Design Philosophy

SHADOW follows three important principles.

1. Model the Decision

The system focuses on understanding the structure of a decision rather than simply producing a generic answer.

2. Make Uncertainty Visible

Unknown information should remain an assumption or uncertainty rather than being presented as a fact.

3. Explore Consequences

A decision should be examined through multiple possible scenarios instead of a single static prediction.

🏗️ Architecture
┌─────────────────────────────────┐
│            FRONTEND             │
│          Next.js / React        │
│                                 │
│  Decision Input                 │
│  Analysis Dashboard             │
│  Graph Visualization            │
│  Stress Testing                 │
│  Counterfactuals                │
│  Reports / Feedback             │
└────────────────┬────────────────┘
                 │
                 │ HTTPS / JSON
                 ▼
┌─────────────────────────────────┐
│             BACKEND             │
│              FastAPI            │
│                                 │
│  API Routes                     │
│  AI Parsing                     │
│  Simulation Engine              │
│  Reporting                      │
│  Feedback Storage               │
└────────────────┬────────────────┘
                 │
          ┌──────┴──────┐
          ▼             ▼
┌────────────────┐ ┌────────────────┐
│  AI Services   │ │  Data / Store  │
│                │ │                │
│  Gemini API    │ │  SQLite / DB   │
└────────────────┘ └────────────────┘
🛠️ Technology Stack
Frontend
Next.js
React
TypeScript
React Flow
CSS / Tailwind-based styling
Backend
Python
FastAPI
Pydantic
Uvicorn
AI
Google Gemini API
AI-assisted scenario parsing
Structured decision extraction
Data
SQLite
Structured JSON models
Feedback storage
Deployment
Vercel — Frontend
Render — Backend
GitHub — Source Control
📁 Project Structure
decision-intelligence-app/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── engines/
│   │   ├── models/
│   │   ├── services/
│   │   ├── __init__.py
│   │   └── main.py
│   │
│   ├── tests/
│   ├── .env
│   ├── .env.example
│   ├── python-version
│   ├── Dockerfile
│   ├── requirements.txt
│   └── shadow.db
│
├── docs/
│
└── README.md

Note: .env contains secrets and should never be committed to GitHub. Use .env.example for required variable names.

🔌 API

The backend exposes REST endpoints for the major decision-intelligence operations.

Endpoint	Method	Purpose
/health	GET	Backend health check
/api/parse	POST	Parse a decision
/api/simulate	POST	Run decision simulation
/api/compare	POST	Compare scenarios
/api/report	POST	Generate a decision report
/api/feedback	POST	Store decision feedback
⚙️ Local Development
Prerequisites

Install:

Node.js
Python 3.11+
Git
1. Clone the Repository
git clone https://github.com/premg326/decision-intelligence-app.git
cd decision-intelligence-app
Frontend Setup
cd frontend
npm install

Create:

frontend/.env.local

Add:

NEXT_PUBLIC_API_URL=http://localhost:8000

Run:

npm run dev

Frontend:

http://localhost:3000
Backend Setup

Open another terminal:

cd backend

Create a virtual environment.

Windows
python -m venv .venv
.venv\Scripts\activate
macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt
🔐 Environment Variables

Create:

backend/.env

Example:

GEMINI_API_KEY=your_gemini_api_key

CORS_ORIGINS=http://localhost:3000

For production, use your deployed frontend URL:

CORS_ORIGINS=https://your-vercel-domain.vercel.app

Never commit API keys or .env files to GitHub.

▶️ Start the Backend
uvicorn app.main:app --reload --port 8000

Backend:

http://localhost:8000

Health check:

http://localhost:8000/health
🌐 Production Deployment

SHADOW uses a two-service deployment architecture.

                    Internet
                       │
                       ▼
              ┌─────────────────┐
              │     Vercel      │
              │ Next.js Frontend│
              └────────┬────────┘
                       │
                       │ HTTPS API
                       ▼
              ┌─────────────────┐
              │     Render      │
              │ FastAPI Backend │
              └────────┬────────┘
                       │
                       ▼
                 AI Services
Frontend — Vercel

Deploy the frontend directory using Vercel.

Set the environment variable:

NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-URL

Example:

NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
Backend — Render

Deploy the backend directory using Render.

Required environment variables:

GEMINI_API_KEY=your_gemini_api_key

and:

CORS_ORIGINS=https://YOUR-VERCEL-DOMAIN.vercel.app

The backend should run using:

uvicorn app.main:app --host 0.0.0.0 --port $PORT
🔒 Security

SHADOW separates the frontend from the backend.

Frontend
   ↓
HTTPS API
   ↓
Backend
   ↓
AI Services

API keys are kept server-side and should never be exposed in frontend code.

Environment variables are used for:

AI API credentials
CORS configuration
Other deployment-specific settings
🧪 Example Scenario
Input
Decision
I am considering opening a small coffee shop near a college campus.
Objective
Maximize monthly profit while keeping financial risk manageable.
Domain
Food & beverage
Context / Data
Student foot traffic is high during weekdays but lower on weekends.
Rent is increasing, nearby competitors are offering discounts,
ingredient costs are rising, and customer demand may vary during
exam periods. I have limited initial capital and would need to
hire two employees.
SHADOW Model

The system can identify factors such as:

Customer Demand
Rent
Capital
Operating Costs
Employees
Customers
Competition

The resulting analysis can expose:

Impact
Risk
Uncertainty
Critical paths
Dependency levels
Potential interventions
Scenario outcomes
📊 Example Analysis

A generated SHADOW analysis may contain:

Impact Score
Risk Score
Affected Nodes
Cascade Levels
Uncertainty Range
Critical Paths

The dependency graph allows users to visually inspect how factors influence one another.

Example:

Opening Coffee Shop
        │
        ├──────────────► Customer Demand
        │                       │
        │                       ▼
        │                    Revenue
        │                       │
        ├──────────────► Operating Costs
        │                       │
        │                       ▼
        │                    Profit
        │
        ├──────────────► Rent
        │
        ├──────────────► Capital
        │
        └──────────────► Employees
🎯 Use Cases

SHADOW can be adapted to scenarios such as:

Business planning
Startup decisions
Financial planning
Operations
Supply chains
Resource allocation
Project planning
Risk analysis
Strategic planning
What-if analysis
🔮 Future Improvements

Potential future development includes:

More advanced probabilistic simulation
Larger decision-model libraries
Historical outcome learning
More sophisticated causal modeling
Multi-user collaboration
Persistent cloud storage
Advanced scenario comparison
Domain-specific models
Improved uncertainty quantification
User authentication and workspaces
💡 Why SHADOW?

Traditional decision tools often focus on:

Input → Recommendation

SHADOW focuses on:

Decision
   ↓
Dependencies
   ↓
Consequences
   ↓
Scenarios
   ↓
Risks
   ↓
Interventions

The goal is to make the structure, dependencies, uncertainty, and potential consequences of a decision easier to understand.

👥 Project
SHADOW — Decision Intelligence Engine

A decision-analysis platform combining:

AI
+
Dependency Modeling
+
Simulation
+
Risk Analysis
+
Counterfactual Reasoning
📄 License

This project is currently intended for educational, research, and hackathon development purposes.

If the project is later released as open source, an appropriate open-source license can be added here.

⭐ Project Status

Frontend: Deployed on Vercel
Backend: Deployed on Render
AI Integration: Gemini API
Source Code: GitHub

SHADOW — Before you act, see the cascade.
