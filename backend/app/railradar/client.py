"""Small server-side client for the RailRadar public API."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException


class RailRadarClient:
    BASE_URL = "https://api.railradar.in/v1"

    def __init__(self, api_key: str | None = None, timeout: float = 12.0):
        self.api_key = api_key or os.getenv("RAILRADAR_API_KEY")
        self.timeout = timeout

    def _get(self, path: str, params: dict[str, str]) -> dict:
        if not self.api_key:
            raise HTTPException(
                status_code=503,
                detail={"code": "RAILRADAR_NOT_CONFIGURED", "message": "Live train search is not configured."},
            )
        url = f"{self.BASE_URL}{path}?{urlencode(params)}"
        request = Request(url, headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 401:
                raise HTTPException(status_code=502, detail={"code": "RAILRADAR_AUTH_FAILED", "message": "The train data provider rejected the configured key."}) from exc
            if exc.code == 429:
                raise HTTPException(status_code=503, detail={"code": "RAILRADAR_RATE_LIMITED", "message": "Live train search is temporarily rate limited."}) from exc
            if exc.code == 404:
                return {"success": True, "data": []}
            raise HTTPException(status_code=502, detail={"code": "RAILRADAR_UPSTREAM_ERROR", "message": "The train data provider could not complete the request."}) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=503, detail={"code": "RAILRADAR_UNAVAILABLE", "message": "Live train data is temporarily unavailable."}) from exc
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise HTTPException(status_code=502, detail={"code": "RAILRADAR_INVALID_RESPONSE", "message": "The train data provider returned an invalid response."})
        return payload

    def search_stations(self, query: str, limit: int = 10) -> list[dict]:
        payload = self._get("/lookup/search/stations", {"q": query, "limit": str(limit)})
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def trains_between(self, origin: str, destination: str, travel_date: str, live: bool = True) -> dict:
        payload = self._get(
            f"/trains/between/{quote(origin, safe='')}/{quote(destination, safe='')}",
            {"date": travel_date, "live": str(live).lower(), "byCity": "false"},
        )
        return payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
