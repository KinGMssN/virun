# TBS RoamAgent — Deterministic Route Planner (Member 3)

Transport fares, timestamps and feasibility are calculated by the deterministic planner;
Groq is used only for natural-language parsing and AI-generated sightseeing suggestions.
No transport fixture is used by default. Set `TRANSPORT_REPOSITORY=json` only when you explicitly want the development sample dataset.

## Run it
```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload                             # http://127.0.0.1:8000
pytest                                                    # no database needed
```
In the monorepo, the backend serves `../frontend/index.html`; a standalone
backend checkout uses its local `frontend/index.html`. Both serve the UI and its
image assets from port 8000.
For the standalone frontend/API proxy preview, start the backend on port 8000,
then from the repository root run:
```bash
python backend/scripts/local_frontend_proxy.py             # http://127.0.0.1:8001
```
The root URL serves the Virun frontend from `../frontend/`. General text and voice
questions use `/api/chat` and Groq, with up to eight recent conversation turns. The stay-plan
and saved-itinerary pages show verified OpenStreetMap places on a Leaflet map. Trip
requests ask for a 1–15 day destination stay, parse details with Groq, check transport,
and request a separate day-by-day sightseeing suggestion. API documentation is at
`http://127.0.0.1:8000/docs`; bundled
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
| POST | `/api/chat` | Groq-backed assistant reply; accepts a message and up to 8 recent turns |
| POST | `/api/parse-trip` | Groq extracts trip constraints and asks for missing details |
| POST | `/api/generate-itinerary` | Groq creates validated sightseeing suggestions with named places from nearby OpenStreetMap results; returns 503 when verified place lookup finds none |
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
`TRANSPORT_REPOSITORY=empty` (default; no fabricated results), `json` (explicit sample dataset for development), or `supabase` (set `SUPABASE_URL`, `SUPABASE_KEY`).
For this read-only planner repository, use the Supabase anon/public key with the included
read-only row-level security policies; never use a `service_role` key in this app.
The SQL file under `supabase/migrations/` is the legacy transport-only schema. New schema
creation uses the SQLAlchemy/Alembic migration below. The planner contract does not change.
The Supabase repository has offline contract tests using a fake client, including pagination.
A live Supabase check still requires a configured project and credentials; do not put its
service key in source control.

## Relational schema (SQLAlchemy + Alembic)

SQLAlchemy models live in `app/db/models.py`; Alembic creates schema changes. The first
migration creates the app tables and enables RLS. Private account/trip tables have no
PostgREST policies yet, so they remain inaccessible through Supabase's API until
authentication and authorization are implemented. Supabase Auth owns `auth.users`.

The public schema tables are `profiles`, `roles`, `profile_roles`, `guide_profiles`,
`guide_languages`, `guide_profile_languages`, `guide_services`, `guide_availability`,
`destinations`, `attractions`, `trip_requests`, `itineraries`, `itinerary_legs`,
`bookings`, `booking_legs`, `payments`, `reviews`, `conversations`,
`conversation_participants`, `messages`, `trip_events`, `transport_stops`, and
`transport_options`. The migration references Supabase Auth's `auth.users` table but
never creates or drops it.

To apply the schema to Supabase PostgreSQL, put its PostgreSQL connection URI in
`DATABASE_URL` in the ignored `.env` file, then run from `backend/`:

```bash
alembic upgrade head
```

Migration `0002_generated_sightseeing_itineraries` extends `public.itineraries` to
store Groq stay plans (`itinerary_type='sightseeing'`, `data_source='GROQ'`) and
their validated day-by-day JSON in `generated_content`. A generated plan is saved
only after the database commit succeeds. Ensure this migration is applied before
using `/api/generate-itinerary`; the Render Docker startup runs Alembic on deploy.
If persistence is unavailable, the API still returns the generated plan with
`saved_to_database=false` and a safe `save_error`; the frontend displays it and keeps
a browser-local copy. Cross-device, account-scoped itinerary retrieval still needs
authenticated CRUD.

Stay plans query OpenStreetMap's Nominatim geocoder and Overpass place data for
named places within 7 km of the selected city/area. Responses are cached in memory
for six hours, requests are throttled, and the frontend links to OpenStreetMap
attribution. The public services are best-effort and can return no places; the AI
prompt then avoids naming specific venues. Set `OSM_NOMINATIM_URL` and
`OSM_OVERPASS_URL` to alternate compatible endpoints if requested by those services.

Authentication screens use Supabase Auth email/password and Google OAuth. A safe
internal return route can be requested as `#/signin?returnTo=itinerary`; external
redirect URLs are rejected. OAuth callbacks default to the tourist dashboard.
Cookie choices are saved in local storage; no analytics or advertising tracker is
currently installed. The privacy and cookie pages describe the current provider
flows and browser storage.

For local development only, the demo seed script can load simulated records. Do not use it for live data:

```bash
python scripts/seed_transport_database.py
```

`DATABASE_URL` is the database connection URI (including its database password), not
the Supabase anon API key. Keep both private. The runtime planner uses `SUPABASE_URL`
and `SUPABASE_KEY` when `TRANSPORT_REPOSITORY=supabase`.
Use the Supabase PostgreSQL URI (not its API URL or anon key). SQLAlchemy is configured
to use psycopg 3; `postgres://` and `postgresql://` URLs are normalized automatically.
If the database password contains reserved URI characters, URL-encode them before
putting the URI in `.env` or Render's environment settings.

Google sign-in uses Supabase Auth OAuth with PKCE. Set `SUPABASE_URL` and
`SUPABASE_KEY` (the anon/public key) in `backend/.env` and in Render. The backend
auth config endpoint refuses to expose a service-role/secret key. In Supabase,
enable Google under Authentication > Providers and add the project's Supabase
callback URL (`https://<project-ref>.supabase.co/auth/v1/callback`) to the Google
OAuth client's authorized redirect URIs. Add `http://127.0.0.1:8001` and your
Render app origin as authorized JavaScript origins. Under Authentication > URL
Configuration, allow `http://127.0.0.1:8001/**` and your Render origin. The OAuth
redirect itself does not need the application database; profile persistence and
role-based authorization are separate work still pending.

## Docker and Render
From the repository root:
```bash
docker build -f backend/Dockerfile -t virun .
docker run --rm -p 8000:8000 -e CORS_ORIGINS=http://localhost:8000 virun
```
Open `http://localhost:8000`. For Render, use the included `render.yaml` blueprint and
set `CORS_ORIGINS`, `GROQ_API_KEY`, `GROQ_MODEL`, and the private `RAILRADAR_API_KEY` in the
service environment. Set `GROQ_API_KEY` to your Groq API key and leave `USE_MOCK_PARSER`
unset or `false` to enable Groq. The blueprint sets `GROQ_MODEL` to
`openai/gpt-oss-20b`. Set `MODEL_TIMEOUT_SECONDS` to a private service variable only if
you need a non-default timeout (default 60 seconds). The blueprint requests provider
keys as secrets and does not store their values in source control. The backend CI workflow runs the test suite on Python
3.11 and 3.12 and builds the Docker image.

## Three-part travel flow

The frontend guides a traveler through Going (RailRadar outbound trains), Staying (a Groq-generated day plan using required days, nights, and budget inputs), and Returning (RailRadar trains back to the origin). RailRadar does not provide fare quotes, seat inventory, or booking. Groq itinerary suggestions are not verified price quotes or reservations.

## Known limitations
* The planner has no transport data by default. Supabase rows labeled DEMO, SAMPLE, SIMULATED, or MOCK are excluded from results. RailRadar train timetable search is available through `/api/rail`; fares, seats, and booking are unavailable.
* RailRadar can provide train timetables and live running status when configured. It does not provide fare quotes, seat counts or booking in this integration. Bus schedules are not connected.
* Only whole-minute precision; one flat per-passenger fare rule; no taxes/fees besides the luggage fee.
* Place names resolve via exact stop id / name / alias match (no fuzzy matching). Location resolution uses records from the selected repository.
* Search is capped (3 legs / 500 candidates) to stay fast.
* Supabase pagination and schema mapping are covered by offline fake-client tests; the
  repository has not been exercised against a live database. RailRadar calls also need
  an API key and have not yet been verified from this workspace.
