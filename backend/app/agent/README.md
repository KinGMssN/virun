# Virun Agent — backend

Agentic travel assistant: one chat endpoint with a bounded tool-calling loop.

## Files (all new, nothing existing was modified)

- `app/agent/router.py` — `POST /api/agent/chat`, `GET /api/agent/hotels`, `GET /api/agent/cities`
- `app/agent/service.py` — agentic loop (Groq tool-calling when configured, rule-based mock fallback)
- `app/agent/tools.py` — `search_hotels` (reads `frontend/resources/datasets/hotels/*.json`, OpenStreetMap ODbL), `rapido_handoff` (deep-link candidates only — no public booking API exists), `tracking_session`
- `app/schemas/agent.py` — request/response models

## Wire-up (one line, in `app/main.py`)

```python
from app.agent.router import router as agent_router
app.include_router(agent_router)
```

## Env

- `GROQ_API_KEY` + `GROQ_MODEL` — live tool-calling mode (same vars the concierge already uses)
- `HOTELS_DIR` — override path to the hotels dataset (default: `frontend/resources/datasets/hotels/`)
- Without the Groq vars the agent runs in **mock** mode and says so in every response.

## Honest limits

- Hotel "booking" is a mock until the team connects a real booking API (e.g. Amadeus).
- Rapido publishes no third-party booking API; the tool returns deep-link candidates for verification against the installed app.
- Live tracking is browser GPS (`watchPosition`) on the frontend; the backend stores no positions in this demo.
