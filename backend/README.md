# TBS RoamAgent — Deterministic Route Planner (Member 3)

All fares, timestamps and feasibility are calculated here. **No LLM is involved.**
Bundled data is **SIMULATED** (fictional schedules/fares/availability).

## Run it
```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload                             # http://127.0.0.1:8000
pytest                                                    # no database needed
```
The root URL serves the Virun frontend. Journey search uses `/api/plan`, and the
chat panel parses free-text requests through `/api/parse-trip` before checking them
with the planner. API documentation is at `http://127.0.0.1:8000/docs`; bundled
images are served under `/resources/`. Copy `.env.example` to `.env` to configure
the concierge and integrations. The planner works with bundled JSON data without
external credentials. Set `RAILRADAR_API_KEY` locally and as a private Render
service environment variable to enable real train timetables and live status. The
frontend uses one primary station code per listed city; edit its mapping if you
need another station. The provider key stays on the backend and never belongs in
frontend code.
Try it:
```bash
curl -X POST http://127.0.0.1:8000/api/plan -H "Content-Type: application/json" -d @docs/sample_request.json
curl http://127.0.0.1:8000/api/transport/options
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| POST | `/api/plan` | Body = `TripRequest`. 200 + `itineraries`, or `{"error": {...}}` (404 `NO_FEASIBLE_ROUTE`, 422 `INVALID_REQUEST` / `UNKNOWN_LOCATION`) |
| POST | `/api/plan/recover` | Body = `{"trip_request": TripRequest, "unavailable_leg_ids": [...]}`; replans while excluding disrupted legs |
| GET | `/api/transport/options` | All records incl. cancelled/sold-out, with `data_source`. Optional filters: `origin_stop_id`, `destination_stop_id`, `mode` |
| GET | `/api/rail/stations?q=Visakhapatnam` | Real railway station lookup through RailRadar; requires `RAILRADAR_API_KEY` |
| GET | `/api/rail/trains?from_station=VSKP&to_station=SC&travel_date=2026-10-11` | Real train timetable and live status/delay when available. RailRadar does not return fares, seat inventory, or booking. |
| GET | `/` | Virun single-file frontend |
| GET | `/resources/...` | Frontend images and other bundled resources |
| GET | `/health` | liveness |

Sample JSON (generated from the real planner): `docs/sample_request.json`, `sample_response.json`,
`sample_error_no_feasible_route.json`, `sample_error_invalid_request.json`.
Regenerate with `python scripts/generate_samples.py`.

## Reusable function (Member 4)
```python
from app.planner.service import plan_trip
result = plan_trip(trip_request, unavailable_leg_ids=["BUS-DEMO-002"])   # TripRequest or dict
if result.error: ...            # result.error.code / message / details
else: result.itineraries        # list[Itinerary]
```
It never raises for bad input; it returns `PlanResponse(error=...)`. Do **not** write a second planner.

## Rules (single source of truth: `app/planner/algorithms.py`)
| Topic | Rule |
|---|---|
| Fare | `total = Σ(leg fare + luggage fee if has_luggage) × passengers`. Flat per-passenger fares. Frontend totals are ignored. |
| Budget | `budget_inr` is a hard limit on the **total for all passengers**. |
| Departure | First leg must depart on/after 00:00 of `departure_date` (request timezone). |
| Transfer | Next leg departs ≥ previous arrival + **30 min** (+**15 min** with luggage). |
| Deadline | Arrival must be ≤ `arrival_deadline`. `arrival_buffer_minutes = deadline − arrival`. |
| Excluded legs | status other than `available_in_demo`/`available`, or id in `unavailable_leg_ids`. |
| Duration | final arrival − first departure (includes waits). |
| Risk | `1 − Π(leg reliability) + 0.05×transfers + 0.10 if buffer < 30 min`; low < 0.15 ≤ medium < 0.30 ≤ high. |
| Cheapest | min total fare (ties: duration, arrival, route key) |
| Fastest | min duration (ties: fare, arrival, route key) |
| Lowest risk | min risk score (ties: fare, duration, route key) |
| Balanced | min of `0.35·fare + 0.30·duration + 0.20·risk + 0.10·transfers + 0.05·comfort` (first four min-max normalised over feasible routes, 0 = best). Comfort = soft penalty for bus legs not matching `bus_preference` and non-AC legs when AC is preferred. Required AC and non-AC preferences are hard constraints. |
| Duplicates | A route that wins several categories is returned once with all labels (`labels`, `label`). `priority` only changes the order. |
| Bounds | 1–10 passengers, max 3 legs, max 500 candidates (`search_truncated` is reported on failure). |

Weights and buffers live in `PlannerConfig`.

## Repository switch (JSON → Supabase)
`TRANSPORT_REPOSITORY=json` (default) or `supabase` (set `SUPABASE_URL`, `SUPABASE_KEY`).
For this read-only planner repository, use the Supabase anon/public key with the included
read-only row-level security policies; never use a `service_role` key in this app.
Schema: `supabase/migrations/001_initial_schema.sql`; seed: `supabase/seed_demo_data.sql`
(regenerate with `python scripts/generate_seed_sql.py`). The planning code does not change.
The Supabase repository has offline contract tests using a fake client, including pagination.
A live Supabase check still requires a configured project and credentials; do not put its
service key in source control.

## Docker and Render
From the repository root:
```bash
docker build -f backend/Dockerfile -t virun .
docker run --rm -p 8000:8000 -e CORS_ORIGINS=http://localhost:8000 virun
```
Open `http://localhost:8000`. For Render, use the included `render.yaml` blueprint and
set `CORS_ORIGINS`, `GROQ_API_KEY`, `GROQ_MODEL`, and the private `RAILRADAR_API_KEY` in the
service environment. The blueprint requests the RailRadar key as a secret and does not
store its value in source control. The backend CI workflow runs the test suite on Python
3.11 and 3.12 and builds the Docker image.

## Known limitations
* Bundled planner data is synthetic, covers one corridor (Visakhapatnam to Hyderabad), and uses fixed dates. RailRadar results are separate and appear only when its key is configured.
* RailRadar can provide train timetables and live running status when configured. It does not provide fare quotes, seat counts or booking in this integration. Bus data remains synthetic; passenger count does not check seat inventory.
* Only whole-minute precision; one flat per-passenger fare rule; no taxes/fees besides the luggage fee.
* Place names resolve via exact stop id / name / alias match (no fuzzy matching). "Hyderabad" resolves to the hub `HYD-DEMO`.
* Search is capped (3 legs / 500 candidates) to stay fast.
* Supabase pagination and schema mapping are covered by offline fake-client tests; the
  repository has not been exercised against a live database. RailRadar calls also need
  an API key and have not yet been verified from this workspace.
