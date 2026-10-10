"""Seed the planner's two transport tables from the clearly labeled JSON demo dataset."""
from __future__ import annotations

import json
import os
from datetime import datetime
from itertools import groupby
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from app.db import models  # noqa: F401 - registers the tables
from app.db.base import Base

ROOT = Path(__file__).resolve().parents[1]


def _load_rows(name: str) -> list[dict]:
    data = json.loads((ROOT / "app" / "data" / "transport_options.json").read_text(encoding="utf-8"))
    rows = data[name]
    if name == "options":
        for row in rows:
            for key in ("departure_at", "arrival_at"):
                row[key] = datetime.fromisoformat(row[key])
    return rows


def _upsert(connection, table_name: str, rows: list[dict], key: str) -> int:
    table = Base.metadata.tables[table_name]
    allowed = {column.name for column in table.columns}
    records = [{column: value for column, value in row.items() if column in allowed} for row in rows]
    if not records:
        return 0
    records.sort(key=lambda row: tuple(sorted(row)))
    for _, group in groupby(records, key=lambda row: tuple(sorted(row))):
        batch = list(group)
        statement = insert(table).values(batch)
        updates = {column: getattr(statement.excluded, column) for column in batch[0] if column != key}
        connection.execute(statement.on_conflict_do_update(index_elements=[key], set_=updates))
    return len(records)


def main() -> None:
    load_dotenv(ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is required; it was not printed or read from source control.")
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as connection:
        stops = _upsert(connection, "transport_stops", _load_rows("stops"), "stop_id")
        options = _upsert(connection, "transport_options", _load_rows("options"), "option_id")
    engine.dispose()
    print(f"Seeded {stops} demo stops and {options} demo transport options.")


if __name__ == "__main__":
    main()
