"""
Database connection management module.

This module provides database connection utilities for PostgreSQL/TimescaleDB.
It supports connection pooling, context managers, and connection string management.
"""

import os
from typing import Optional
from contextlib import contextmanager
from urllib.parse import urlparse

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv, find_dotenv

from common.logger import get_logger
from common.exceptions import ConfigurationError, StorageError

logger = get_logger(__name__)

# Global database objects
_engine: Optional[Engine] = None
_SessionFactory: Optional[scoped_session] = None


def load_database_url(env_file: Optional[str] = None) -> str:
    """
    Load database URL from environment or .env file.

    Args:
        env_file: Optional path to .env file containing TIMESCALE_SERVICE_URL

    Returns:
        Database connection URL

    Raises:
        ConfigurationError: If database URL cannot be loaded
    """
    # Load .env file if provided or try to find it
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv(find_dotenv())

    # Try to get database URL from environment variable
    db_url = os.getenv("TIMESCALE_SERVICE_URL") or os.getenv("DATABASE_URL")

    if not db_url:
        # Try to build from individual PG environment variables
        pg_host = os.getenv("PGHOST")
        pg_port = os.getenv("PGPORT")
        pg_user = os.getenv("PGUSER")
        pg_password = os.getenv("PGPASSWORD")
        pg_database = os.getenv("PGDATABASE")
        pg_sslmode = os.getenv("PGSSLMODE", "require")

        if pg_host and pg_user and pg_database:
            db_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}?sslmode={pg_sslmode}"
            logger.info(
                "Built database URL from PG environment variables",
                host=pg_host,
                database=pg_database,
            )

    # SQLAlchemy 2.0 loads the "postgresql" dialect only; normalize postgres:// -> postgresql://
    if db_url and db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[11:]
        logger.debug("Normalized database URL scheme from postgres:// to postgresql://")

    if not db_url:
        raise ConfigurationError(
            "Database URL not found. Please set TIMESCALE_SERVICE_URL or DATABASE_URL environment variable, "
            "or provide PGHOST, PGUSER, PGDATABASE environment variables.",
            error_code="DATABASE_URL_MISSING",
            context={
                "env_vars": [
                    "TIMESCALE_SERVICE_URL",
                    "DATABASE_URL",
                    "PGHOST",
                    "PGUSER",
                    "PGDATABASE",
                ]
            },
        )

    # Validate and sanitize database URL for logging
    parsed = urlparse(db_url)
    safe_url = f"{parsed.scheme}://***:***@{parsed.hostname}:{parsed.port}{parsed.path}"
    logger.info(
        "Database URL loaded", safe_url=safe_url, database=parsed.path.lstrip("/")
    )

    return db_url


def create_database_engine(
    database_url: Optional[str] = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False,
) -> Engine:
    """
    Create SQLAlchemy database engine with connection pooling.

    Args:
        database_url: Database connection URL (loads from env if None)
        pool_size: Number of connections to keep in the pool
        max_overflow: Max additional connections to allow beyond pool_size
        pool_timeout: Seconds to wait before giving up on getting a connection
        pool_recycle: Seconds to recycle connections (helps with stale connections)
        echo: Echo SQL statements to logger (for debugging)

    Returns:
        SQLAlchemy Engine instance

    Raises:
        ConfigurationError: If database URL cannot be loaded
        StorageError: If database connection fails
    """
    global _engine

    if _engine is not None:
        logger.debug("Returning existing database engine")
        return _engine

    # Load database URL if not provided
    if database_url is None:
        database_url = load_database_url()

    try:
        # Create engine with connection pooling
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Test connections before using
            echo=echo,
            # TimescaleDB/PostgreSQL specific settings
            connect_args={"connect_timeout": 10, "application_name": "rule_engine"},
        )

        # Test connection
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info(
            "Database engine created successfully",
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
        )

        return _engine

    except Exception as e:
        logger.error("Failed to create database engine", error=str(e), exc_info=True)
        raise StorageError(
            f"Failed to connect to database: {str(e)}",
            error_code="DATABASE_CONNECTION_ERROR",
            context={"error": str(e)},
        ) from e


def get_engine() -> Engine:
    """
    Get the global database engine instance.

    Returns:
        SQLAlchemy Engine instance

    Raises:
        StorageError: If engine not initialized
    """
    global _engine

    if _engine is None:
        _engine = create_database_engine()

    return _engine


def create_session_factory(engine: Optional[Engine] = None) -> scoped_session:
    """
    Create a scoped session factory.

    Args:
        engine: SQLAlchemy engine (uses global engine if None)

    Returns:
        Scoped session factory
    """
    global _SessionFactory

    if _SessionFactory is not None:
        logger.debug("Returning existing session factory")
        return _SessionFactory

    if engine is None:
        engine = get_engine()

    # Create session factory (expire_on_commit=False so returned ORM instances
    # remain usable after commit, e.g. when repositories return created entities)
    _SessionFactory = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,
        )
    )

    logger.info("Session factory created")
    return _SessionFactory


def get_session_factory() -> scoped_session:
    """
    Get the global session factory instance.

    Returns:
        Scoped session factory
    """
    global _SessionFactory

    if _SessionFactory is None:
        _SessionFactory = create_session_factory()

    return _SessionFactory


@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database sessions.

    Automatically commits on success, rolls back on error,
    and closes the session when done.

    Usage:
        with get_db_session() as session:
            result = session.query(Rule).all()

    Yields:
        SQLAlchemy Session instance
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        session.rollback()
        logger.error(
            "Database session rolled back due to error", error=str(e), exc_info=True
        )
        raise
    finally:
        session.close()
        session_factory.remove()  # Clear thread-local so next call gets a fresh session
        logger.debug("Database session closed")


def init_database(
    database_url: Optional[str] = None, env_file: Optional[str] = None
) -> Engine:
    """
    Initialize database connection.

    This is a convenience function that loads the database URL
    and creates the engine.

    Args:
        database_url: Database connection URL (optional)
        env_file: Path to .env file containing credentials (optional)

    Returns:
        SQLAlchemy Engine instance
    """
    if env_file:
        database_url = load_database_url(env_file)

    engine = create_database_engine(database_url)
    create_session_factory(engine)

    logger.info("Database initialized successfully")
    return engine


def close_database():
    """
    Close all database connections and clean up resources.
    """
    global _engine, _SessionFactory

    if _SessionFactory:
        _SessionFactory.remove()
        _SessionFactory = None
        logger.info("Session factory removed")

    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")


def test_connection(database_url: Optional[str] = None) -> bool:
    """
    Test database connection.

    Args:
        database_url: Database connection URL (optional)

    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = create_database_engine(database_url) if database_url else get_engine()

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(
                "Database connection test successful", version=version.split()[1]
            )

        return True

    except Exception as e:
        logger.error("Database connection test failed", error=str(e), exc_info=True)
        return False


if __name__ == "__main__":
    import sys

    # Test database connection
    env_file = sys.argv[1] if len(sys.argv) > 1 else None

    print("Testing database connection...")
    if env_file:
        print(f"Loading credentials from: {env_file}")

    try:
        success = test_connection()
        if success:
            print("✓ Database connection successful!")
            sys.exit(0)
        else:
            print("✗ Database connection failed!")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
