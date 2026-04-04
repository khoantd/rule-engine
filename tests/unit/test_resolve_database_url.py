"""Unit tests for optional database URL resolution (repository selection)."""

import os
from unittest.mock import patch

import pytest

from common.db_connection import resolve_database_url_optional


@pytest.mark.unit
@patch("common.db_connection.load_dotenv")
def test_resolve_database_url_optional_none_when_unset(mock_dotenv) -> None:
    """When no DB-related env vars are set, return None."""
    keys = (
        "TIMESCALE_SERVICE_URL",
        "DATABASE_URL",
        "PGHOST",
        "PGUSER",
        "PGDATABASE",
        "PGPASSWORD",
        "PGPORT",
        "PGSSLMODE",
    )
    removed = {k: os.environ.pop(k, None) for k in keys}
    try:
        assert resolve_database_url_optional() is None
    finally:
        for k, v in removed.items():
            if v is not None:
                os.environ[k] = v


@pytest.mark.unit
@patch("common.db_connection.load_dotenv")
def test_resolve_database_url_optional_from_database_url(mock_dotenv) -> None:
    """DATABASE_URL is returned and postgres:// is normalized."""
    with patch.dict(
        os.environ,
        {
            "TIMESCALE_SERVICE_URL": "",
            "DATABASE_URL": "postgres://u:p@localhost:5432/mydb",
        },
        clear=False,
    ):
        url = resolve_database_url_optional()
        assert url == "postgresql://u:p@localhost:5432/mydb"


@pytest.mark.unit
@patch("common.db_connection.load_dotenv")
def test_resolve_database_url_optional_prefers_timescale_over_database_url(
    mock_dotenv,
) -> None:
    """TIMESCALE_SERVICE_URL wins when both are set."""
    with patch.dict(
        os.environ,
        {
            "TIMESCALE_SERVICE_URL": "postgresql://ts:5432/one",
            "DATABASE_URL": "postgresql://db:5432/two",
        },
        clear=False,
    ):
        assert resolve_database_url_optional() == "postgresql://ts:5432/one"


@pytest.mark.unit
@patch("common.db_connection.load_dotenv")
def test_resolve_database_url_optional_builds_from_pg_vars(mock_dotenv) -> None:
    """PG* variables compose a URL when explicit URL env vars are absent."""
    with patch.dict(
        os.environ,
        {
            "TIMESCALE_SERVICE_URL": "",
            "DATABASE_URL": "",
            "PGHOST": "db.example",
            "PGPORT": "5433",
            "PGUSER": "app",
            "PGPASSWORD": "secret",
            "PGDATABASE": "rules",
            "PGSSLMODE": "disable",
        },
        clear=False,
    ):
        url = resolve_database_url_optional()
        assert url == ("postgresql://app:secret@db.example:5433/rules?sslmode=disable")
