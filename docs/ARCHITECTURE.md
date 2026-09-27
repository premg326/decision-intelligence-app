# SHADOW Architecture

## Principle
AI interprets; engines calculate.

## Layers
1. Experience — Next.js
2. API — FastAPI
3. Intelligence — AI parser/explainer
4. Scenario model — entities, assumptions, constraints
5. Graph — dependency network
6. Simulation — deterministic propagation
7. Stress — adversarial perturbations
8. Uncertainty — Monte Carlo
9. Optimization — interventions
10. Feedback — prediction vs actual

## Domain neutrality
No road, city, company, hospital, policy, or other specific scenario is encoded
in the backend or frontend. Scenarios are supplied by the user/AI parser.

## Production extensions
Use verified domain adapters for external datasets. A domain adapter should
translate authoritative data into entities, variables and relationships without
putting domain assumptions into the core engine.
