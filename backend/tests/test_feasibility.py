"""Hard-constraint checks: transfers, chronology, cancelled legs, deadline, budget, cycles."""
from datetime import datetime

import pytest

from app.planner import algorithms as alg
from app.schemas.transport import TransportOption
from app.schemas.trip_request import TripRequest
from tests.conftest import BASE_REQUEST, make_option


def req(**overrides) -> TripRequest:
    return TripRequest.model_validate({**BASE_REQUEST, **overrides})


def chain(gap_minutes: int):
    """A->B arrives 10:00, B->C departs `gap_minutes` later."""
    first = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00", 100)
    dep2 = datetime.fromisoformat("2026-10-11T10:00:00+05:30").timestamp() + gap_minutes * 60
    dep2 = datetime.fromtimestamp(dep2, tz=first.arrival_at.tzinfo).strftime("%Y-%m-%dT%H:%M")
    second = make_option("L2", "B", "C", dep2, "2026-10-11T18:00", 100)
    return (first, second)


# ---------------------------------------------------------------- transfer buffers
def test_transfer_exactly_at_minimum_is_ok():
    assert alg.find_violations(chain(30), req(has_luggage=False)) == []


def test_transfer_one_minute_short_is_rejected():
    assert alg.find_violations(chain(29), req(has_luggage=False)) == [alg.INSUFFICIENT_TRANSFER_TIME]


def test_luggage_requires_longer_transfer():
    assert alg.find_violations(chain(40), req(has_luggage=False)) == []
    assert alg.find_violations(chain(40), req(has_luggage=True)) == [alg.INSUFFICIENT_TRANSFER_TIME]
    assert alg.find_violations(chain(45), req(has_luggage=True)) == []


def test_next_leg_departing_before_previous_arrival_is_chronology_violation():
    assert alg.find_violations(chain(-10), req()) == [alg.CHRONOLOGY_VIOLATION]


def test_disconnected_legs_are_rejected():
    a = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00")
    c = make_option("L2", "C", "D", "2026-10-11T12:00", "2026-10-11T14:00")
    assert alg.DISCONNECTED_LEG in alg.find_violations((a, c), req())


def test_invalid_timestamps_are_rejected():
    naive = TransportOption.model_construct(
        option_id="BAD", origin_stop_id="A", destination_stop_id="B", mode="bus",
        departure_at=datetime(2026, 10, 11, 8, 0), arrival_at=datetime(2026, 10, 11, 10, 0),
        fare_inr=1, luggage_fee_inr=0, status="available_in_demo", data_source="SIMULATED",
        reliability_score=0.9,
    )
    backwards = make_option("OK", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00").model_copy(
        update={"arrival_at": datetime.fromisoformat("2026-10-11T07:00:00+05:30")}
    )
    assert alg.find_violations((naive,), req()) == [alg.INVALID_TIMESTAMPS]
    assert alg.find_violations((backwards,), req()) == [alg.INVALID_TIMESTAMPS]


def test_schema_rejects_bad_records():
    with pytest.raises(ValueError):
        make_option("X", "A", "B", "2026-10-11T10:00", "2026-10-11T09:00")  # arrives before departing
    with pytest.raises(ValueError):
        TransportOption(option_id="X", origin_stop_id="A", destination_stop_id="B", mode="bus",
                        departure_at="2026-10-11T08:00:00", arrival_at="2026-10-11T10:00:00",  # naive
                        fare_inr=1, status="available", data_source="SIMULATED")


# ---------------------------------------------------------------- availability
@pytest.mark.parametrize("status", ["cancelled", "sold_out"])
def test_unavailable_status_is_rejected(status):
    leg = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00", status=status)
    assert alg.find_violations((leg,), req()) == [alg.UNAVAILABLE_LEG]


def test_excluded_leg_ids_are_rejected():
    leg = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00")
    assert alg.find_violations((leg,), req(), frozenset({"L1"})) == [alg.UNAVAILABLE_LEG]
    assert alg.find_violations((leg,), req(), frozenset({"OTHER"})) == []


# ---------------------------------------------------------------- deadline / budget / date / AC
def test_deadline_exactly_met_is_ok_one_minute_late_is_not():
    on_time = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-12T09:00")
    late = make_option("L2", "A", "B", "2026-10-11T08:00", "2026-10-12T09:01")
    assert alg.find_violations((on_time,), req()) == []
    assert alg.find_violations((late,), req()) == [alg.DEADLINE_EXCEEDED]


def test_budget_is_total_for_all_passengers():
    leg = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00", fare=600)
    assert alg.find_violations((leg,), req(passengers=1, budget_inr=600)) == []
    assert alg.find_violations((leg,), req(passengers=2, budget_inr=1199)) == [alg.OVER_BUDGET]
    assert alg.find_violations((leg,), req(passengers=2, budget_inr=None)) == []


def test_first_leg_may_not_depart_before_requested_date():
    leg = make_option("L1", "A", "B", "2026-10-10T23:59", "2026-10-11T06:00")
    assert alg.find_violations((leg,), req()) == [alg.DEPARTS_BEFORE_REQUEST_DATE]


def test_required_ac_rejects_explicitly_non_ac_legs_only():
    non_ac = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00", ac=False)
    unknown = make_option("L2", "A", "B", "2026-10-11T08:00", "2026-10-11T10:00", ac=None)
    assert alg.find_violations((non_ac,), req(ac_preference="required")) == [alg.AC_REQUIRED_NOT_MET]
    assert alg.find_violations((unknown,), req(ac_preference="required")) == []
    assert alg.find_violations((non_ac,), req(ac_preference="preferred")) == []


def test_multiple_violations_are_all_reported_in_fixed_order():
    leg = make_option("L1", "A", "B", "2026-10-11T08:00", "2026-10-13T10:00", fare=5000, status="cancelled")
    assert alg.find_violations((leg,), req()) == [alg.UNAVAILABLE_LEG, alg.DEADLINE_EXCEEDED, alg.OVER_BUDGET]


# ---------------------------------------------------------------- candidate generation
def test_generation_has_no_cycles_duplicates_or_time_travel(repo):
    cands, truncated = alg.generate_candidates(repo.list_options(), "VIZAG", "HYD-HITEC")
    assert len(cands) == 10 and not truncated
    for c in cands:
        ids = [leg.option_id for leg in c]
        assert len(ids) == len(set(ids)), "duplicate leg"
        stops = [c[0].origin_stop_id] + [leg.destination_stop_id for leg in c]
        assert len(stops) == len(set(stops)), "cycle"
        assert stops[0] == "VIZAG" and stops[-1] == "HYD-HITEC"
        for prev, nxt in zip(c, c[1:]):
            assert prev.destination_stop_id == nxt.origin_stop_id
            assert nxt.departure_at >= prev.arrival_at
    used = {leg.option_id for c in cands for leg in c}
    assert not used & {"BUS-DEMO-008", "BUS-DEMO-009"}  # reverse / cycle traps never appear


def test_generation_is_bounded(repo):
    cands, truncated = alg.generate_candidates(repo.list_options(), "VIZAG", "HYD-HITEC", alg.PlannerConfig(max_candidates=3))
    assert len(cands) == 3 and truncated
    cands, _ = alg.generate_candidates(repo.list_options(), "VIZAG", "HYD-HITEC", alg.PlannerConfig(max_legs=1))
    assert all(len(c) == 1 for c in cands)


def test_generation_is_independent_of_record_order(repo):
    forward = alg.generate_candidates(repo.list_options(), "VIZAG", "HYD-HITEC")[0]
    backward = alg.generate_candidates(list(reversed(repo.list_options())), "VIZAG", "HYD-HITEC")[0]
    assert forward == backward


def test_place_resolution(repo):
    stops = repo.list_stops()
    assert alg.resolve_stop_id("Visakhapatnam", stops) == "VIZAG"
    assert alg.resolve_stop_id("  VIZAG ", stops) == "VIZAG"
    assert alg.resolve_stop_id("Hitech City, Hyderabad", stops) == "HYD-HITEC"
    assert alg.resolve_stop_id("hitech city", stops) == "HYD-HITEC"
    assert alg.resolve_stop_id("Hyderabad", stops) == "HYD-DEMO"
    assert alg.resolve_stop_id("Atlantis", stops) is None
