# Virun demo: run, deploy, show

Demo only. No real booking, payment, KYC verification, or payout happens here.

## Run locally

```bash
cd backend
python -m uvicorn app.main:app
```

Open http://127.0.0.1:8000

- Home page: choose Tourist or Guide, or Sign in / Create Account.
- Sign in demo: enter a name, choose Tourist or Guide, continue. The demo
  password is not checked or sent. Google sign-in needs Supabase configured
  on the backend, and will show that error until then.
- Tourist dashboard: Find a guide, Request guide, see My guide requests.
- Guide dashboard: see Requests from tourists, toggle known cities and
  availability. Both save in this browser only.
- Guide Requests page: Accept or Reject a tourist request made in the
  same browser. With no request, a sample request is shown.

## Deploy on Render

The root `render.yaml` is set for demo: `TRANSPORT_REPOSITORY=json`,
`USE_MOCK_PARSER=true`, `ENABLE_MOCK_FALLBACK=true`, so it runs without
Groq, Supabase, or RailRadar keys. Database migration only runs when
`DATABASE_URL` is set.

## Still not done, do not claim as live

Booking, payment and escrow, KYC and guide verification, live bus fares
and inventory, Supabase live verification, production Render project, and
4 backend tests that were already failing before this change.

## Reset demo data completely

Tap "Reset demo data" on the home page hero, or in the footer on any
public page. It asks for confirmation, then clears in this browser only:
demo login, signup name, email and role, guide requests, known cities,
availability, journey, and cookie choice. It does not delete the
transport dataset, place data, or any code, because the planner needs
those to run. No real account is created in the demo, so there is no
backend account to delete. After reset, the home page opens clean, and
you can sign in again with fake demo details.
