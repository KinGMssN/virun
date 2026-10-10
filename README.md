# Virun — frontend preview

Live site: https://kingmssn.github.io/virun/

## What is here

- `index.html` — the whole frontend in one file (HTML + CSS + JS, no build step).
  Open it via any static server, e.g. `python3 -m http.server`, then visit
  `http://localhost:8000/`. GitHub Pages serves this file as the site.
- `resources/images/` — all pictures the site uses, organized by city:
  `kashmir/`, `goa/`, `hyderabad/`, `visakhapatnam/`, `mumbai/`, `delhi/`,
  `bengaluru/` (each with `photos/`), plus `chatbot/` (mascot) and `ui-art/`.
  Every folder has an `ATTRIBUTION.md` saying where its pictures came from.
- `.nojekyll` — tells GitHub Pages to serve the files as-is (no Jekyll build).
- `backend/` — the team's API work (separate from this frontend).

## Frontend notes

- Seven city themes: Kashmir, Goa, Hyderabad, Visakhapatnam, Mumbai, Delhi,
  Bengaluru. City data lives in `cityData` / `cityPhotoCounts` near the top
  of the `<script>` in `index.html`.
- Destination cards show **live weather** from Open-Meteo (no API key needed).
- The floating Virun bot is fixed bottom-right; tap it to open the chat panel.
- The itinerary page is a 3-step frontend wizard (city + interests → generate
  → three plan options). Real generation will come from the backend.
- "Sign in with Google" on the sign-in page is a frontend button for now;
  the backend team is wiring the real login.

## Picture credits

- Kashmir / Hyderabad / Visakhapatnam / Goa (`goa_01`–`goa_15`): real photos
  from Wikimedia Commons, freely licensed (see each folder's ATTRIBUTION.md).
- Goa hero (`goa_beach_hero.jpg`) and all Mumbai / Delhi / Bengaluru photos:
  AI-generated for this project.
