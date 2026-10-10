"""Orchestration: validate -> resolve places -> generate -> check -> rank -> build response.

`plan_trip` is THE planner. POST /api/plan and Member 4's disruption-recovery service
must both call it (never write a second planner).
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Optional

from pydantic import ValidationError

from app.planner import algorithms as alg
from app.repositories.transport_repository import TransportRepository, get_default_repository
from app.schemas.itinerary import (
    ERR_INVALID_REQUEST,
    ERR_NO_FEASIBLE_ROUTE,
    ERR_UNKNOWN_LOCATION,
    ErrorBody,
    Itinerary,
    ItineraryLeg,
    PlanResponse,
)
from app.schemas.transport import Stop
from app.schemas.trip_request import TripRequest


def format_validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    return [
        {"field": ".".join(str(p) for p in err["loc"]) or "request", "message": err["msg"]}
        for err in exc.errors()
    ]


def _error(code: str, message: str, details: Any = None, **extra) -> PlanResponse:
    return PlanResponse(error=ErrorBody(code=code, message=message, details=details), **extra)


def _no_route_message(reason: str, request: TripRequest, origin: str, destination: str) -> str:
    messages = {
        alg.NO_CONNECTION: f"No transport records connect {origin} to {destination}.",
        alg.DEADLINE_EXCEEDED: "No route satisfies the current arrival deadline.",
        alg.OVER_BUDGET: f"No route fits within the budget of INR {request.budget_inr}.",
        alg.UNAVAILABLE_LEG: "Every route uses a cancelled, sold-out or excluded leg.",
        alg.INSUFFICIENT_TRANSFER_TIME: "Every route has a transfer that is too short.",
        alg.DEPARTS_BEFORE_REQUEST_DATE: "No route departs on or after the requested departure date.",
        alg.AC_REQUIRED_NOT_MET: "No route meets the required AC preference.",
        alg.DISCONNECTED_LEG: "No route has connected legs.",
        alg.INVALID_TIMESTAMPS: "Transport records have invalid timestamps.",
    }
    return messages.get(reason, "No route satisfies the hard constraints.")


def plan_trip(
    trip_request: TripRequest | dict,
    unavailable_leg_ids: Optional[Iterable[str]] = None,
    repository: Optional[TransportRepository] = None,
    config: alg.PlannerConfig = alg.DEFAULT_CONFIG,
) -> PlanResponse:
    """Plan a trip. Never raises for bad input; returns PlanResponse(error=...) instead.

    unavailable_leg_ids: option IDs to treat as cancelled (used by Member 4 for recovery).
    """
    excluded = sorted({str(x) for x in (unavailable_leg_ids or [])})
    excluded_set = frozenset(excluded)

    # --- A. input validation
    if isinstance(trip_request, dict):
        try:
            trip_request = TripRequest.model_validate(trip_request)
        except ValidationError as exc:
            return _error(ERR_INVALID_REQUEST, "The trip request is invalid.", format_validation_errors(exc),
                          unavailable_leg_ids=excluded)
    request: TripRequest = trip_request

    repo = repository or get_default_repository()
    stops: list[Stop] = repo.list_stops()
    options = repo.list_options()
    stop_names = {s.stop_id: s.name for s in stops}

    origin_id = alg.resolve_stop_id(request.origin, stops)
    destination_id = alg.resolve_stop_id(request.destination, stops)
    unknown = [
        {"field": field, "value": value}
        for field, value, resolved in (
            ("origin", request.origin, origin_id),
            ("destination", request.destination, destination_id),
        )
        if resolved is None
    ]
    if unknown:
        return _error(ERR_UNKNOWN_LOCATION, "Origin or destination is not covered by the transport dataset.",
                      unknown, unavailable_leg_ids=excluded)
    if origin_id == destination_id:
        return _error(ERR_INVALID_REQUEST, "Origin and destination must be different places.",
                      unavailable_leg_ids=excluded)

    # --- B. candidate generation
    candidates, truncated = alg.generate_candidates(options, origin_id, destination_id, config)
    if not candidates:
        return _error(
            ERR_NO_FEASIBLE_ROUTE,
            _no_route_message(alg.NO_CONNECTION, request, request.origin, request.destination),
            {"reason": alg.NO_CONNECTION, "candidates_evaluated": 0},
            unavailable_leg_ids=excluded,
        )

    # --- C/D/E/F. feasibility + metrics
    feasible: list[alg.ScoredCandidate] = []
    rejected: list[tuple[alg.Candidate, list[str]]] = []
    for cand in candidates:
        violations = alg.find_violations(cand, request, excluded_set, config)
        if violations:
            rejected.append((cand, violations))
        else:
            feasible.append(alg.ScoredCandidate(cand, alg.compute_metrics(cand, request, config)))

    if not feasible:
        counts = Counter(code for _, v in rejected for code in v)
        closest_cand, _ = min(
            rejected,
            key=lambda cv: (len(cv[1]), alg.VIOLATION_ORDER.index(cv[1][0]), "+".join(o.option_id for o in cv[0])),
        )
        # Headline reason = the violation that blocks the MOST candidates (ties: VIOLATION_ORDER).
        reason = max(counts, key=lambda code: (counts[code], -alg.VIOLATION_ORDER.index(code)))
        return _error(
            ERR_NO_FEASIBLE_ROUTE,
            _no_route_message(reason, request, request.origin, request.destination),
            {
                "reason": reason,
                "candidates_evaluated": len(candidates),
                "rejections": {code: counts[code] for code in alg.VIOLATION_ORDER if code in counts},
                "closest_route_key": "+".join(o.option_id for o in closest_cand),
                "search_truncated": truncated,
            },
            unavailable_leg_ids=excluded,
            candidates_evaluated=len(candidates),
        )

    # --- G. ranking
    ranked = alg.rank_candidates(feasible, request.priority, config)
    itineraries = [
        _build_itinerary(i, alt, request, stop_names) for i, alt in enumerate(ranked, start=1)
    ]
    return PlanResponse(
        itineraries=itineraries,
        unavailable_leg_ids=excluded,
        candidates_evaluated=len(candidates),
        candidates_feasible=len(feasible),
    )


def _build_itinerary(index: int, alt: alg.RankedAlternative, request: TripRequest, stop_names: dict[str, str]) -> Itinerary:
    tz = request.tzinfo
    m = alt.scored.metrics
    legs: list[ItineraryLeg] = []
    for n, (leg, wait) in enumerate(zip(alt.scored.legs, m.transfer_waits), start=1):
        luggage_fee = leg.luggage_fee_inr if request.has_luggage else 0
        legs.append(
            ItineraryLeg(
                leg_number=n,
                option_id=leg.option_id,
                origin_stop_id=leg.origin_stop_id,
                destination_stop_id=leg.destination_stop_id,
                origin_name=stop_names.get(leg.origin_stop_id),
                destination_name=stop_names.get(leg.destination_stop_id),
                mode=leg.mode,
                operator=leg.operator,
                departure_at=leg.departure_at.astimezone(tz),
                arrival_at=leg.arrival_at.astimezone(tz),
                duration_minutes=leg.duration_minutes,
                wait_before_minutes=wait,
                fare_per_passenger_inr=leg.fare_inr,
                luggage_fee_per_passenger_inr=luggage_fee,
                leg_total_inr=(leg.fare_inr + luggage_fee) * request.passengers,
                seat_type=leg.seat_type,
                ac=leg.ac,
                reliability_score=leg.reliability_score,
                origin_lat=leg.origin_lat,
                origin_lng=leg.origin_lng,
                destination_lat=leg.destination_lat,
                destination_lng=leg.destination_lng,
                data_source=leg.data_source,
            )
        )
    sources = sorted({leg.data_source for leg in alt.scored.legs})
    return Itinerary(
        itinerary_id=f"ROUTE-{index:03d}",
        route_key=alt.scored.route_key,
        label=" / ".join(alt.labels),
        labels=alt.labels,
        legs=legs,
        passengers=request.passengers,
        fare_per_passenger_inr=m.fare_per_passenger_inr,
        total_fare_inr=m.total_fare_inr,
        departure_at=m.departure_at.astimezone(tz),
        arrival_at=m.arrival_at.astimezone(tz),
        duration_minutes=m.duration_minutes,
        arrival_buffer_minutes=m.arrival_buffer_minutes,
        transfer_count=m.transfer_count,
        risk_level=m.risk_level,
        risk_score=m.risk_score,
        balanced_score=alt.balanced_score,
        feasible=True,
        data_source=sources[0] if len(sources) == 1 else "MIXED",
    )
