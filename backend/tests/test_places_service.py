from urllib.parse import unquote_plus

from app.concierge import places_service


def test_finds_named_osm_places_and_caches_results(monkeypatch):
    places_service._cache.clear()
    monkeypatch.setattr(places_service.time, "sleep", lambda _seconds: None)
    calls = []

    def fake_request(url, *, data=None, timeout=15):
        calls.append((url, data, timeout))
        if data is None:
            return [{"lat": "17.3850", "lon": "78.4867"}]
        return {
            "elements": [
                {
                    "type": "node",
                    "id": 123,
                    "lat": 17.38,
                    "lon": 78.48,
                    "tags": {"name": "Charminar", "historic": "monument"},
                },
                {"type": "node", "id": 124, "lat": 17.39, "lon": 78.49, "tags": {"historic": "fort"}},
            ]
        }

    monkeypatch.setattr(places_service, "_request_json", fake_request)

    found = places_service.find_nearby_places("Hyderabad")
    cached = places_service.find_nearby_places(" Hyderabad ")

    assert len(calls) == 2
    assert found == cached
    assert found[0]["name"] == "Charminar"
    assert found[0]["category"] == "Monument"
    assert found[0]["source_url"].endswith("/node/123")
    assert "openstreetmap.org/?mlat=" in found[0]["map_url"]
    query = unquote_plus(calls[1][1].decode("utf-8"))
    assert query.count("around:50000,") == 5
    assert query.count('["name"]') == 5
    assert "[timeout:45]" in query
    assert "out center tags 200;" in query
    assert calls[0][2] == 15
    assert calls[1][2] == 50


def test_no_geocoder_result_returns_empty_without_overpass(monkeypatch):
    places_service._cache.clear()
    calls = []
    monkeypatch.setattr(places_service, "_request_json", lambda url, **kwargs: calls.append(url) or [])

    assert places_service.find_nearby_places("Unknown settlement") == []
    assert len(calls) == 1
