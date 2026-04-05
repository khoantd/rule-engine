"""
Optional DB integration tests for consumer ruleset registration.

Enable with RUN_DB_INTEGRATION_TESTS=1 and a working DATABASE_URL / TIMESCALE_SERVICE_URL.
"""

import os

import pytest

pytestmark = pytest.mark.integration

skip_no_db = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"),
    reason="Set RUN_DB_INTEGRATION_TESTS=1 and configure DATABASE_URL to run",
)


@skip_no_db
def test_database_connects_for_registration_flow():
    """Smoke check: session factory works when integration env is enabled."""
    from sqlalchemy import text

    from common.db_connection import get_db_session

    with get_db_session() as session:
        session.execute(text("SELECT 1"))
