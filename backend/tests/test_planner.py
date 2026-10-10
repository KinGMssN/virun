"""End-to-end planner behaviour: fares, ranking, determinism, failures, recovery, API, dataset."""
import json
import random

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.planner.service import plan_trip
from app.repositories.transport_repository import InMemoryTransportRepository, JsonTransportRepository
from app.schemas.trip_request import TripRequest
from tests.conftest import BASE_REQUEST

client = TestClient(app)


def by_route(resp):
    return {i.route_key: i for i in resp.itineraries}


# ---------------------------------------------------------------- happy path
def test_demo_request_returns_ranked_alternatives(request_dict):
    r = plan_trip(request_dict)
    assert r.error is None
    assert r.candidates_evaluated == 10 and r.candidates_feasible == 4
    assert [i.itinerary_id for i in r.itineraries] == ["ROUTE-001", "ROUTE-002", "ROUTE-003"]
    routes = by_route(r)
    assert set(routes) == {"TRAIN-DEMO-001+BUS-DEMO-004", "BUS-DEMO-003+METRO-DEMO-001", "BUS-DEMO-002"}
    assert routes["BUS-DEMO-003+METRO-DEMO-001"].labels == ["Cheapest"]
    assert routes["TRAIN-DEMO-001+BUS-DEMO-004"].labels == ["Balanced", "Fastest"]  # priority first
    assert routes["BUS-DEMO-002"].labels == ["Lowest risk"]
    for it in r.itineraries:
        assert it.feasible and it.data_source == "SIMULATED"
        assert it.arrival_at <= TripRequest.model_validate(request_dict).arrival_deadline
        assert it.arrival_buffer_minutes >= 0
        assert it.total_fare_inr <= 1200
        assert it.transfer_count == len(it.legs) - 1


def test_transfer_journey_details(request_dict):
    it = by_route(plan_trip(request_dict))["TRAIN-DEMO-001+BUS-DEMO-004"]
    assert it.transfer_count == 1
    assert it.total_fare_inr == 970 and it.duration_minutes == 630
    assert it.arrival_at.isoformat() == "2026-10-12T06:00:00+05:30"
    assert it.arrival_buffer_minutes == 180
    assert [l.wait_before_minutes for l in it.legs] == [None, 75]
    assert it.risk_level == "medium"


def test_priority_only_changes_order(request_dict):
    a = plan_trip({**request_dict, "priority": "cheapest"})
    b = plan_trip({**request_dict, "priority": "lowest_risk"})
    assert a.itineraries[0].labels[0] == "Cheapest"
    assert b.itineraries[0].labels[0] == "Lowest risk"
    assert {i.route_key for i in a.itineraries} == {i.route_key for i in b.itineraries}
    assert plan_trip({**request_dict, "priority": "safest"}).itineraries[0].labels[0] == "Lowest risk"


def test_no_duplicate_alternatives(request_dict):
    keys = [i.route_key for i in plan_trip(request_dict).itineraries]
    assert len(keys) == len(set(keys))


def test_single_feasible_route_carries_every_label(request_dict):
    r = plan_trip({**request_dict, "departure_date": "2026-10-12", "arrival_deadline": "2026-10-12T20:00:00+05:30"})
    assert [i.route_key for i in r.itineraries] == ["BUS-DEMO-007"]
    assert len(r.itineraries[0].labels) == 4


# ---------------------------------------------------------------- fares
def test_fare_includes_luggage_fee_only_when_has_luggage(request_dict):
    with_l = by_route(plan_trip(request_dict))["BUS-DEMO-003+METRO-DEMO-001"]
    without = by_route(plan_trip({**request_dict, "has_luggage": False}))["BUS-DEMO-003+METRO-DEMO-001"]
    assert with_l.total_fare_inr == 650 + 50 + 60 == 760
    assert without.total_fare_inr == 650 + 60 == 710
    assert with_l.legs[0].luggage_fee_per_passenger_inr == 50 and without.legs[0].luggage_fee_per_passenger_inr == 0


def test_fare_scales_with_passengers_and_leg_totals_add_up(request_dict):
    r = plan_trip({**request_dict, "passengers": 3, "budget_inr": None})
    for it in r.itineraries:
        assert it.total_fare_inr == it.fare_per_passenger_inr * 3
        assert sum(l.leg_total_inr for l in it.legs) == it.total_fare_inr
    assert by_route(r)["BUS-DEMO-003+METRO-DEMO-001"].total_fare_inr == 760 * 3


def test_budget_applies_to_total_of_all_passengers(request_dict):
    r = plan_trip({**request_dict, "passengers": 2, "budget_inr": 1600})
    assert {i.route_key for i in r.itineraries} == {"BUS-DEMO-003+METRO-DEMO-001"}  # 1520 only
    assert plan_trip({**request_dict, "passengers": 2, "budget_inr": 1500}).error.code == "NO_FEASIBLE_ROUTE"


def test_frontend_supplied_totals_are_ignored(request_dict):
    honest = plan_trip(request_dict)
    cheated = plan_trip({**request_dict, "total_fare_inr": 1, "fare_inr": 1})
    assert honest.model_dump() == cheated.model_dump()


# ---------------------------------------------------------------- preferences
def test_required_ac_removes_non_ac_routes(request_dict):
    r = plan_trip({**request_dict, "ac_preference": "required"})
    assert all(l.ac is not False for i in r.itineraries for l in i.legs)
    assert "BUS-DEMO-003+METRO-DEMO-001" not in by_route(r)
    assert by_route(r)["BUS-DEMO-001+METRO-DEMO-001"].labels == ["Cheapest"]


# ---------------------------------------------------------------- determinism
def test_same_request_same_output(request_dict):
    assert plan_trip(request_dict).model_dump_json() == plan_trip(request_dict).model_dump_json()


def test_output_independent_of_record_order(request_dict):
    base = JsonTransportRepository()
    expected = plan_trip(request_dict, repository=base).model_dump_json()
    for seed in range(5):
        opts = base.list_options()
        random.Random(seed).shuffle(opts)
        shuffled = InMemoryTransportRepository(opts, list(reversed(base.list_stops())))
        assert plan_trip(request_dict, repository=shuffled).model_dump_json() == expected


# ---------------------------------------------------------------- failures
def test_no_feasible_route_deadline(request_dict):
    r = plan_trip({**request_dict, "arrival_deadline": "2026-10-12T05:00:00+05:30"})
    assert r.itineraries == []
    assert r.error.code == "NO_FEASIBLE_ROUTE"
    assert r.error.message == "No route satisfies the current arrival deadline."
    assert r.error.details["reason"] == "DEADLINE_EXCEEDED"


def test_no_feasible_route_budget(request_dict):
    r = plan_trip({**request_dict, "budget_inr": 500})
    assert r.error.code == "NO_FEASIBLE_ROUTE" and r.error.details["reason"] == "OVER_BUDGET"


def test_no_connection_between_places(request_dict):
    r = plan_trip({**request_dict, "origin": "Hyderabad", "destination": "Vijayawada"})
    assert r.error.code == "NO_FEASIBLE_ROUTE" and r.error.details["reason"] == "NO_CONNECTION"


def test_unknown_location_and_same_place(request_dict):
    r = plan_trip({**request_dict, "destination": "Atlantis"})
    assert r.error.code == "UNKNOWN_LOCATION" and r.error.details == [{"field": "destination", "value": "Atlantis"}]
    assert plan_trip({**request_dict, "destination": "vizag"}).error.code == "INVALID_REQUEST"


@pytest.mark.parametrize("patch,field", [
    ({"passengers": 0}, "passengers"),
    ({"budget_inr": -5}, "budget_inr"),
    ({"arrival_deadline": "2026-10-12T09:00:00"}, "arrival_deadline"),   # no UTC offset
    ({"arrival_deadline": "2026-10-10T09:00:00+05:30"}, "request"),      # before departure date
    ({"timezone": "Mars/Base"}, "timezone"),
    ({"ac_preference": "maybe"}, "ac_preference"),
    ({"priority": "vibes"}, "priority"),
])
def test_invalid_requests_return_structured_error(request_dict, patch, field):
    r = plan_trip({**request_dict, **patch})
    assert r.error.code == "INVALID_REQUEST"
    assert any(d["field"] == field for d in r.error.details)


# ---------------------------------------------------------------- recovery (Member 4)
def test_unavailable_leg_ids_trigger_replanning(request_dict):
    first = plan_trip(request_dict)
    assert "BUS-DEMO-002" in " ".join(i.route_key for i in first.itineraries)
    again = plan_trip(request_dict, unavailable_leg_ids=["BUS-DEMO-002", "NOT-A-REAL-ID"])
    assert again.error is None
    assert all("BUS-DEMO-002" not in i.route_key for i in again.itineraries)
    assert again.unavailable_leg_ids == ["BUS-DEMO-002", "NOT-A-REAL-ID"]


def test_excluding_everything_gives_structured_error(request_dict):
    ids = [o.option_id for o in JsonTransportRepository().list_options()]
    r = plan_trip(request_dict, unavailable_leg_ids=ids)
    assert r.error.code == "NO_FEASIBLE_ROUTE" and r.error.details["reason"] == "UNAVAILABLE_LEG"


def test_plan_trip_accepts_model_and_positional_arguments(request_dict):
    model = TripRequest.model_validate(request_dict)
    assert plan_trip(model, ["BUS-DEMO-002"]).model_dump() == plan_trip(request_dict, ["BUS-DEMO-002"]).model_dump()


# ---------------------------------------------------------------- API
def test_api_plan_success(request_dict):
    res = client.post("/api/plan", json=request_dict)
    assert res.status_code == 200
    body = res.json()
    assert "error" not in body and len(body["itineraries"]) == 3
    assert body["itineraries"][0]["arrival_at"].endswith("+05:30")


def test_api_plan_no_feasible_route(request_dict):
    res = client.post("/api/plan", json={**request_dict, "arrival_deadline": "2026-10-12T05:00:00+05:30"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NO_FEASIBLE_ROUTE"
    assert set(res.json()) == {"error"}


def test_api_plan_invalid_body(request_dict):
    res = client.post("/api/plan", json={**request_dict, "passengers": 0})
    assert res.status_code == 422
    err = res.json()["error"]
    assert err["code"] == "INVALID_REQUEST" and any(d["field"] == "passengers" for d in err["details"])


def test_api_transport_options_lists_everything_with_source_labels():
    res = client.get("/api/transport/options")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == len(body["options"]) == 13
    assert {o["data_source"] for o in body["options"]} == {"SIMULATED"}
    assert "SIMULATED" in body["meta"]["dataset_label"]
    assert {o["status"] for o in body["options"]} >= {"cancelled", "sold_out", "available_in_demo"}


def test_api_transport_options_filters():
    body = client.get("/api/transport/options", params={"mode": "metro"}).json()
    assert body["count"] == 2 and all(o["mode"] == "metro" for o in body["options"])
    body = client.get("/api/transport/options", params={"origin_stop_id": "VIZAG", "destination_stop_id": "HYD-HITEC"}).json()
    assert all(o["origin_stop_id"] == "VIZAG" and o["destination_stop_id"] == "HYD-HITEC" for o in body["options"])


# ---------------------------------------------------------------- dataset integrity
def test_dataset_is_coherent_and_labelled():
    raw = json.loads(JsonTransportRepository().path.read_text(encoding="utf-8"))
    repo = JsonTransportRepository()
    assert repo.skipped_records == []
    ids = [o["option_id"] for o in raw["options"]]
    assert len(ids) == len(set(ids)), "option IDs must be unique"
    assert all(o["data_source"] == "SIMULATED" for o in raw["options"])
    assert all(s["data_source"] == "SIMULATED" for s in raw["stops"])
    stops = {s["stop_id"]: s for s in raw["stops"]}
    for o in repo.list_options():  # parsing already proves tz-aware + arrival > departure
        assert o.origin_stop_id in stops and o.destination_stop_id in stops
        assert (o.origin_lat, o.origin_lng) == (stops[o.origin_stop_id]["latitude"], stops[o.origin_stop_id]["longitude"])
        assert (o.destination_lat, o.destination_lng) == (stops[o.destination_stop_id]["latitude"], stops[o.destination_stop_id]["longitude"])


def test_json_repository_skips_invalid_records(tmp_path):
    good = json.loads(JsonTransportRepository().path.read_text(encoding="utf-8"))
    good["options"].append({**good["options"][0], "option_id": "BROKEN", "arrival_at": "2026-01-01T00:00:00+05:30"})
    path = tmp_path / "data.json"
    path.write_text(json.dumps(good), encoding="utf-8")
    repo = JsonTransportRepository(path)
    assert [s["id"] for s in repo.skipped_records] == ["BROKEN"]
    assert len(repo.list_options()) == 13
