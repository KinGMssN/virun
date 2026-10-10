"""Small, cached OpenStreetMap lookup for real nearby visitor places.

Searches are traveler-initiated and destination-only. Requests are throttled for
the public Nominatim service; alternate endpoints can be configured by operators.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger("places")
_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_lock = threading.Lock()
_request_lock = threading.Lock()
_last_request_at = 0.0
_CACHE_SECONDS = 6 * 60 * 60


def _request_json(url: str, *, data: bytes | None = None) -> dict | list:
    global _last_request_at
    # Nominatim requires no more than one request per second per application.
    with _request_lock:
        delay = 1.05 - (time.monotonic() - _last_request_at)
        if delay > 0:
            time.sleep(delay)
        headers = {"User-Agent": "VirunTravelPlanner/1.0 (traveler-initiated place search)"}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"
        request = Request(url, data=data, headers=headers)
        try:
            with urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
        finally:
            _last_request_at = time.monotonic()
    if not isinstance(result, (dict, list)):
        raise ValueError("Unexpected OpenStreetMap response")
    return result


def find_nearby_places(destination: str, limit: int = 20) -> list[dict]:
    """Return named, real OSM attractions near the requested destination."""
    query = " ".join(destination.strip().split())
    if not query:
        return []
    key = query.casefold()
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached and now - cached[0] < _CACHE_SECONDS:
            return cached[1][:limit]

    geocoder = os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org/search").rstrip("/")
    params = urlencode({"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "in"})
    try:
        matches = _request_json(f"{geocoder}?{params}")
        if not isinstance(matches, list) or not matches:
            _store(key, [], now)
            return []
        lat = float(matches[0]["lat"])
        lon = float(matches[0]["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Invalid coordinates from geocoder")

        overpass_url = os.getenv("OSM_OVERPASS_URL", "https://overpass-api.de/api/interpreter").strip()
        query_body = f"""[out:json][timeout:12];
(
  nwr(around:7000,{lat:.6f},{lon:.6f})["tourism"~"^(attraction|museum|viewpoint|zoo|theme_park|gallery|aquarium)$"];
  nwr(around:7000,{lat:.6f},{lon:.6f})["historic"~"^(monument|memorial|fort|castle|archaeological_site|ruins)$"];
  nwr(around:7000,{lat:.6f},{lon:.6f})["leisure"="park"];
);
out center tags 60;"""
        data = urlencode({"data": query_body}).encode("utf-8")
        response = _request_json(overpass_url, data=data)
        elements = response.get("elements", []) if isinstance(response, dict) else []
        places: list[dict] = []
        seen: set[str] = set()
        for item in elements:
            tags = item.get("tags") or {}
            name = str(tags.get("name", "")).strip()
            if not name:
                continue
            osm_type = item.get("type")
            osm_id = item.get("id")
            if osm_type not in {"node", "way", "relation"} or not osm_id:
                continue
            dedupe = name.casefold()
            if dedupe in seen:
                continue
            seen.add(dedupe)
            center = item.get("center") or item
            place_lat = float(center["lat"])
            place_lon = float(center["lon"])
            category = next(
                (str(tags[k]).replace("_", " ").title() for k in ("tourism", "historic", "leisure") if tags.get(k)),
                "Place of interest",
            )
            places.append({
                "name": name[:160],
                "category": category[:60],
                "latitude": place_lat,
                "longitude": place_lon,
                "source_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                "map_url": f"https://www.openstreetmap.org/?mlat={place_lat:.6f}&mlon={place_lon:.6f}#map=16/{place_lat:.6f}/{place_lon:.6f}",
            })
        places.sort(key=lambda place: (place["name"].casefold(), place["category"].casefold()))
        result = places[:limit]
        _store(key, result, time.monotonic())
        return result
    except Exception as exc:
        # Do not log the destination query or the request URL.
        log.warning("OpenStreetMap place lookup failed (%s)", type(exc).__name__)
        _store(key, [], time.monotonic(), ttl=300)
        return []


def _store(key: str, places: list[dict], now: float, ttl: int = _CACHE_SECONDS) -> None:
    with _cache_lock:
        if key not in _cache and len(_cache) >= 200:
            oldest = min(_cache, key=lambda item: _cache[item][0])
            _cache.pop(oldest, None)
        _cache[key] = (now, places)
