import json

from fastapi.testclient import TestClient

from app.concierge import router as router_module
from app.concierge.model_adapter import ModelError
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


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
