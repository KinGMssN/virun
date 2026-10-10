import json
import logging
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.concierge.model_adapter import ModelError
from app.concierge.prompts import build_prompt
from app.schemas.trip import (
    AcPreference, BusPreference, ParseTripRequest, ParseTripResponse, Priority, TripRequest,
)

log = logging.getLogger("concierge")

REQUIRED = ["origin", "destination", "departure_date", "arrival_deadline", "duration_days"]
QUESTIONS = {
    "origin": "Where will your journey start?",
    "destination": "Where do you want to go?",
    "departure_date": "Which date do you want to travel?",
    "arrival_deadline": "What time must you arrive?",
    "duration_days": "How many days do you want to spend on the trip? Choose 1 to 15 days.",
    "passengers": "How many passengers are travelling (1 to 10)?",
    "budget_inr": "Please enter a valid budget in rupees.",
}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

BUS_SYNONYMS = {"sleeper": "sleeper", "seater": "seater", "seat": "seater", "any": "any"}
AC_SYNONYMS = {
    "required": "required", "ac": "preferred", "preferred": "preferred",
    "non_ac": "non_ac", "non-ac": "non_ac", "non ac": "non_ac",
    "no_preference": "no_preference", "none": "no_preference",
}
PRIORITY_SYNONYMS = {
    "cheapest": "cheapest", "cheap": "cheapest", "low-cost": "cheapest",
    "fastest": "fastest", "fast": "fastest", "comfort": "comfort",
    "comfortable": "comfort", "balanced": "balanced",
}


def clean_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?|```$", "", (raw or "").strip(), flags=re.M).strip()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


def resolve_date(text, ref: date | None):
    """Resolve relative date words using ONLY the supplied reference date."""
    if not text or ref is None:
        return None
    t = str(text).lower()
    if "day after tomorrow" in t:
        return ref + timedelta(days=2)
    if "tomorrow" in t:
        return ref + timedelta(days=1)
    if "today" in t or "tonight" in t:
        return ref
    for i, d in enumerate(WEEKDAYS):
        if d in t:
            return ref + timedelta(days=((i - ref.weekday()) % 7) or 7)
    return None


def parse_time(s):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", str(s or "").strip())
    if not m:
        return None
    h, mi = int(m[1]), int(m[2])
    return time(h, mi) if h < 24 and mi < 60 else None


def to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def to_number(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(re.sub(r"[₹,\s]|rs\.?", "", str(v), flags=re.I))
    except ValueError:
        return None


def norm_enum(value, synonyms: dict, default: str) -> str:
    if value is None:
        return default
    return synonyms.get(str(value).strip().lower(), default)


def _get_data(adapter, prompt: str) -> dict:
    for _ in range(2):  # one retry on malformed output
        raw = adapter.extract(prompt)
        try:
            return clean_json(raw)
        except (json.JSONDecodeError, ValueError):
            continue
    raise ModelError("INVALID_MODEL_OUTPUT")


def run_parse(req: ParseTripRequest, adapter) -> ParseTripResponse:
    prompt = build_prompt(req.message, str(req.reference_date), req.timezone, req.duration_days)
    try:
        data = _get_data(adapter, prompt)
    except ModelError as e:
        log.warning("model error code=%s", e.code)
        return ParseTripResponse(status="error", error_code=e.code, fallback="manual_entry")
    except Exception:
        log.warning("model error code=MODEL_ERROR")
        return ParseTripResponse(status="error", error_code="MODEL_ERROR", fallback="manual_entry")

    tz = ZoneInfo(req.timezone)

    dep = None
    if data.get("departure_date"):
        try:
            dep = date.fromisoformat(str(data["departure_date"]))
        except ValueError:
            dep = None
    if dep is None:
        dep = resolve_date(data.get("relative_date_text"), req.reference_date)

    t = parse_time(data.get("arrival_time"))
    deadline = None
    if dep and t:
        arrive_date = dep + timedelta(days=1) if data.get("arrival_next_day") is True else dep
        deadline = datetime.combine(arrive_date, t, tzinfo=tz)

    # Invalid (not missing) passenger count or budget must be rejected, not defaulted.
    raw_pass = data.get("passengers")
    passengers = 1 if raw_pass is None else (to_int(raw_pass) if to_int(raw_pass) is not None else 0)
    raw_budget = data.get("budget_inr")
    budget = to_number(raw_budget)
    budget_invalid = raw_budget is not None and budget is None
    form_duration = re.search(r"\[trip-days:\s*(\d{1,2})\]", req.message, re.I)
    stated_duration = re.search(r"\b(\d{1,2})\s*days?\b", req.message, re.I)
    raw_duration = req.duration_days
    if raw_duration is None:
        if form_duration:
            raw_duration = form_duration.group(1)
        elif stated_duration:
            raw_duration = stated_duration.group(1)
        else:
            raw_duration = data.get("duration_days")
    duration_days = to_int(raw_duration)
    duration_invalid = raw_duration is not None and (
        duration_days is None or not 1 <= duration_days <= 15
    )

    partial = {
        "origin": (data.get("origin") or None),
        "destination": (data.get("destination") or None),
        "departure_date": dep.isoformat() if dep else None,
        "arrival_deadline": deadline.isoformat() if deadline else None,
        "duration_days": duration_days,
        "timezone": req.timezone,
        "passengers": passengers,
        "budget_inr": budget,
        "bus_preference": norm_enum(data.get("bus_preference"), BUS_SYNONYMS, BusPreference.any.value),
        "ac_preference": norm_enum(data.get("ac_preference"), AC_SYNONYMS, AcPreference.no_preference.value),
        "has_luggage": data.get("has_luggage") is True,
        "priority": norm_enum(data.get("priority"), PRIORITY_SYNONYMS, Priority.balanced.value),
    }

    problems = [f for f in REQUIRED if not partial.get(f)]
    if budget_invalid or (budget is not None and not (0 < budget <= 100000)):
        problems.append("budget_inr")
    if duration_invalid and "duration_days" not in problems:
        problems.append("duration_days")
    if not (1 <= passengers <= 10):
        problems.append("passengers")

    if problems:
        return ParseTripResponse(
            status="needs_clarification",
            partial_trip_request=partial,
            missing_fields=problems,
            clarification_questions=[QUESTIONS[f] for f in problems],
        )

    return ParseTripResponse(status="ready", trip_request=TripRequest(**partial))
