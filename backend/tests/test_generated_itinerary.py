import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.concierge import router as router_module
from app.concierge.model_adapter import ModelError
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

PLACE = {
    "name": "Charminar",
    "category": "Monument",
    "latitude": 17.3616,
    "longitude": 78.4747,
    "source_url": "https://www.openstreetmap.org/node/123",
    "map_url": "https://www.openstreetmap.org/?mlat=17.3616&mlon=78.4747",
}


@pytest.fixture(autouse=True)
def avoid_external_places_service(monkeypatch):
    monkeypatch.setattr(router_module, "find_nearby_places", lambda _destination: [PLACE])


class FakeGenerator:
    def __init__(self, response):
        self.response = response
        self.prompt = None

    def generate_itinerary(self, prompt):
        self.prompt = prompt
        if isinstance(self.response, Exception):
            raise self.response
        return json.dumps(self.response)


def make_days(count):
    return [
        {
            "day": day,
            "title": f"Day {day}",
            "morning": "Visit a suggested landmark.",
            "afternoon": "Explore a nearby area.",
            "evening": "Relax and enjoy local food.",
        }
        for day in range(1, count + 1)
    ]


def test_generates_requested_number_of_days(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Goa", "duration_days": 3, "days": make_days(3)}
    )
    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 3, "preferences": "beaches"},
    )

    assert response.status_code == 200
    assert len(response.json()["days"]) == 3
    assert "beaches" in generator.prompt
    assert "- Charminar (Monument)" in generator.prompt


def test_persists_generated_plan_and_returns_database_id(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Goa", "duration_days": 2, "days": make_days(2)}
    )
    itinerary_id = uuid4()
    captured = {}

    def save_plan(**kwargs):
        captured.update(kwargs)
        return itinerary_id

    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)
    monkeypatch.setattr(router_module, "save_generated_itinerary", save_plan)

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 2, "duration_nights": 1, "budget_inr": 5000},
    )

    assert response.status_code == 200
    assert response.json()["saved_to_database"] is True
    assert response.json()["itinerary_id"] == str(itinerary_id)
    assert captured["duration_nights"] == 1
    assert captured["budget_inr"] == 5000
    assert captured["plan"].destination == "Goa"


def test_includes_only_places_returned_by_the_places_provider(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Hyderabad", "duration_days": 1, "days": make_days(1)}
    )
    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)
    monkeypatch.setattr(router_module, "find_nearby_places", lambda _: [PLACE])
    monkeypatch.setattr(router_module, "save_generated_itinerary", lambda **_: uuid4())

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Hyderabad", "duration_days": 1},
    )

    assert response.status_code == 200
    assert response.json()["places"] == [PLACE]
    day = response.json()["days"][0]
    assert day["morning_location"] == PLACE
    assert day["afternoon_location"] == PLACE
    assert day["evening_location"] == PLACE
    assert all("Charminar" in day[slot] for slot in ("morning", "afternoon", "evening"))
    assert "do not invent or substitute venue\nnames" in generator.prompt


def test_itinerary_still_generates_when_place_lookup_returns_no_results(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Goa", "duration_days": 1, "days": make_days(1)}
    )
    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)
    monkeypatch.setattr(router_module, "find_nearby_places", lambda _: [])

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["destination"] == "Goa"
    assert body["places"] == []
    assert all(
        day[field] is None
        for day in body["days"]
        for field in ("morning_location", "afternoon_location", "evening_location")
    )
    assert "do not invent venue names" in generator.prompt


def test_keeps_generated_plan_visible_when_database_is_not_configured(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Goa", "duration_days": 1, "days": make_days(1)}
    )
    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)
    monkeypatch.setattr(
        router_module,
        "save_generated_itinerary",
        lambda **_: (_ for _ in ()).throw(router_module.DatabaseNotConfigured("missing")),
    )

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["days"][0]["title"] == "Day 1"
    assert body["saved_to_database"] is False
    assert body["itinerary_id"] is None
    assert "DATABASE_URL" in body["save_error"]


def test_keeps_generated_plan_visible_when_database_write_fails(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Goa", "duration_days": 1, "days": make_days(1)}
    )
    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)
    monkeypatch.setattr(
        router_module,
        "save_generated_itinerary",
        lambda **_: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 1},
    )

    assert response.status_code == 200
    assert len(response.json()["days"]) == 1
    assert response.json()["saved_to_database"] is False
    assert "database connectivity" in response.json()["save_error"]


def test_rejects_generated_itinerary_with_wrong_day_count(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Goa", "duration_days": 3, "days": make_days(2)}
    )
    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 3},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "INVALID_MODEL_OUTPUT"


def test_rejects_duration_above_fifteen_days():
    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 16},
    )

    assert response.status_code == 422


def test_accepts_fifteen_day_itinerary(monkeypatch):
    generator = FakeGenerator(
        {"destination": "Goa", "duration_days": 15, "days": make_days(15)}
    )
    monkeypatch.setattr(router_module, "get_adapter", lambda: generator)

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 15},
    )

    assert response.status_code == 200
    assert len(response.json()["days"]) == 15


def test_reports_missing_groq_configuration(monkeypatch):
    monkeypatch.setattr(router_module, "get_adapter", lambda: (_ for _ in ()).throw(ModelError("NOT_CONFIGURED")))

    response = client.post(
        "/api/generate-itinerary",
        json={"destination": "Goa", "duration_days": 1},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "NOT_CONFIGURED"
