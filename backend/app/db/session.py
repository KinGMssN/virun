"""Small lazy SQLAlchemy session factory for the configured PostgreSQL database."""
from __future__ import annotations

import os
from functools import lru_cache
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.connection import normalize_database_url


class DatabaseNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise DatabaseNotConfigured("Database persistence is unavailable. Configure DATABASE_URL.")
    engine = create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def save_generated_itinerary(*, plan, duration_nights: int | None, budget_inr: float | None) -> UUID:
    """Persist a Groq sightseeing plan without inventing transport fare or time."""
    from app.db.models import Itinerary

    session = _session_factory()()
    try:
        record = Itinerary(
            trip_request_id=None,
            label=f"{plan.destination} {plan.duration_days}-day stay plan"[:80],
            itinerary_type="sightseeing",
            generated_content=plan.model_dump(mode="json", exclude={"itinerary_id", "saved_to_database", "save_error"}),
            duration_days=plan.duration_days,
            duration_nights=duration_nights,
            budget_inr=budget_inr,
            total_fare_inr=None,
            duration_minutes=None,
            data_source="GROQ",
        )
        session.add(record)
        session.commit()
        return record.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
