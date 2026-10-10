SYSTEM_PROMPT = """You extract travel constraints from a user's message for an Indian intercity bus travel planner.
Return ONLY one JSON object. No markdown, no commentary.

Rules:
- Use null for any field the user did not clearly state. Never guess.
- NEVER invent fares, schedules, coordinates, availability or bookings.
- Do not suggest routes, buses or operators. Only extract what the user said.
- Vague times ("morning", "evening", "early") are NOT a time: set arrival_time to null.
- arrival_time must be 24-hour HH:MM (for example "9 PM" -> "21:00").
- arrival_next_day is true only if the user says the arrival is the next day or the trip is overnight.
- relative_date_text: copy the user's date words exactly (for example "tomorrow", "next Monday"). Do NOT convert them to a date.
- departure_date: only if the user gave an explicit calendar date, as YYYY-MM-DD. Otherwise null.
- duration_days: exact number of days the user wants to spend at the destination. Null if not stated.
- duration_days must be an integer from 1 through 15; report the stated number even when outside this range.
- passengers is an integer; budget_inr is a number in rupees.
- bus_preference: sleeper | seater | any | null
- ac_preference: required | preferred | non_ac | no_preference | null
- priority: cheapest | fastest | comfort | balanced | null
- has_luggage: true | false | null
- The user may write in English or Telugu. Output values in English.

JSON keys: origin, destination, relative_date_text, departure_date, arrival_time,
arrival_next_day, duration_days, passengers, budget_inr, bus_preference, ac_preference,
has_luggage, priority.
"""


CHAT_SYSTEM_PROMPT = """You are Virun, a friendly and practical travel assistant for India.
Answer the user's question directly and concisely. Ask one focused follow-up question
when necessary. Help with destinations, packing, trip planning, local travel, and
general travel questions.

You do not have live access to train or bus running status, schedules, fares, seat
availability, bookings, weather, or opening hours. Never invent or claim those facts.
For live transport planning, invite the user to use the app's Train & Bus search; for
weather, ask them to check the live weather card. Be clear that suggested itineraries
are ideas to verify before travel. Never claim to make a booking or payment.
Do not request passwords, API keys, payment details, or other secrets. Keep replies
warm, useful, and brief, using the user's language when practical.
"""


def build_prompt(
    message: str,
    reference_date: str | None,
    timezone: str,
    duration_days: int | None = None,
) -> str:
    return (
        f"{SYSTEM_PROMPT}\n"
        f"Reference date (for context only): {reference_date}\n"
        f"Timezone: {timezone}\n"
        f"Duration supplied in the form: {duration_days}\n"
        f"User message: {message}\n"
        f"JSON:"
    )


def build_itinerary_prompt(
    destination: str,
    duration_days: int,
    preferences: str | None,
    duration_nights: int | None = None,
    budget_inr: float | None = None,
    real_places: list[dict[str, str]] | None = None,
) -> str:
    place_list = "\n".join(
        f"- {place['name']} ({place['category']})" for place in (real_places or [])
    )
    location_instructions = (
        "Each morning, afternoon, and evening activity must name one place from the verified list below. "
        "Use each place name exactly as written, do not invent or substitute venue names, and include the "
        "chosen place in the activity text itself."
        if place_list
        else "No verified nearby place records are available right now. Still create the requested itinerary, "
        "but do not invent venue names or claim a specific location; describe activities generally."
    )
    return f"""Create a practical day-by-day sightseeing suggestion for a trip in India.
Return ONLY one JSON object with keys "destination", "duration_days", and "days".
The days array must contain exactly {duration_days} objects, numbered sequentially from 1.
Each day object must contain "day", "title", "morning", "afternoon", and "evening".
Use concise activity suggestions. Tailor the pace and suggestions to the supplied stay length
and maximum trip budget. Do not provide price quotes or claim current opening hours, prices,
availability, or reservations; do not invent factual details. Keep a sensible pace and do not repeat
the same attraction unless the user asks. These are AI-generated suggestions, not verified
travel facts or bookings. {location_instructions}

Destination: {destination}
Trip duration: exactly {duration_days} days
Nights at destination: {duration_nights if duration_nights is not None else "not specified"}
Maximum total trip budget: INR {budget_inr if budget_inr is not None else "not specified"}
Traveler interests and preferences: {preferences or "No specific preferences provided"}
Verified nearby places (OpenStreetMap):
{place_list}
JSON:"""
