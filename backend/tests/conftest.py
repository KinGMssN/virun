import copy

import pytest

from app.repositories.transport_repository import JsonTransportRepository
from app.schemas.transport import Stop, TransportOption

BASE_REQUEST = {
    "origin": "Visakhapatnam",
    "destination": "Hitech City, Hyderabad",
    "departure_date": "2026-10-11",
    "arrival_deadline": "2026-10-12T09:00:00+05:30",
    "timezone": "Asia/Kolkata",
    "passengers": 1,
    "budget_inr": 1200,
    "bus_preference": "sleeper",
    "ac_preference": "preferred",
    "has_luggage": True,
    "priority": "balanced",
}


@pytest.fixture
def request_dict():
    return copy.deepcopy(BASE_REQUEST)


@pytest.fixture(scope="session")
def repo():
    return JsonTransportRepository()


def make_option(option_id, origin, destination, dep, arr, fare=100, **kw) -> TransportOption:
    """dep/arr like '2026-10-11T20:00' (IST is added)."""
    return TransportOption(
        option_id=option_id,
        origin_stop_id=origin,
        destination_stop_id=destination,
        mode=kw.pop("mode", "bus"),
        departure_at=dep + ":00+05:30",
        arrival_at=arr + ":00+05:30",
        fare_inr=fare,
        status=kw.pop("status", "available_in_demo"),
        data_source="SIMULATED",
        **kw,
    )


def make_stops(*ids):
    return [Stop(stop_id=i, name=i, data_source="SIMULATED") for i in ids]
