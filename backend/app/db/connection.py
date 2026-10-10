from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


def normalize_database_url(database_url: str) -> URL:
    """Use the installed psycopg 3 driver for common PostgreSQL URL schemes."""
    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise ValueError(
            "DATABASE_URL must be a valid PostgreSQL connection URI "
            "(for example, postgresql+psycopg://...)."
        ) from exc

    if url.drivername not in {
        "postgres",
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    }:
        raise ValueError(
            "DATABASE_URL must use a PostgreSQL scheme "
            "(postgres://, postgresql://, or postgresql+psycopg://)."
        )

    return url.set(drivername="postgresql+psycopg")
