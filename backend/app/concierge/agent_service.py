"""Bounded Groq tool loop for itinerary planning."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.concierge.itinerary_service import generate_itinerary
from app.concierge.places_service import find_nearby_places
from app.schemas.trip import ItineraryGenerationRequest

log = logging.getLogger("concierge.agent")
MAX_TOOL_TURNS = 6

SYSTEM = """You are Virun, an agentic travel planner for India. Use tools to search real places, create a day plan, estimate the full trip budget, and validate the result. Ask one concise clarification question when essential destination or trip duration is missing. Never represent estimated costs as live quotes. Place search uses OpenStreetMap; if it returns no places, say so and don't claim specific venues are verified. Use available place scale scores only as simulated survey-based ranking signals, never factual quality guarantees. Respect budget/preferences; revise by calling tools again when validation reports issues. Never claim bookings, live availability, opening hours, or live prices."""

TOOLS = [
    {"type": "function", "function": {"name": "calculate_budget", "description": "Estimate total INR trip cost by category and compare against budget. Intercity fare stays excluded unless supplied; the tool states this limitation.", "parameters": {"type": "object", "properties": {"duration_days": {"type": "integer", "minimum": 1, "maximum": 15}, "travelers": {"type": "integer", "minimum": 1}, "budget_inr": {"type": "number"}, "intercity_transportation_inr": {"type": "number", "minimum": 0}, "local_transportation_per_day_inr": {"type": "number", "minimum": 0}, "accommodation_per_night_inr": {"type": "number", "minimum": 0}, "food_per_person_per_day_inr": {"type": "number", "minimum": 0}, "activities_per_person_inr": {"type": "number", "minimum": 0}, "other_inr": {"type": "number", "minimum": 0}}, "required": ["duration_days"]}}},
    {"type": "function", "function": {"name": "search_destinations", "description": "Search verified nearby attractions for a destination using OpenStreetMap. Empty results mean no verified places were found.", "parameters": {"type": "object", "properties": {"destination": {"type": "string"}, "preferences": {"type": "string"}}, "required": ["destination"]}}},
    {"type": "function", "function": {"name": "build_itinerary", "description": "Generate a day-by-day sightseeing itinerary using existing Groq itinerary logic and verified nearby places.", "parameters": {"type": "object", "properties": {"destination": {"type": "string"}, "duration_days": {"type": "integer", "minimum": 1, "maximum": 15}, "duration_nights": {"type": "integer", "minimum": 0}, "budget_inr": {"type": "number"}, "preferences": {"type": "string"}}, "required": ["destination", "duration_days"]}}},
    {"type": "function", "function": {"name": "validate_itinerary", "description": "Check day count, user preferences, schedule pace, missing trip details, and estimated cost versus budget.", "parameters": {"type": "object", "properties": {"itinerary": {"type": "object"}, "duration_days": {"type": "integer"}, "preferences": {"type": "string"}, "budget_inr": {"type": "number"}, "estimated_total_inr": {"type": "number"}}, "required": ["itinerary", "duration_days"]}}},
]


def _place_scores():
    try:
        data = json.loads(Path(__file__).with_name("place_scores.json").read_text(encoding="utf-8"))
        return {row["place"].casefold(): row for row in data["places"]}, data["source"]
    except (OSError, ValueError, KeyError):
        return {}, "unavailable"


def _calculate_budget(args):
    days = int(args.get("duration_days", 1))
    travelers = max(1, int(args.get("travelers", 1)))
    nights = max(0, days - 1)
    # Heuristic planning allowances; category values supplied by user override them.
    local_transport = float(args.get("local_transportation_per_day_inr", 350)) * days * travelers
    intercity_transport = args.get("intercity_transportation_inr")
    stay_rate = float(args.get("accommodation_per_night_inr", 1500))
    food_rate = float(args.get("food_per_person_per_day_inr", 700))
    activity_rate = float(args.get("activities_per_person_inr", 500 * days))
    other = float(args.get("other_inr", 300 * days * travelers))
    costs = {"local_transportation": local_transport, "intercity_transportation": None if intercity_transport is None else float(intercity_transport), "accommodation": stay_rate * nights, "food": food_rate * days * travelers, "activities": activity_rate * travelers, "other": other}
    total = round(sum(value for value in costs.values() if value is not None), 2)
    budget = args.get("budget_inr")
    return {"currency": "INR", "estimated_costs": costs, "estimated_total": total, "budget": budget, "within_budget": None if budget is None else total <= float(budget), "complete": intercity_transport is not None, "assumptions": ["Planning estimates, not live quotes", "Intercity transportation is excluded unless you provide its cost", "Local transportation defaults to ₹350 per traveler-day", "Accommodation defaults to ₹1,500 per room-night", "Food defaults to ₹700 per traveler-day", "Activities default to ₹500 per traveler-day", "Other expenses default to ₹300 per traveler-day"]}


def _search(args):
    found = find_nearby_places(args["destination"])
    scores, source = _place_scores()
    for place in found:
        score = scores.get(place["name"].casefold())
        place["survey_scale_score"] = score["scale"] if score else None
        place["survey_scale_source"] = source if score else None
    # Keep unknown score records, stable after those that have a workbook signal.
    found.sort(key=lambda p: (p["survey_scale_score"] is None, -(p["survey_scale_score"] or 0), p["name"].casefold()))
    return {"source": "OpenStreetMap", "count": len(found), "places": found, "ranking_note": "Known places are ranked by the workbook's simulated survey scale; this is not a factual quality guarantee."}


def _validate(args):
    plan = args.get("itinerary") or {}
    issues = []
    missing = []
    days = plan.get("days") or []
    duration = int(args["duration_days"])
    if len(days) != duration:
        issues.append(f"Expected {duration} itinerary days; received {len(days)}.")
    prefs = (args.get("preferences") or "").casefold()
    text = " ".join(str(d.get(k, "")) for d in days for k in ("title", "morning", "afternoon", "evening")).casefold()
    for interest in (p.strip() for p in prefs.replace(";", ",").split(",") if p.strip()):
        if interest not in text and len(interest) > 2:
            issues.append(f"Preference '{interest}' is not clearly reflected in the itinerary.")
    for day in days:
        slots = [day.get(s, "") for s in ("morning", "afternoon", "evening")]
        if sum(bool(s.strip()) for s in slots if isinstance(s, str)) < 2:
            issues.append(f"Day {day.get('day', '?')} has fewer than two scheduled activity periods.")
    cost, budget = args.get("estimated_total_inr"), args.get("budget_inr")
    if budget is None:
        missing.append("A trip budget was not provided, so affordability cannot be confirmed.")
    if not plan.get("destination"):
        missing.append("The itinerary destination is missing.")
    if not args.get("preferences"):
        missing.append("No traveler preferences were provided for a preference fit check.")
    if cost is not None and budget is not None and float(cost) > float(budget):
        issues.append(f"Estimated total ₹{float(cost):.0f} exceeds budget ₹{float(budget):.0f}.")
    activities = [str(day.get(slot, "")).strip().casefold() for day in days for slot in ("morning", "afternoon", "evening") if day.get(slot)]
    if len(activities) != len(set(activities)):
        issues.append("One or more activity descriptions repeat; vary the schedule or explain the repeat.")
    return {"valid": not issues, "issues": issues, "missing_information": missing, "days_found": len(days), "duration_days": duration, "estimated_total_inr": cost, "budget_inr": budget}


def _run_tool(name, args, adapter):
    if name == "calculate_budget":
        return _calculate_budget(args)
    if name == "search_destinations":
        return _search(args)
    if name == "build_itinerary":
        places = find_nearby_places(args["destination"])
        req = ItineraryGenerationRequest(**args)
        return generate_itinerary(req, adapter, places).model_dump(mode="json")
    if name == "validate_itinerary":
        return _validate(args)
    raise ValueError("Unknown tool")


def _assistant_tool_message(response, calls):
    """Replay Groq's full assistant message, including GPT-OSS reasoning metadata."""
    dump = {}
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        try:
            dump = model_dump(exclude_none=True)
        except TypeError:
            dump = model_dump()
    message = {"role": "assistant"}
    for field in ("content", "refusal", "reasoning", "reasoning_details"):
        if field in dump and dump[field] is not None:
            message[field] = dump[field]
        elif not dump:
            value = getattr(response, field, None)
            if value is not None:
                message[field] = value
    dumped_calls = dump.get("tool_calls") if dump else None
    if dumped_calls:
        message["tool_calls"] = dumped_calls
    else:
        message["tool_calls"] = [
            {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}}
            for call in calls
        ]
    return message


def run_agent(adapter, history, message):
    """Execute at most six model/tool cycles and return the final assistant text."""
    if not hasattr(adapter, "chat_with_tools"):
        return adapter.chat(history, message)
    messages = [{"role": "system", "content": SYSTEM}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})
    for _ in range(MAX_TOOL_TURNS):
        response = adapter.chat_with_tools(messages, TOOLS)
        calls = getattr(response, "tool_calls", None)
        if not calls:
            content = (getattr(response, "content", None) or "").strip()
            if content:
                return content
            raise ValueError("Model returned no final response")
        messages.append(_assistant_tool_message(response, calls))
        for call in calls:
            try:
                args = json.loads(call.function.arguments or "{}")
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be an object")
                result = _run_tool(call.function.name, args, adapter)
            except Exception as exc:
                log.warning("agent tool failed name=%s error=%s", call.function.name, type(exc).__name__)
                result = {"error": "Tool execution failed; revise the request or use available information."}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False, default=str)})
    # One final tool-free turn asks the model to summarize completed work safely.
    messages.append({"role": "system", "content": "Execution limit reached. Summarize only available results and mention unresolved validation issues."})
    response = adapter.chat_with_tools(messages, [])
    content = (getattr(response, "content", None) or "").strip()
    if not content:
        raise ValueError("Model returned no final response")
    return content


def plan_trip(adapter, request, places):
    """Drive a complete itinerary workflow, retaining tool results for the response."""
    from app.schemas.trip import GeneratedItinerary

    # Places are fetched by the endpoint and reused for ranking and itinerary generation.
    place_result = _search_from_places(places)
    budget = _calculate_budget({
        "duration_days": request.duration_days,
        "travelers": 1,
        "budget_inr": request.budget_inr,
    })
    req_args = request.model_dump(exclude_none=True)
    itinerary = None
    validation = None

    if hasattr(adapter, "chat_with_tools"):
        messages = [
            {"role": "system", "content": SYSTEM + " For a complete plan, use search_destinations, calculate_budget, build_itinerary, and validate_itinerary. Use the supplied destination, duration, budget, and interests exactly. If validation identifies a fixable itinerary issue, revise and validate again before finishing."},
            {"role": "user", "content": "Create the complete itinerary now. Constraints: " + json.dumps(req_args, ensure_ascii=False) + ". Search context: " + json.dumps(place_result, ensure_ascii=False, default=str) + ". Budget calculation: " + json.dumps(budget, ensure_ascii=False) + ". Call the tools needed to create and validate the plan."},
        ]
        for _ in range(MAX_TOOL_TURNS):
            response = adapter.chat_with_tools(messages, TOOLS)
            calls = getattr(response, "tool_calls", None)
            if not calls:
                break
            messages.append(_assistant_tool_message(response, calls))
            for call in calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                    if name == "search_destinations":
                        result = place_result
                    elif name == "calculate_budget":
                        result = budget
                    elif name == "build_itinerary":
                        itinerary = generate_itinerary(request, adapter, places)
                        result = itinerary.model_dump(mode="json")
                    elif name == "validate_itinerary":
                        # Recompute against the actual generated plan, not model-supplied values.
                        if itinerary is None:
                            itinerary = generate_itinerary(request, adapter, places)
                        validation = _validate({"itinerary": itinerary.model_dump(mode="json"), "duration_days": request.duration_days, "preferences": request.preferences, "budget_inr": request.budget_inr, "estimated_total_inr": budget["estimated_total"]})
                        result = validation
                    else:
                        result = {"error": "Unknown tool"}
                except Exception as exc:
                    log.warning("planning tool failed name=%s error=%s", name, type(exc).__name__)
                    result = {"error": "Tool failed; the planner will retry with available information."}
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False, default=str)})

    # Guarantee a complete response even when the model stops early or skips a tool.
    if itinerary is None:
        itinerary = generate_itinerary(request, adapter, places)
    validation = _validate({"itinerary": itinerary.model_dump(mode="json"), "duration_days": request.duration_days, "preferences": request.preferences, "budget_inr": request.budget_inr, "estimated_total_inr": budget["estimated_total"]})
    # Give the existing generator one corrective pass for schedule or preference issues.
    fixable = [issue for issue in validation["issues"] if "exceeds budget" not in issue]
    if fixable:
        from app.schemas.trip import ItineraryGenerationRequest
        revised_request = ItineraryGenerationRequest(
            **{**request.model_dump(), "preferences": ((request.preferences or "")[:850] + "\nPlanner revision required: " + "; ".join(fixable))[:1000]}
        )
        try:
            revised = generate_itinerary(revised_request, adapter, places)
            revised_validation = _validate({"itinerary": revised.model_dump(mode="json"), "duration_days": request.duration_days, "preferences": request.preferences, "budget_inr": request.budget_inr, "estimated_total_inr": budget["estimated_total"]})
            itinerary, validation = revised, revised_validation
        except Exception as exc:
            log.warning("itinerary revision failed (%s)", type(exc).__name__)
    itinerary.budget_estimate = budget
    itinerary.validation = validation
    return itinerary


def _search_from_places(places):
    scores, source = _place_scores()
    results = []
    for place in places:
        item = dict(place)
        score = scores.get(str(item.get("name", "")).casefold())
        item["survey_scale_score"] = score["scale"] if score else None
        item["survey_scale_source"] = source if score else None
        results.append(item)
    results.sort(key=lambda p: (p["survey_scale_score"] is None, -(p["survey_scale_score"] or 0), p["name"].casefold()))
    return {"source": "OpenStreetMap", "count": len(results), "places": results, "ranking_note": "Known places are ranked by the workbook's simulated survey scale; this is not a factual quality guarantee."}
