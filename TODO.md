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
- [x] API keys are read from ignored `backend/.env`; `.env.example` contains blank secret placeholders.

## Still required before production

- [ ] Choose and contract a live bus provider that supplies schedules, fares, and inventory; add its credentials and integration.
- [ ] Decide which account roles to support and select an identity/authentication provider; implement server-side registration, sessions, and authorization. Current frontend role selection and demo checks are not secure authentication.
- [ ] Select and provision a production database; implement migrations and persistent user, guide, trip, booking, and review data with access controls. The current JSON planner and optional Supabase repository do not provide those product records.
- [ ] Choose a booking provider and implement confirmed booking, cancellation, and status synchronization. Until then, the app is a planner and must not claim a reservation was made.
- [ ] Choose a payment processor and implement server-side payment intents, verified webhooks, refunds, and state transitions before accepting payments. Do not collect or store card details in this app.
- [ ] Either integrate an approved identity-verification service with a reviewed sensitive-data process or remove identity-verification claims and controls.
- [ ] Either implement guide discovery, availability, requests, messaging, trip tracking, and emergency workflows or keep those screens clearly marked as demo-only.
- [ ] Replace remaining sample destination, guide, review, pricing, weather, and dashboard content with verified sources or ensure every affected screen labels it as sample content.
- [ ] Create the Render project, add private Groq and RailRadar environment secrets, set production CORS origins, connect a domain, and configure monitoring, backups, and operational alerts. The project has not been created from this workspace.
- [ ] Review and publish accurate privacy policy, terms, support contact, data-retention/deletion procedures, and applicable legal requirements before collecting user data or payments.
- [ ] Run the complete backend test suite and application-level smoke tests in a standard CPython environment. This workspace's MSYS Python has no compatible Pydantic Core wheel; installing dependencies falls back to a Rust build, but Rust is unavailable. Live provider checks above succeeded independently.

## Current data and product boundaries

Groq powers natural-language trip parsing when configured. RailRadar provides real train schedules and live status when available; the live station and timetable calls were checked on 2026-10-10. It does not provide fares, seat inventory, or booking in this integration. Bundled planner and bus routes remain simulated and use fixed sample data. Authentication, guide workflows, payment, and booking are not production services yet.

## Credentials

Keep `GROQ_API_KEY` and `RAILRADAR_API_KEY` only in ignored local `.env` files or private deployment secrets. Never place values in `.env.example`, frontend code, logs, or source control.
