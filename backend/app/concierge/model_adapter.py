import json
import os
import re

from openai import APITimeoutError, OpenAI, RateLimitError


class ModelError(Exception):
    """Safe error carrying only a code, never raw provider details."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class GroqAdapter:
    def __init__(self):
        key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL")
        if not key or not self.model:
            raise ModelError("NOT_CONFIGURED")
        self.client = OpenAI(
            api_key=key,
            base_url="https://api.groq.com/openai/v1",
            timeout=float(os.getenv("MODEL_TIMEOUT_SECONDS", "60")),
            max_retries=0,
        )

    def _complete_json(self, prompt: str) -> str:
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return r.choices[0].message.content or ""
        except APITimeoutError:
            raise ModelError("MODEL_TIMEOUT")
        except RateLimitError:
            raise ModelError("QUOTA_EXCEEDED")
        except Exception:
            raise ModelError("MODEL_ERROR")

    def extract(self, prompt: str) -> str:
        return self._complete_json(prompt)

    def generate_itinerary(self, prompt: str) -> str:
        return self._complete_json(prompt)


class MockAdapter:
    """Simple rule-based parser used when the model is unavailable.
    English only. Extracts only what is literally in the message."""

    def extract(self, prompt: str) -> str:
        msg = prompt.split("User message:", 1)[-1].rsplit("JSON:", 1)[0].strip()
        low = msg.lower()
        out = {
            "origin": None, "destination": None, "relative_date_text": None,
            "departure_date": None, "arrival_time": None, "arrival_next_day": False,
            "duration_days": None,
            "passengers": None, "budget_inr": None, "bus_preference": None,
            "ac_preference": None, "has_luggage": None, "priority": None,
        }
        m = re.search(
            r"from (.+?) to (.+?)(?:,|\.| with | and | before | by | arrive | tomorrow\b| today\b| tonight\b|$)",
            msg,
            re.I,
        )
        if m:
            out["origin"], out["destination"] = m.group(1).strip(), m.group(2).strip()
        for word in ("day after tomorrow", "tomorrow", "today", "tonight"):
            if word in low:
                out["relative_date_text"] = word
                break
        if re.search(r"\b(?:overnight|next day|following day)\b", low):
            out["arrival_next_day"] = True
        duration = re.search(r"\b(\d{1,2})\s*days?\b", low)
        if duration:
            out["duration_days"] = int(duration[1])
        t = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", low)
        if t:
            h, mi, ap = int(t[1]), int(t[2] or 0), t[3]
            if ap == "pm" and h < 12:
                h += 12
            if ap == "am" and h == 12:
                h = 0
            if h < 24 and mi < 60:
                out["arrival_time"] = f"{h:02d}:{mi:02d}"
        b = re.search(r"(?:₹|rs\.?\s*|budget\D{0,10})\s*([\d,]+)", low)
        if b:
            out["budget_inr"] = int(b[1].replace(",", "") or 0) or None
        if "sleeper" in low:
            out["bus_preference"] = "sleeper"
        elif "seater" in low:
            out["bus_preference"] = "seater"
        if "non-ac" in low or "non ac" in low:
            out["ac_preference"] = "non_ac"
        elif re.search(r"\bac\b", low):
            out["ac_preference"] = "preferred"
        if "cheap" in low or "low-cost" in low or "low cost" in low:
            out["priority"] = "cheapest"
        elif "fast" in low:
            out["priority"] = "fastest"
        if "luggage" in low or "bag" in low:
            out["has_luggage"] = True
        return json.dumps(out)


def get_adapter():
    if os.getenv("USE_MOCK_PARSER", "false").lower() == "true":
        return MockAdapter()
    return GroqAdapter()
