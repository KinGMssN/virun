# TBS RoamAgent: AI Concierge (Member 2)

Converts a natural-language travel request into a validated `TripRequest`.
It never invents fares, schedules, coordinates, availability or bookings.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in XAI_API_KEY and GROK_MODEL
uvicorn app.main:app --reload
pytest
```

## Environment variables (for Member 4 / Render)
| Variable | Purpose |
|---|---|
| XAI_API_KEY | xAI API key (server only, never commit) |
| GROK_MODEL | Grok model name from the xAI docs |
| MODEL_TIMEOUT_SECONDS | Model timeout, default 15 |
| USE_MOCK_PARSER | true = use the rule-based mock, no API calls |
| ENABLE_MOCK_FALLBACK | true = use mock when model times out / quota / errors |
| CORS_ORIGINS | Comma-separated frontend origins |

## Endpoint: POST /api/parse-trip
Request: `{"message": "...", "timezone": "Asia/Kolkata", "reference_date": "2026-10-10"}`

Response: `status` (ready | needs_clarification | error), `trip_request`,
`partial_trip_request`, `missing_fields`, `clarification_questions`, `error_code`, `fallback`.

`fallback` is `manual_entry` (show a manual form) or `mock_parser` (result came from the basic parser).

Planner receives (only when status = ready): origin, destination, departure_date,
arrival_deadline, timezone, passengers, budget_inr, bus_preference, ac_preference,
has_luggage, priority.

## Date rules
- Relative dates ("tomorrow", "next Monday") use ONLY `reference_date`. No reference_date -> ask for the date.
- Timezone defaults to Asia/Kolkata only when none is supplied.
- Vague times ("morning") are ambiguous -> ask "What time must you arrive?".
- arrival_deadline is on the same date as departure_date, unless the user says the trip is overnight / arrives next day (then +1 day).
- Invalid passengers (not 1-10) or budget (not 1-100000) are never accepted; the user is asked again.

## Known limitations
- Mock parser is English-only and basic. Telugu needs the real model.
- No live data: no fares, schedules or availability.
- Place names are plain text; matching them to real stops is the planner's job.
- Absolute dates like "15 Oct" depend on the model returning a YYYY-MM-DD date.

## Demo messages
1. I need to go from Visakhapatnam to Hitech City, Hyderabad, budget ₹1,200, sleeper bus, arrive before 9 AM tomorrow. (ready)
2. Find a low-cost journey to Hyderabad tomorrow morning. (asks origin, arrival time)
3. From Vizag, arrive before 9 AM tomorrow. (asks destination)
4. Vizag to Hyderabad tomorrow, sleeper. (asks arrival time)
5. Vizag to Hyderabad tomorrow, 0 passengers, arrive 9 AM. (asks passengers)
6. Overnight bus from Vizag to Hyderabad leaving tomorrow, arrive 7 AM. (deadline next day)
7. రేపు ఉదయం 9 లోపు విశాఖపట్నం నుండి హైదరాబాద్ (Telugu)
8. Stop the model (wrong key) and send any message. (error + manual_entry)
