"""Agent tools — real implementations over the repo's own datasets.

search_hotels reads frontend/resources/datasets/hotels/<city>.json
(OpenStreetMap, ODbL — attribution required).
rapido_handoff is honest: Rapido publishes no third-party booking API,
so the tool returns deep-link candidates for the team to verify
against the installed app; it never claims a booking was made.
"""
import json
import os
from typing import Any, Dict, List, Optional

CANDIDATE_DIRS = [
    os.getenv("HOTELS_DIR", ""),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend",
                 "resources", "datasets", "hotels"),
    os.path.join(os.getcwd(), "frontend", "resources", "datasets", "hotels"),
]

KNOWN_CITIES = ["kashmir", "goa", "hyderabad", "visakhapatnam",
                "mumbai", "delhi", "bengaluru"]


def _hotels_dir() -> Optional[str]:
    for d in CANDIDATE_DIRS:
        if d and os.path.isdir(d):
            return d
    return None


def search_hotels(city: str, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    """Search the OSM hotels dataset for a city. Never invents entries."""
    d = _hotels_dir()
    if not d:
        return []
    key = (city or "").strip().lower()
    if key not in KNOWN_CITIES:
        # try to match loosely, else default file listing
        matches = [c for c in KNOWN_CITIES if key and key in c]
        key = matches[0] if matches else ""
    if not key:
        return []
    path = os.path.join(d, key + ".json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    hotels = data.get("hotels", [])
    q = (query or "").strip().lower()
    if q:
        hotels = [h for h in hotels if q in h.get("name", "").lower()
                  or q in (h.get("address") or "").lower()]
    return hotels[: max(1, min(limit, 10))]


def rapido_handoff(pickup: str, drop: str,
                   pickup_lat: Optional[float] = None,
                   pickup_lng: Optional[float] = None,
                   drop_lat: Optional[float] = None,
                   drop_lng: Optional[float] = None) -> Dict[str, Any]:
    """Build a Rapido handoff. No public booking API exists, so this
    returns deep-link candidates + store links for manual verification."""
    links = []
    if pickup_lat is not None and drop_lat is not None:
        links.append(
            "rapido://ride?pickup_lat=%s&pickup_lng=%s&drop_lat=%s&drop_lng=%s"
            % (pickup_lat, pickup_lng, drop_lat, drop_lng))
    links.append("https://www.rapido.bike/")
    return {
        "bookable_via_api": False,
        "pickup": pickup,
        "drop": drop,
        "deep_links": links,
        "note": ("Rapido has no public third-party booking API. Verify the "
                 "deep-link format against the installed Rapido app before "
                 "relying on it; otherwise fall back to opening the app."),
    }


def tracking_session(city: str) -> Dict[str, Any]:
    """Describe how live tracking works for the frontend demo."""
    return {
        "method": "browser_geolocation",
        "watch": True,
        "note": ("Frontend uses navigator.geolocation.watchPosition on HTTPS "
                 "with the traveler's permission; positions stream to this "
                 "session. No live position is stored server-side in the demo."),
        "city": city,
    }


TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Search real hotel/accommodation entries from the OpenStreetMap dataset for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City key, e.g. goa, hyderabad"},
                    "query": {"type": "string", "description": "Optional name/area filter"},
                    "limit": {"type": "integer", "description": "Max results (1-10)"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rapido_handoff",
            "description": "Prepare a Rapido ride handoff. Cannot book; returns deep links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pickup": {"type": "string"},
                    "drop": {"type": "string"},
                },
                "required": ["pickup", "drop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tracking_session",
            "description": "Explain/start live GPS tracking for the traveler's trip.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
]

_TOOL_FUNCS = {
    "search_hotels": search_hotels,
    "rapido_handoff": rapido_handoff,
    "tracking_session": tracking_session,
}


def run_tool(name: str, args: Dict[str, Any]):
    fn = _TOOL_FUNCS.get(name)
    if not fn:
        raise ValueError("unknown tool: " + name)
    return fn(**{k: v for k, v in args.items()})
