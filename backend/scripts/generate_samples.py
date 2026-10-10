"""Write docs/sample_*.json from the REAL planner (share these with Members 1, 2 and 4).

    python scripts/generate_samples.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

REQUEST = {
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
client = TestClient(app)
out = ROOT / "docs"


def dump(name, data):
    (out / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote docs/" + name)


dump("sample_request.json", REQUEST)
dump("sample_response.json", client.post("/api/plan", json=REQUEST).json())
dump("sample_error_no_feasible_route.json",
     client.post("/api/plan", json={**REQUEST, "arrival_deadline": "2026-10-12T05:00:00+05:30"}).json())
dump("sample_error_invalid_request.json", client.post("/api/plan", json={**REQUEST, "passengers": 0}).json())
