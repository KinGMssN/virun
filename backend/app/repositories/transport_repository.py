"""Data access for stops and transport options.

The planner only ever talks to `TransportRepository`. Switching from JSON fixtures
to PostgreSQL/Supabase means changing ONE environment variable (TRANSPORT_REPOSITORY),
not the planning algorithm.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

from pydantic import ValidationError

from app.schemas.transport import Stop, TransportOption

logger = logging.getLogger(__name__)

DEFAULT_JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "transport_options.json"


class TransportRepository(ABC):
    @abstractmethod
    def list_options(self) -> list[TransportOption]:
        """All legs, including cancelled/sold-out ones (the planner filters them)."""

    @abstractmethod
    def list_stops(self) -> list[Stop]:
        ...

    def metadata(self) -> dict[str, Any]:
        """Dataset label/disclaimer shown to API clients."""
        return {}


class InMemoryTransportRepository(TransportRepository):
    """Used by tests and by anything that already has objects in hand."""

    def __init__(
        self,
        options: Iterable[TransportOption],
        stops: Iterable[Stop],
        meta: Optional[dict[str, Any]] = None,
    ):
        self._options = list(options)
        self._stops = list(stops)
        self._meta = meta or {}

    def list_options(self) -> list[TransportOption]:
        return list(self._options)

    def list_stops(self) -> list[Stop]:
        return list(self._stops)

    def metadata(self) -> dict[str, Any]:
        return dict(self._meta)


class JsonTransportRepository(TransportRepository):
    """Reads app/data/transport_options.json. Works with NO database connection.

    Records that fail validation (naive timestamps, arrival <= departure, ...) are
    skipped and listed in `skipped_records` instead of crashing the planner.
    """

    def __init__(self, path: Optional[Path | str] = None):
        self.path = Path(path) if path else DEFAULT_JSON_PATH
        self.skipped_records: list[dict[str, Any]] = []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._meta: dict[str, Any] = raw.get("meta", {})
        self._stops = self._parse(raw.get("stops", []), Stop, "stop_id")
        self._options = self._parse(raw.get("options", []), TransportOption, "option_id")

    def _parse(self, rows: list[dict], model, id_field: str) -> list:
        parsed = []
        for row in rows:
            try:
                parsed.append(model.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid %s record %s: %s", model.__name__, row.get(id_field), exc)
                self.skipped_records.append({"id": row.get(id_field), "error": str(exc)})
        return parsed

    def list_options(self) -> list[TransportOption]:
        return list(self._options)

    def list_stops(self) -> list[Stop]:
        return list(self._stops)

    def metadata(self) -> dict[str, Any]:
        return dict(self._meta)


class SupabaseTransportRepository(TransportRepository):
    """Reads `transport_stops` / `transport_options` (see supabase/migrations/001_initial_schema.sql).

    NOT TESTED against a live project in the hackathon build. Needs:
      pip install supabase   and env SUPABASE_URL + SUPABASE_KEY
    """

    PAGE = 1000

    def __init__(self, client=None):
        if client is None:
            from supabase import create_client  # lazy import: JSON mode needs no supabase package

            client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        self._client = client

    def _fetch_all(self, table: str) -> list[dict]:
        rows: list[dict] = []
        start = 0
        while True:
            batch = (
                self._client.table(table).select("*").order(self._order(table))
                .range(start, start + self.PAGE - 1).execute().data
            )
            rows.extend(batch)
            if len(batch) < self.PAGE:
                return rows
            start += self.PAGE

    @staticmethod
    def _order(table: str):
        return "stop_id" if table == "transport_stops" else "option_id"

    def list_options(self) -> list[TransportOption]:
        out = []
        for row in self._fetch_all("transport_options"):
            try:
                out.append(TransportOption.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid DB option %s: %s", row.get("option_id"), exc)
        return out

    def list_stops(self) -> list[Stop]:
        return [Stop.model_validate(r) for r in self._fetch_all("transport_stops")]

    def metadata(self) -> dict[str, Any]:
        return {"dataset_label": "SUPABASE", "disclaimer": "Records come from the shared database."}


@lru_cache(maxsize=1)
def get_default_repository() -> TransportRepository:
    kind = os.getenv("TRANSPORT_REPOSITORY", "json").lower()
    if kind == "supabase":
        return SupabaseTransportRepository()
    if kind == "json":
        return JsonTransportRepository(os.getenv("TRANSPORT_DATA_PATH") or None)
    raise ValueError(f"Unknown TRANSPORT_REPOSITORY '{kind}' (use 'json' or 'supabase')")
