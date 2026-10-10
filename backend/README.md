# TBS RoamAgent — Deterministic Route Planner (Member 3)

All fares, timestamps and feasibility are calculated here. **No LLM is involved.**
Bundled data is **SIMULATED** (fictional schedules/fares/availability).

## Run it
```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload                             # http://127.0.0.1:8000/docs
pytest                                                    # 52 tests, no database needed
```
Try it:
```bash
curl -X POST http://127.0.0.1:8000/api/plan -H "Content-Type: application/json" -d @docs/sample_request.json
curl http://127.0.0.1:8000/api/transport/options
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| POST | `/api/plan` | Body = `TripRequest`. 200 + `itineraries`, or `{"error": {...}}` (404 `NO_FEASIBLE_ROUTE`, 422 `INVALID_REQUEST` / `UNKNOWN_LOCATION`) |
| GET | `/api/transport/options` | All records incl. cancelled/sold-out, with `data_source`. Optional filters: `origin_stop_id`, `destination_stop_id`, `mode` |
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
| Balanced | min of `0.35·fare + 0.30·duration + 0.20·risk + 0.10·transfers + 0.05·comfort` (first four min-max normalised over feasible routes, 0 = best). Comfort = soft penalty for bus legs not matching `bus_preference` and non-AC legs when AC is preferred. |
| Duplicates | A route that wins several categories is returned once with all labels (`labels`, `label`). `priority` only changes the order. |
| Bounds | max 3 legs, max 500 candidates (`search_truncated` is reported on failure). |

Weights and buffers live in `PlannerConfig`.

## Repository switch (JSON → Supabase)
`TRANSPORT_REPOSITORY=json` (default) or `supabase` (needs `pip install supabase`, `SUPABASE_URL`, `SUPABASE_KEY`).
Schema: `supabase/migrations/001_initial_schema.sql`; seed: `supabase/seed_demo_data.sql`
(regenerate with `python scripts/generate_seed_sql.py`). The planning code does not change.

## Known limitations
* Data is synthetic and covers one corridor (Visakhapatnam → Hyderabad, 11–12 Oct 2026). Dates are fixed.
* No live fares, seat counts or real-time delays; passenger count does not check seat inventory.
* Only whole-minute precision; one flat per-passenger fare rule; no taxes/fees besides the luggage fee.
* Place names resolve via exact stop id / name / alias match (no fuzzy matching). "Hyderabad" resolves to the hub `HYD-DEMO`.
* Search is capped (3 legs / 500 candidates) to stay fast.
* `SupabaseTransportRepository` is written but **not tested against a live database**.
