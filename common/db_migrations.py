"""
Database migration and setup utilities.

This module provides utilities for running database migrations and
initializing the database schema.
"""

import sys
import os
from pathlib import Path

from alembic.config import Config
from alembic import command

from common.db_connection import init_database, load_database_url, get_engine
from common.logger import get_logger

logger = get_logger(__name__)


def run_migrations(alembic_dir: str = None, env_file: str = None) -> None:
    """
    Run database migrations using Alembic.

    Args:
        alembic_dir: Path to alembic.ini file
        env_file: Path to .env file with database credentials
    """
    if env_file:
        logger.info(f"Loading database credentials from: {env_file}")
        load_database_url(env_file)

    # Initialize database connection
    init_database()

    # Get alembic config
    if alembic_dir is None:
        project_root = Path(__file__).parent.parent
        alembic_dir = str(project_root / "alembic.ini")

    alembic_cfg = Config(alembic_dir)

    logger.info("Running database migrations...")

    try:
        # Run upgrade to head
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error("Failed to run database migrations", error=str(e), exc_info=True)
        raise


def create_schema_from_scratch(env_file: str = None) -> None:
    """
    Create database schema from scratch using SQLAlchemy models.

    This is useful for development and testing.

    Args:
        env_file: Path to .env file with database credentials
    """
    from common.db_models import Base
    from common.db_connection import init_database

    if env_file:
        logger.info(f"Loading database credentials from: {env_file}")
        load_database_url(env_file)

    # Initialize database connection
    engine = init_database()

    logger.info("Creating database schema from models...")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema created successfully")
    except Exception as e:
        logger.error("Failed to create database schema", error=str(e), exc_info=True)
        raise


def drop_all_tables(env_file: str = None) -> None:
    """
    Drop all database tables (DANGER: This will delete all data!).

    Args:
        env_file: Path to .env file with database credentials
    """
    from common.db_models import Base
    from common.db_connection import init_database

    if env_file:
        logger.info(f"Loading database credentials from: {env_file}")
        load_database_url(env_file)

    engine = init_database()

    logger.warning("Dropping all database tables...")

    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error("Failed to drop database tables", error=str(e), exc_info=True)
        raise


def reset_database(env_file: str = None) -> None:
    """
    Reset database: drop all tables and recreate schema (DANGER: Will delete all data!).

    Args:
        env_file: Path to .env file with database credentials
    """
    logger.warning("Resetting database (will delete all data)...")
    drop_all_tables(env_file)
    create_schema_from_scratch(env_file)
    logger.info("Database reset completed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Database migration and setup utilities"
    )
    parser.add_argument(
        "command",
        choices=["migrate", "create-schema", "drop-tables", "reset"],
        help="Command to execute",
    )
    parser.add_argument(
        "--env-file", help="Path to .env file with database credentials"
    )
    parser.add_argument("--alembic-dir", help="Path to alembic.ini file")

    args = parser.parse_args()

    try:
        if args.command == "migrate":
            run_migrations(args.alembic_dir, args.env_file)
        elif args.command == "create-schema":
            create_schema_from_scratch(args.env_file)
        elif args.command == "drop-tables":
            drop_all_tables(args.env_file)
        elif args.command == "reset":
            reset_database(args.env_file)

        print("✓ Command completed successfully")
        sys.exit(0)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
