from types import SimpleNamespace

from app.concierge.agent_service import _calculate_budget, _validate, run_agent


def test_budget_breakdown_and_limit_comparison():
    result = _calculate_budget({"duration_days": 3, "travelers": 2, "budget_inr": 10000, "transportation_inr": 1000})
    assert result["estimated_costs"] == {
        "transportation": 1000, "accommodation": 3000, "food": 4200,
        "activities": 3000, "other": 1800,
    }
    assert result["estimated_total"] == 13000
    assert result["within_budget"] is False
    assert "not live quotes" in result["assumptions"][0]


def test_validation_reports_budget_and_duration_issues():
    result = _validate({"itinerary": {"days": [{"day": 1, "morning": "Walk", "afternoon": "Museum", "evening": "Dinner"}]}, "duration_days": 2, "budget_inr": 1000, "estimated_total_inr": 1500})
    assert result["valid"] is False
    assert any("Expected 2" in issue for issue in result["issues"])
    assert any("exceeds budget" in issue for issue in result["issues"])


def test_native_tool_turns_return_tool_result_and_continue():
    call = SimpleNamespace(id="call-1", function=SimpleNamespace(name="calculate_budget", arguments='{"duration_days": 1, "budget_inr": 4000}'))
    first = SimpleNamespace(content=None, tool_calls=[call], reasoning="provider reasoning token")
    final = SimpleNamespace(content="A one-day estimate is ready.", tool_calls=None)

    class Adapter:
        def __init__(self):
            self.messages = []

        def chat_with_tools(self, messages, tools):
            self.messages.append((messages, tools))
            return first if len(self.messages) == 1 else final

    adapter = Adapter()
    assert run_agent(adapter, [], "Plan a one-day trip under ₹4,000") == final.content
    messages, tools = adapter.messages[1]
    assert tools
    assert messages[-1]["role"] == "tool"
    assert '"within_budget": true' in messages[-1]["content"]
    assert messages[-2]["reasoning"] == "provider reasoning token"
