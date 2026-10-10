"""Deterministic route construction, feasibility checks, metrics and ranking.

Pure functions only: no I/O, no clock, no randomness, no LLM.
Same inputs -> same outputs, regardless of the order records come back from the repository.

RULES (keep in sync with README):
  FARE      total = sum over legs of (fare_inr + luggage_fee_inr if has_luggage) x passengers
  BUDGET    budget_inr is a HARD limit on that TOTAL (all passengers)
  DURATION  final arrival - first departure (includes transfer waits), whole minutes
  BUFFER    arrival_deadline - final arrival, whole minutes (must be >= 0)
  TRANSFER  next.departure >= previous.arrival + 30 min (+15 min if has_luggage)
  RISK      1 - product(leg reliability) + 0.05 x transfers + 0.10 if arrival buffer < 30 min
            low < 0.15 <= medium < 0.30 <= high
  BALANCED  0.35 fare + 0.30 duration + 0.20 risk + 0.10 transfers + 0.05 comfort
            (fare/duration/risk/transfers min-max normalised over the feasible set; 0 = best)
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, Sequence

from app.schemas.transport import AVAILABLE_STATUSES, Stop, TransportOption
from app.schemas.trip_request import TripRequest

# --------------------------------------------------------------------------- config


@dataclass(frozen=True)
class PlannerConfig:
    min_transfer_minutes: int = 30
    luggage_extra_minutes: int = 15
    max_legs: int = 3
    max_candidates: int = 500
    tight_buffer_minutes: int = 30
    transfer_risk_penalty: float = 0.05
    tight_buffer_risk_penalty: float = 0.10
    risk_low_below: float = 0.15
    risk_medium_below: float = 0.30
    w_fare: float = 0.35
    w_duration: float = 0.30
    w_risk: float = 0.20
    w_transfers: float = 0.10
    w_comfort: float = 0.05


DEFAULT_CONFIG = PlannerConfig()

# --------------------------------------------------------------------------- violation codes

UNAVAILABLE_LEG = "UNAVAILABLE_LEG"
INVALID_TIMESTAMPS = "INVALID_TIMESTAMPS"
DISCONNECTED_LEG = "DISCONNECTED_LEG"
DEPARTS_BEFORE_REQUEST_DATE = "DEPARTS_BEFORE_REQUEST_DATE"
CHRONOLOGY_VIOLATION = "CHRONOLOGY_VIOLATION"
INSUFFICIENT_TRANSFER_TIME = "INSUFFICIENT_TRANSFER_TIME"
AC_REQUIRED_NOT_MET = "AC_REQUIRED_NOT_MET"
AC_PREFERENCE_NOT_MET = "AC_PREFERENCE_NOT_MET"
DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
OVER_BUDGET = "OVER_BUDGET"
NO_CONNECTION = "NO_CONNECTION"  # not a per-candidate violation: no candidate exists at all

# Order used to pick the "primary" reason when reporting failures.
VIOLATION_ORDER = [
    INVALID_TIMESTAMPS,
    DISCONNECTED_LEG,
    UNAVAILABLE_LEG,
    CHRONOLOGY_VIOLATION,
    INSUFFICIENT_TRANSFER_TIME,
    DEPARTS_BEFORE_REQUEST_DATE,
    AC_REQUIRED_NOT_MET,
    AC_PREFERENCE_NOT_MET,
    DEADLINE_EXCEEDED,
    OVER_BUDGET,
]

# --------------------------------------------------------------------------- place names


def normalise_place(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def resolve_stop_id(text: str, stops: Iterable[Stop]) -> Optional[str]:
    """Match free text to a stop by id, name or alias (case/punctuation-insensitive)."""
    key = normalise_place(text)
    if not key:
        return None
    for stop in sorted(stops, key=lambda s: s.stop_id):
        names = {normalise_place(stop.stop_id), normalise_place(stop.name)}
        names.update(normalise_place(a) for a in stop.aliases)
        if key in names:
            return stop.stop_id
    return None


# --------------------------------------------------------------------------- candidate generation

Candidate = tuple[TransportOption, ...]


def generate_candidates(
    options: Iterable[TransportOption],
    origin_stop_id: str,
    destination_stop_id: str,
    config: PlannerConfig = DEFAULT_CONFIG,
) -> tuple[list[Candidate], bool]:
    """Depth-first search over legs.

    * a leg may follow another only if stops connect (destination of one == origin of next)
    * no leg is used twice, no stop is visited twice (no cycles)
    * a leg that departs BEFORE the previous leg arrives is never generated (time travel)
    * at most `max_legs` legs and `max_candidates` results (bounded)

    Returns (candidates, truncated). Output order is deterministic.
    """
    by_origin: dict[str, list[TransportOption]] = defaultdict(list)
    for opt in sorted(options, key=lambda o: (o.departure_at, o.arrival_at, o.option_id)):
        by_origin[opt.origin_stop_id].append(opt)

    results: list[Candidate] = []
    truncated = False

    def dfs(path: list[TransportOption], visited: frozenset[str]) -> None:
        nonlocal truncated
        here = path[-1].destination_stop_id if path else origin_stop_id
        for opt in by_origin.get(here, []):
            if len(results) >= config.max_candidates:
                truncated = True
                return
            if any(p.option_id == opt.option_id for p in path):
                continue  # duplicate leg
            if opt.destination_stop_id in visited:
                continue  # cycle
            if path and opt.departure_at < path[-1].arrival_at:
                continue  # impossible chronology
            new_path = path + [opt]
            if opt.destination_stop_id == destination_stop_id:
                results.append(tuple(new_path))
            elif len(new_path) < config.max_legs:
                dfs(new_path, visited | {opt.destination_stop_id})

    if origin_stop_id != destination_stop_id:
        dfs([], frozenset({origin_stop_id}))
    return results, truncated


# --------------------------------------------------------------------------- feasibility


def required_transfer_minutes(has_luggage: bool, config: PlannerConfig = DEFAULT_CONFIG) -> int:
    return config.min_transfer_minutes + (config.luggage_extra_minutes if has_luggage else 0)


def minutes_between(start: datetime, end: datetime) -> int:
    return math.floor((end - start).total_seconds() / 60)


def _is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.utcoffset() is not None


def find_violations(
    candidate: Candidate,
    request: TripRequest,
    unavailable_leg_ids: frozenset[str] = frozenset(),
    config: PlannerConfig = DEFAULT_CONFIG,
) -> list[str]:
    """Every hard-constraint violation of a candidate. Empty list == feasible."""
    found: set[str] = set()

    # timestamps first: everything else compares them
    for leg in candidate:
        if not (_is_aware(leg.departure_at) and _is_aware(leg.arrival_at)) or leg.arrival_at <= leg.departure_at:
            found.add(INVALID_TIMESTAMPS)
    if INVALID_TIMESTAMPS in found:
        return [INVALID_TIMESTAMPS]

    for leg in candidate:
        if leg.status not in AVAILABLE_STATUSES or leg.option_id in unavailable_leg_ids:
            found.add(UNAVAILABLE_LEG)
        if request.ac_preference == "required" and leg.ac is False:
            found.add(AC_REQUIRED_NOT_MET)
        if request.ac_preference == "non_ac" and leg.ac is True:
            found.add(AC_PREFERENCE_NOT_MET)

    needed = required_transfer_minutes(request.has_luggage, config)
    for prev, nxt in zip(candidate, candidate[1:]):
        if prev.destination_stop_id != nxt.origin_stop_id:
            found.add(DISCONNECTED_LEG)
            continue
        gap = minutes_between(prev.arrival_at, nxt.departure_at)
        if gap < 0:
            found.add(CHRONOLOGY_VIOLATION)
        elif gap < needed:
            found.add(INSUFFICIENT_TRANSFER_TIME)

    if candidate[0].departure_at < request.earliest_departure:
        found.add(DEPARTS_BEFORE_REQUEST_DATE)
    if candidate[-1].arrival_at > request.arrival_deadline:
        found.add(DEADLINE_EXCEEDED)
    if request.budget_inr is not None and total_fare_inr(candidate, request) > request.budget_inr:
        found.add(OVER_BUDGET)

    return [code for code in VIOLATION_ORDER if code in found]


# --------------------------------------------------------------------------- metrics


def fare_per_passenger_inr(candidate: Sequence[TransportOption], has_luggage: bool) -> int:
    return sum(leg.fare_inr + (leg.luggage_fee_inr if has_luggage else 0) for leg in candidate)


def total_fare_inr(candidate: Sequence[TransportOption], request: TripRequest) -> int:
    """THE fare rule: per-passenger fare (with luggage fees if any) x passengers."""
    return fare_per_passenger_inr(candidate, request.has_luggage) * request.passengers


@dataclass(frozen=True)
class CandidateMetrics:
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    fare_per_passenger_inr: int
    total_fare_inr: int
    arrival_buffer_minutes: int
    transfer_count: int
    transfer_waits: tuple[Optional[int], ...]  # per leg; None for the first
    risk_score: float
    risk_level: str
    comfort_penalty: float


def comfort_penalty(candidate: Sequence[TransportOption], request: TripRequest) -> float:
    """0 (matches preferences) .. 1 (matches none). Soft preference, used only in the balanced score.

    Each leg adds 0.5 if it is a bus whose seat_type differs from bus_preference,
    and 0.5 if ac_preference is 'preferred'/'required' and the leg is explicitly non-AC.
    Unknown (None) attributes never count against a leg.
    """
    total = 0.0
    for leg in candidate:
        if (
            request.bus_preference != "any"
            and leg.mode == "bus"
            and leg.seat_type is not None
            and leg.seat_type != request.bus_preference
        ):
            total += 0.5
        if request.ac_preference in ("preferred", "required") and leg.ac is False:
            total += 0.5
    return round(total / len(candidate), 4)


def risk_level_for(score: float, config: PlannerConfig = DEFAULT_CONFIG) -> str:
    if score < config.risk_low_below:
        return "low"
    if score < config.risk_medium_below:
        return "medium"
    return "high"


def compute_metrics(
    candidate: Candidate, request: TripRequest, config: PlannerConfig = DEFAULT_CONFIG
) -> CandidateMetrics:
    departure = candidate[0].departure_at
    arrival = candidate[-1].arrival_at
    buffer_minutes = minutes_between(arrival, request.arrival_deadline)
    transfers = len(candidate) - 1

    waits: list[Optional[int]] = [None]
    for prev, nxt in zip(candidate, candidate[1:]):
        waits.append(minutes_between(prev.arrival_at, nxt.departure_at))

    survival = math.prod(leg.reliability_score for leg in candidate)
    risk = (1.0 - survival) + config.transfer_risk_penalty * transfers
    if buffer_minutes < config.tight_buffer_minutes:
        risk += config.tight_buffer_risk_penalty
    risk = round(min(max(risk, 0.0), 1.0), 4)

    return CandidateMetrics(
        departure_at=departure,
        arrival_at=arrival,
        duration_minutes=minutes_between(departure, arrival),
        fare_per_passenger_inr=fare_per_passenger_inr(candidate, request.has_luggage),
        total_fare_inr=total_fare_inr(candidate, request),
        arrival_buffer_minutes=buffer_minutes,
        transfer_count=transfers,
        transfer_waits=tuple(waits),
        risk_score=risk,
        risk_level=risk_level_for(risk, config),
        comfort_penalty=comfort_penalty(candidate, request),
    )


# --------------------------------------------------------------------------- ranking

CATEGORY_ORDER = ["cheapest", "fastest", "lowest_risk", "balanced"]
CATEGORY_LABELS = {
    "cheapest": "Cheapest",
    "fastest": "Fastest",
    "lowest_risk": "Lowest risk",
    "balanced": "Balanced",
}


@dataclass(frozen=True)
class ScoredCandidate:
    legs: Candidate
    metrics: CandidateMetrics

    @property
    def route_key(self) -> str:
        return "+".join(leg.option_id for leg in self.legs)


@dataclass(frozen=True)
class RankedAlternative:
    categories: tuple[str, ...]  # e.g. ("fastest", "balanced")
    scored: ScoredCandidate
    balanced_score: float

    @property
    def labels(self) -> list[str]:
        return [CATEGORY_LABELS[c] for c in self.categories]


def _norm(value: float, lo: float, hi: float) -> float:
    return 0.0 if hi == lo else (value - lo) / (hi - lo)


def balanced_scores(items: Sequence[ScoredCandidate], config: PlannerConfig = DEFAULT_CONFIG) -> dict[str, float]:
    """Lower is better. Normalised over the feasible set so the result is scale-free."""
    fares = [i.metrics.total_fare_inr for i in items]
    durs = [i.metrics.duration_minutes for i in items]
    risks = [i.metrics.risk_score for i in items]
    trans = [i.metrics.transfer_count for i in items]
    out: dict[str, float] = {}
    for i in items:
        m = i.metrics
        score = (
            config.w_fare * _norm(m.total_fare_inr, min(fares), max(fares))
            + config.w_duration * _norm(m.duration_minutes, min(durs), max(durs))
            + config.w_risk * _norm(m.risk_score, min(risks), max(risks))
            + config.w_transfers * _norm(m.transfer_count, min(trans), max(trans))
            + config.w_comfort * m.comfort_penalty
        )
        out[i.route_key] = round(score, 6)
    return out


def rank_candidates(
    scored: Iterable[ScoredCandidate],
    priority: str = "balanced",
    config: PlannerConfig = DEFAULT_CONFIG,
) -> list[RankedAlternative]:
    """Pick the best candidate per category; merge categories that pick the same route.

    Ties are broken by explicit keys ending in route_key, so the result never depends on
    input order. The requested `priority` category is listed first.
    """
    unique: dict[str, ScoredCandidate] = {}
    for s in sorted(scored, key=lambda s: s.route_key):
        unique.setdefault(s.route_key, s)  # remove duplicate routes
    items = list(unique.values())
    if not items:
        return []

    bscores = balanced_scores(items, config)
    picks = {
        "cheapest": min(items, key=lambda s: (s.metrics.total_fare_inr, s.metrics.duration_minutes, s.metrics.arrival_at, s.route_key)),
        "fastest": min(items, key=lambda s: (s.metrics.duration_minutes, s.metrics.total_fare_inr, s.metrics.arrival_at, s.route_key)),
        "lowest_risk": min(items, key=lambda s: (s.metrics.risk_score, s.metrics.total_fare_inr, s.metrics.duration_minutes, s.route_key)),
        "balanced": min(items, key=lambda s: (bscores[s.route_key], s.metrics.total_fare_inr, s.metrics.duration_minutes, s.route_key)),
    }

    order = [priority] + [c for c in CATEGORY_ORDER if c != priority]
    merged: dict[str, list[str]] = {}
    for cat in order:
        merged.setdefault(picks[cat].route_key, []).append(cat)

    return [
        RankedAlternative(tuple(cats), unique[key], bscores[key])
        for key, cats in merged.items()  # dict keeps insertion order == priority order
    ]
