import json

import pytest
from fastapi.testclient import TestClient

from app.concierge import router as router_module
from app.concierge.model_adapter import MockAdapter, ModelError
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

BASE = {"message": "test", "timezone": "Asia/Kolkata", "reference_date": "2026-10-10"}

FULL = {
    "origin": "Visakhapatnam", "destination": "Hitech City, Hyderabad",
    "relative_date_text": "tomorrow", "departure_date": None, "arrival_time": "09:00",
    "arrival_next_day": False, "passengers": 1, "budget_inr": 1200,
    "bus_preference": "sleeper", "ac_preference": "preferred",
    "has_luggage": True, "priority": "balanced",
}


class FakeAdapter:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def extract(self, prompt):
        self.calls += 1
        out = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        if isinstance(out, Exception):
            raise out
        return out if isinstance(out, str) else json.dumps(out)


def post(monkeypatch, adapter, body=None):
    monkeypatch.setattr(router_module, "get_adapter", lambda: adapter)
    monkeypatch.setenv("ENABLE_MOCK_FALLBACK", "false")
    return client.post("/api/parse-trip", json=body or BASE).json()


def test_complete_request_ready(monkeypatch):
    r = post(monkeypatch, FakeAdapter(FULL))
    assert r["status"] == "ready"
    t = r["trip_request"]
    assert t["departure_date"] == "2026-10-11"
    assert t["arrival_deadline"] == "2026-10-11T09:00:00+05:30"
    assert t["bus_preference"] == "sleeper"


def test_overnight_adds_one_day(monkeypatch):
    r = post(monkeypatch, FakeAdapter({**FULL, "arrival_next_day": True}))
    assert r["trip_request"]["arrival_deadline"] == "2026-10-12T09:00:00+05:30"


@pytest.mark.parametrize("field,question", [
    ("origin", "Where will your journey start?"),
    ("destination", "Where do you want to go?"),
])
def test_missing_place_triggers_question(monkeypatch, field, question):
    r = post(monkeypatch, FakeAdapter({**FULL, field: None}))
    assert r["status"] == "needs_clarification"
    assert field in r["missing_fields"]
    assert question in r["clarification_questions"]
    assert r["partial_trip_request"] is not None


def test_ambiguous_time_asks(monkeypatch):
    r = post(monkeypatch, FakeAdapter({**FULL, "arrival_time": None}))
    assert r["missing_fields"] == ["arrival_deadline"]
    assert "What time must you arrive?" in r["clarification_questions"]


def test_relative_date_without_reference_date(monkeypatch):
    body = {"message": "test", "timezone": "Asia/Kolkata"}
    r = post(monkeypatch, FakeAdapter(FULL), body)
    assert r["status"] == "needs_clarification"
    assert "departure_date" in r["missing_fields"]


def test_already_understood_fields_not_reasked(monkeypatch):
    r = post(monkeypatch, FakeAdapter({**FULL, "origin": None}))
    assert "destination" not in r["missing_fields"]
    assert r["partial_trip_request"]["destination"] == "Hitech City, Hyderabad"


@pytest.mark.parametrize("n", [0, -1, 50, "abc"])
def test_invalid_passengers_rejected(monkeypatch, n):
    r = post(monkeypatch, FakeAdapter({**FULL, "passengers": n}))
    assert r["status"] != "ready"
    assert "passengers" in r["missing_fields"]


@pytest.mark.parametrize("b", [0, -500, "lots", 10**9])
def test_invalid_budget_rejected(monkeypatch, b):
    r = post(monkeypatch, FakeAdapter({**FULL, "budget_inr": b}))
    assert r["status"] != "ready"
    assert "budget_inr" in r["missing_fields"]


def test_rupee_string_budget_normalized(monkeypatch):
    r = post(monkeypatch, FakeAdapter({**FULL, "budget_inr": "₹1,200"}))
    assert r["trip_request"]["budget_inr"] == 1200


def test_fenced_json_accepted(monkeypatch):
    r = post(monkeypatch, FakeAdapter("```json\n" + json.dumps(FULL) + "\n```"))
    assert r["status"] == "ready"


def test_malformed_json_retries_then_errors(monkeypatch):
    a = FakeAdapter("not json at all")
    r = post(monkeypatch, a)
    assert r["status"] == "error"
    assert r["error_code"] == "INVALID_MODEL_OUTPUT"
    assert r["fallback"] == "manual_entry"
    assert a.calls == 2


def test_malformed_then_valid_recovers(monkeypatch):
    r = post(monkeypatch, FakeAdapter("oops", FULL))
    assert r["status"] == "ready"


@pytest.mark.parametrize("code", ["MODEL_TIMEOUT", "QUOTA_EXCEEDED"])
def test_model_failures_are_safe(monkeypatch, code):
    r = post(monkeypatch, FakeAdapter(ModelError(code)))
    assert r["status"] == "error" and r["error_code"] == code
    assert r["fallback"] == "manual_entry"


def test_quota_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(router_module, "get_adapter", lambda: FakeAdapter(ModelError("QUOTA_EXCEEDED")))
    monkeypatch.setenv("ENABLE_MOCK_FALLBACK", "true")
    body = {**BASE, "message": "from Vizag to Hyderabad tomorrow, arrive before 9 AM, sleeper bus"}
    r = client.post("/api/parse-trip", json=body).json()
    assert r["fallback"] == "mock_parser"
    assert r["status"] == "ready"
    assert r["trip_request"]["origin"] == "Vizag"


def test_mock_parser_does_not_include_relative_date_in_destination(monkeypatch):
    body = {
        **BASE,
        "message": "From Visakhapatnam to Hyderabad tomorrow, arrive before 9 AM",
    }
    response = post(monkeypatch, MockAdapter(), body)
    assert response["status"] == "ready"
    assert response["trip_request"]["destination"] == "Hyderabad"
    assert response["trip_request"]["departure_date"] == "2026-10-11"


def test_mock_parser_recognizes_next_day_arrival(monkeypatch):
    body = {
        **BASE,
        "message": "From Visakhapatnam to Hyderabad tomorrow, arrive next day before 9 AM",
    }
    response = post(monkeypatch, MockAdapter(), body)
    assert response["status"] == "ready"
    assert response["trip_request"]["arrival_deadline"] == "2026-10-12T09:00:00+05:30"


def test_unexpected_exception_is_safe(monkeypatch):
    class Boom:
        def extract(self, p):
            raise RuntimeError("secret-key-abc123 stack detail")
    r = post(monkeypatch, Boom())
    assert r["status"] == "error"
    assert "secret" not in json.dumps(r)


def test_response_has_no_fare_or_schedule_keys(monkeypatch):
    r = post(monkeypatch, FakeAdapter(FULL))
    text = json.dumps(r).lower()
    for word in ("fare", "price", "schedule", "availability", "seats_left", "booking"):
        assert word not in text


def test_api_key_never_in_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "sk-test-SECRET")
    r = post(monkeypatch, FakeAdapter(ModelError("MODEL_ERROR")))
    assert "SECRET" not in json.dumps(r)


def test_not_configured_when_no_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("USE_MOCK_PARSER", raising=False)
    monkeypatch.undo()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("USE_MOCK_PARSER", "false")
    monkeypatch.setenv("ENABLE_MOCK_FALLBACK", "false")
    r = client.post("/api/parse-trip", json=BASE).json()
    assert r["status"] == "error" and r["error_code"] == "NOT_CONFIGURED"


def test_blank_and_invalid_input_rejected():
    assert client.post("/api/parse-trip", json={**BASE, "message": "   "}).status_code == 422
    assert client.post("/api/parse-trip", json={**BASE, "timezone": "Mars/Base"}).status_code == 422


def test_telugu_message_passes_through_adapter(monkeypatch):
    body = {**BASE, "message": "రేపు ఉదయం 9 లోపు విశాఖపట్నం నుండి హైదరాబాద్"}
    r = post(monkeypatch, FakeAdapter({**FULL, "origin": "Visakhapatnam", "destination": "Hyderabad"}), body)
    assert r["status"] == "ready"

