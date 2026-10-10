from fastapi.testclient import TestClient

from app.concierge import router as router_module
from app.concierge.model_adapter import ModelError
from app.main import app


client = TestClient(app, raise_server_exceptions=False)


class FakeChatAdapter:
    def __init__(self, reply="Try the old town for a relaxed first afternoon."):
        self.reply = reply
        self.history = None
        self.message = None

    def chat(self, history, message):
        self.history = history
        self.message = message
        return self.reply


def test_chat_returns_groq_reply_and_recent_history(monkeypatch):
    adapter = FakeChatAdapter()
    monkeypatch.setattr(router_module, "get_adapter", lambda: adapter)

    response = client.post(
        "/api/chat",
        json={
            "message": "What should I see first?",
            "history": [{"role": "user", "content": "I am visiting Hyderabad."}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"reply": adapter.reply}
    assert adapter.message == "What should I see first?"
    assert adapter.history == [{"role": "user", "content": "I am visiting Hyderabad."}]


def test_chat_rejects_blank_or_oversized_requests():
    assert client.post("/api/chat", json={"message": "  "}).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 1001}).status_code == 422
    assert client.post(
        "/api/chat",
        json={"message": "hello", "history": [{"role": "user", "content": "hi"}] * 9},
    ).status_code == 422


def test_chat_reports_missing_groq_configuration(monkeypatch):
    monkeypatch.setattr(
        router_module,
        "get_adapter",
        lambda: (_ for _ in ()).throw(ModelError("NOT_CONFIGURED")),
    )

    response = client.post("/api/chat", json={"message": "Hello"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "NOT_CONFIGURED"


def test_chat_provider_error_is_safe(monkeypatch):
    class FailedAdapter:
        def chat(self, history, message):
            raise ModelError("MODEL_TIMEOUT")

    monkeypatch.setattr(router_module, "get_adapter", lambda: FailedAdapter())

    response = client.post("/api/chat", json={"message": "Hello"})

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "MODEL_TIMEOUT"
    assert "api_key" not in response.text.lower()
