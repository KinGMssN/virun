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


def build_itinerary_prompt(destination: str, duration_days: int, preferences: str | None) -> str:
    return f"""Create a practical day-by-day sightseeing suggestion for a trip in India.
Return ONLY one JSON object with keys "destination", "duration_days", and "days".
The days array must contain exactly {duration_days} objects, numbered sequentially from 1.
Each day object must contain "day", "title", "morning", "afternoon", and "evening".
Use concise activity suggestions. Do not claim current opening hours, prices, availability,
or reservations; do not invent factual details. Keep a sensible pace and do not repeat
the same attraction unless the user asks. These are AI-generated suggestions, not verified
travel facts or bookings.

Destination: {destination}
Trip duration: exactly {duration_days} days
Traveler interests and preferences: {preferences or "No specific preferences provided"}
JSON:"""
