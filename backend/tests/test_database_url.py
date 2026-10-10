import pytest
from sqlalchemy.engine import URL

from app.db.connection import normalize_database_url


def test_normalizes_postgres_scheme_and_preserves_connection_options():
    url = normalize_database_url(
        "postgres://user:p%40ss@db.example:5432/virun?sslmode=require"
    )

    assert url == URL.create(
        "postgresql+psycopg",
        username="user",
        password="p@ss",
        host="db.example",
        port=5432,
        database="virun",
        query={"sslmode": "require"},
    )


@pytest.mark.parametrize("scheme", ["postgresql", "postgresql+psycopg"])
def test_normalizes_standard_postgresql_schemes(scheme):
    url = normalize_database_url(f"{scheme}://user:password@db.example/virun")

    assert url.drivername == "postgresql+psycopg"


def test_rejects_non_postgresql_urls_without_echoing_credentials():
    with pytest.raises(ValueError, match="PostgreSQL scheme") as exc_info:
        normalize_database_url("sqlite:///private-name.db")

    assert "private-name" not in str(exc_info.value)


def test_rejects_malformed_urls_without_echoing_input():
    with pytest.raises(ValueError) as exc_info:
        normalize_database_url("not-a-uri-with-secret")

    assert "secret" not in str(exc_info.value)
