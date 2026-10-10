# Virun delivery checklist

Updated 2026-10-10. A checked item is limited to what exists and has been verified; it does not imply that the entire product is production-ready.

## Implemented and verified

- [x] Single-page frontend and Python API for route planning, trip recovery, transport listing, health, and natural-language trip parsing.
- [x] Groq adapter configured through `GROQ_API_KEY` and `GROQ_MODEL`, with a server-side OpenAI-compatible client and JSON output mode.
- [x] Groq live check passed using the local key and configured model; it returned the requested JSON response.
- [x] RailRadar station lookup and live train search endpoints; live station lookup and VSKP–SC timetable request passed using the local key (11 train records returned).
- [x] Rail results clearly omit fares, seat inventory, and booking because the configured provider does not supply those services.
- [x] Bundled transport data is identified as simulated; bus fares and availability are not represented as live.
- [x] Render blueprint, Docker configuration, CI workflow, Supabase schema/seed/repository option, and integration setup docs are present.
- [x] SQLAlchemy models and an Alembic bootstrap migration define the relational app schema, including transport tables.
- [x] Groq-generated stay plans are persisted as `sightseeing` records in `public.itineraries`, with the generated day plan stored as JSONB and no invented transport fare or duration; generated plans remain visible in the Itinerary page and are clearly labeled if the database save fails.
- [x] Supabase email/password and Google login use real Auth calls, redirect to the tourist dashboard by default, and support a safe internal `returnTo` route.
- [x] Privacy and cookie notices, account-processing consent, and a persistent essential/optional cookie preference banner are present. No analytics tracker is active.
- [x] Stay plans query real nearby OpenStreetMap places, cache and throttle public lookups, show map links and attribution, and avoid inventing venue names when lookup data is unavailable.
- [x] Card entry has been removed from the payment preview; identity and government screens now clearly state that no real provider/access control is connected.
- [x] Email/password registration and sign-in call Supabase Auth, Google OAuth uses the Supabase PKCE flow, and cookie/privacy disclosures describe current data flows.
- [x] API frontend serving and Docker packaging use the single frontend entry point under `frontend/index.html`.
- [x] API keys are read from ignored `backend/.env`; `.env.example` contains blank secret placeholders.

## Still required before production

- [ ] Choose and contract a live bus provider that supplies schedules, fares, and inventory; add its credentials and integration.
- [ ] Add SUPABASE_URL and the anon/public SUPABASE_KEY to local and Render environments, configure Supabase Email Auth redirect URLs, then verify sign-up, confirmation, sign-in, refresh, and sign-out with a real test account.
- [ ] Define and enforce account roles and server-side authorization for protected workflows. Supabase email/password sign-up and sign-in forms are implemented, but guide/government/admin screens are still previews and are not protected.
- [ ] Add the Supabase PostgreSQL `DATABASE_URL` and apply/verify the latest Alembic migration (`alembic upgrade head`; Render's Docker startup runs it automatically). Runtime Supabase REST keys are still blank; private-table RLS policies and account-scoped itinerary retrieval remain to be implemented.
- [ ] Choose a booking provider and implement confirmed booking, cancellation, and status synchronization. Until then, the app is a planner and must not claim a reservation was made.
- [ ] Choose a payment processor and implement server-side payment intents, verified webhooks, refunds, and state transitions before accepting payments. Do not collect or store card details in this app.
- [x] Identity verification controls were removed from the frontend preview; no document submission is offered.
- [x] Guide discovery, requests, trip tracking, chat, and emergency controls are labeled as sample or non-live preview flows.
- [x] Sample guide, review, pricing, dashboard, and destination visuals are identified as sample/preview content; no live weather forecast is claimed.
- [ ] Create the Render project, add private Groq and RailRadar environment secrets, set production CORS origins, connect a domain, and configure monitoring, backups, and operational alerts. The project has not been created from this workspace.
- [ ] Have the deployment operator review the privacy/cookie notices and terms, add a real support contact, define data-retention/deletion procedures, and review applicable legal requirements before public launch.
- [ ] Run the complete backend test suite and application-level smoke tests in a standard CPython environment. This workspace's MSYS Python has no compatible Pydantic Core wheel; installing dependencies falls back to a Rust build, but Rust is unavailable. Live provider checks above succeeded independently.

## Current data and product boundaries

Groq powers natural-language trip parsing and stay suggestions when configured. RailRadar provides real train schedules and live status when available; it does not provide fares, seat inventory, or booking in this integration. Stay plans show nearby named OpenStreetMap features when available; opening status and completeness are not guaranteed. Bundled planner and bus routes remain simulated and use fixed sample data. Supabase Auth is integrated but needs live configuration verification; guide role enforcement, payment, and booking are not production services yet.

## Credentials

Keep `GROQ_API_KEY`, `RAILRADAR_API_KEY`, `SUPABASE_KEY`, and `DATABASE_URL` only in ignored local `.env` files or private deployment secrets. Never place values in `.env.example`, frontend code, logs, or source control. The local `backend/.env` currently has an empty `DATABASE_URL`; configure it before expecting database persistence locally.
