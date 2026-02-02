"""
Quick setup script for Tiger Cloud database integration.

This script helps you:
1. Test database connection
2. Run database migrations
3. Create sample data for all objects (rulesets, rules, actionset entries, conditions, actions)
4. Verify setup
"""

import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List

from common.db_connection import init_database, test_connection, load_database_url
from common.db_migrations import create_schema_from_scratch, run_migrations
from common.repository.db_repository import (
    RulesetRepository,
    RuleRepository,
    ConditionRepository,
    ActionRepository,
)
from common.db_connection import get_db_session
from common.db_models import Action, Condition, Pattern
from common.logger import get_logger

logger = get_logger(__name__)

# Path to config files for seeding (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent
CONDITIONS_CONFIG_PATH = PROJECT_ROOT / "data" / "input" / "conditions_config.json"


def setup_database(env_file: str = None):
    """
    Complete database setup process.

    Args:
        env_file: Path to .env file with database credentials
    """
    print("\n" + "=" * 60)
    print("Tiger Cloud Database Setup")
    print("=" * 60 + "\n")

    # Step 1: Load credentials
    print("Step 1: Loading database credentials...")
    if env_file:
        load_database_url(env_file)
        print(f"  ✓ Loaded credentials from: {env_file}")
    else:
        print("  ℹ Using environment variables")
    print()

    # Step 2: Test connection
    print("Step 2: Testing database connection...")
    if test_connection():
        print("  ✓ Database connection successful!\n")
    else:
        print("  ✗ Database connection failed!")
        print("\nPlease check your credentials and try again.")
        return False

    # Step 3: Create schema
    print("Step 3: Creating database schema...")
    try:
        create_schema_from_scratch(env_file)
        print("  ✓ Database schema created\n")
    except Exception as e:
        print(f"  ✗ Failed to create schema: {e}")
        return False

    # Step 4: Create sample data (all objects: rulesets, rules, actionset entries, conditions, actions)
    print("Step 4: Creating sample data for all objects...")
    try:
        create_sample_data()
        print("  ✓ Sample data created\n")
    except Exception as e:
        print(f"  ✗ Failed to create sample data: {e}")
        return False

    # Step 5: Verify setup
    print("Step 5: Verifying setup...")
    try:
        verify_setup()
        print()
    except Exception as e:
        print(f"  ✗ Verification failed: {e}")
        return False

    print("=" * 60)
    print("✓ Database setup completed successfully!")
    print("=" * 60)
    print()
    print("You can now use the rule engine with database storage.")
    print("Set USE_DATABASE=true in your environment or .env file.")
    print()

    return True


def create_sample_data():
    """Create sample ruleset and rules for testing."""
    ruleset_repo = RulesetRepository()
    rule_repo = RuleRepository()
    ruleset = ruleset_repo.get_ruleset_by_name("sample_ruleset")

    if ruleset is not None:
        # Ruleset exists: only skip rules/actionset if it already has rules; otherwise populate
        existing_rules = rule_repo.list_rules(ruleset_id=ruleset.id)
        if existing_rules:
            print(
                f"    Ruleset 'sample_ruleset' already exists with {len(existing_rules)} rule(s), skipping rules/actionset"
            )
            # Still seed conditions and actions (idempotent)
            seed_conditions()
            seed_actions(ruleset.id)
            return
        print(
            f"    Ruleset 'sample_ruleset' already exists (ID: {ruleset.id}), populating rules and actionset..."
        )
        ruleset_id = ruleset.id
    else:
        # Create ruleset
        ruleset = ruleset_repo.create_ruleset(
            name="sample_ruleset",
            description="Sample ruleset for testing",
            version="1.0",
            is_default=True,
            created_by="setup_script",
        )
        ruleset_id = ruleset.id  # capture while instance is usable
        print(f"    Created ruleset: {ruleset.name} (ID: {ruleset_id})")

    # Create sample rules

    rules = [
        {
            "rule_id": "RULE_001",
            "rule_name": "High Score Rule",
            "attribute": "score",
            "condition": "greater_than",
            "constant": "80",
            "message": "Score is high",
            "weight": 1.0,
            "rule_point": 100,
            "priority": 1,
            "action_result": "Y",
        },
        {
            "rule_id": "RULE_002",
            "rule_name": "Medium Score Rule",
            "attribute": "score",
            "condition": "greater_than",
            "constant": "50",
            "message": "Score is medium",
            "weight": 1.0,
            "rule_point": 50,
            "priority": 2,
            "action_result": "Y",
        },
        {
            "rule_id": "RULE_003",
            "rule_name": "Low Score Rule",
            "attribute": "score",
            "condition": "less_than_or_equal",
            "constant": "50",
            "message": "Score is low",
            "weight": 1.0,
            "rule_point": 0,
            "priority": 3,
            "action_result": "N",
        },
    ]

    for rule_data in rules:
        rule = rule_repo.create_rule(
            **rule_data, ruleset_id=ruleset_id, created_by="setup_script"
        )
        print(f"    Created rule: {rule.rule_name} (ID: {rule.id})")

    # Create sample actionset entries (Pattern rows)
    with get_db_session() as session:
        patterns = [
            {
                "pattern_key": "YYY",
                "action_recommendation": "Approved",
                "description": "All rules matched",
            },
            {
                "pattern_key": "YYN",
                "action_recommendation": "Review",
                "description": "Two rules matched",
            },
            {
                "pattern_key": "YNN",
                "action_recommendation": "Reject",
                "description": "One rule matched",
            },
            {
                "pattern_key": "NNN",
                "action_recommendation": "Reject",
                "description": "No rules matched",
            },
        ]

        for pattern_data in patterns:
            pattern = Pattern(**pattern_data, ruleset_id=ruleset_id)
            session.add(pattern)

        print(f"    Created {len(patterns)} actionset entries")

    # Seed conditions from data/input/conditions_config.json (if file exists)
    seed_conditions()

    # Seed demo actions (linked to actionset entries)
    seed_actions(ruleset_id)


def _condition_constant_to_value(constant: Any) -> str:
    """Convert JSON constant to string value for DB (list -> JSON string)."""
    if constant is None:
        return ""
    if isinstance(constant, list):
        return json.dumps(constant)
    return str(constant)


def seed_conditions() -> None:
    """Seed conditions from data/input/conditions_config.json if file exists."""
    if not CONDITIONS_CONFIG_PATH.exists():
        logger.info("Conditions config not found, skipping condition seed", path=str(CONDITIONS_CONFIG_PATH))
        return

    try:
        with open(CONDITIONS_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not load conditions config", path=str(CONDITIONS_CONFIG_PATH), error=str(e))
        return

    conditions_set = data.get("conditions_set") or data.get("conditions") or []
    if not conditions_set:
        logger.info("No conditions_set in config", path=str(CONDITIONS_CONFIG_PATH))
        return

    condition_repo = ConditionRepository()
    with get_db_session() as session:
        existing_ids = {row.condition_id for row in session.query(Condition.condition_id).all()}

    created = 0
    for item in conditions_set:
        condition_id = item.get("condition_id") or item.get("id")
        if not condition_id or condition_id in existing_ids:
            continue
        name = item.get("condition_name") or item.get("name") or condition_id
        attribute = item.get("attribute", "")
        equation = item.get("equation") or item.get("operator", "equal")
        constant = item.get("constant")
        value = _condition_constant_to_value(constant)
        description = item.get("description")
        try:
            condition_repo.create_condition(
                condition_id=str(condition_id),
                name=str(name),
                attribute=str(attribute),
                operator=str(equation),
                value=value,
                description=description,
                created_by="setup_script",
            )
            created += 1
            existing_ids.add(condition_id)
        except Exception as e:
            logger.warning("Could not create condition", condition_id=condition_id, error=str(e))

    if created:
        print(f"    Seeded {created} condition(s) from {CONDITIONS_CONFIG_PATH.name}")


def seed_actions(ruleset_id: int) -> None:
    """Seed demo actions and link them to actionset entries where applicable."""
    with get_db_session() as session:
        pattern_rows = session.query(Pattern).filter(Pattern.ruleset_id == ruleset_id).all()
        pattern_key_to_id = {p.pattern_key: p.id for p in pattern_rows}

    # Demo actions: some linked to patterns, some standalone
    demo_actions: List[Dict[str, Any]] = [
        {
            "action_id": "ACT_APPROVED_EMAIL",
            "name": "Send approval email",
            "action_type": "notification",
            "configuration": {"channel": "email", "template": "approved"},
            "description": "Send email when pattern is Approved",
            "pattern_key": "YYY",
        },
        {
            "action_id": "ACT_REVIEW_TASK",
            "name": "Create review task",
            "action_type": "task",
            "configuration": {"type": "review", "assignee": "default"},
            "description": "Create task when pattern is Review",
            "pattern_key": "YYN",
        },
        {
            "action_id": "ACT_REJECT_NOTIFY",
            "name": "Notify on reject",
            "action_type": "notification",
            "configuration": {"channel": "email", "template": "rejected"},
            "description": "Notify when pattern is Reject",
            "pattern_key": "YNN",
        },
        {
            "action_id": "ACT_AUDIT_LOG",
            "name": "Audit log entry",
            "action_type": "audit",
            "configuration": {"level": "info", "retention_days": 90},
            "description": "Standalone audit action",
            "pattern_key": None,
        },
    ]

    action_repo = ActionRepository()
    with get_db_session() as session:
        existing_ids = {row.action_id for row in session.query(Action.action_id).all()}

    created = 0
    for act in demo_actions:
        if act["action_id"] in existing_ids:
            continue
        pattern_key = act.get("pattern_key")
        pattern_id = pattern_key_to_id.get(pattern_key) if pattern_key else None
        try:
            action_repo.create_action(
                action_id=act["action_id"],
                name=act["name"],
                action_type=act["action_type"],
                configuration=act["configuration"],
                description=act.get("description"),
                pattern_id=pattern_id,
                created_by="setup_script",
            )
            created += 1
            existing_ids.add(act["action_id"])
        except Exception as e:
            logger.warning("Could not create action", action_id=act["action_id"], error=str(e))

    if created:
        print(f"    Seeded {created} action(s)")


def verify_setup():
    """Verify database setup by querying data."""
    from common.db_models import Ruleset, Rule, Pattern, Condition, Action

    with get_db_session() as session:
        # Count rulesets
        ruleset_count = session.query(Ruleset).count()
        print(f"  ✓ Found {ruleset_count} ruleset(s)")

        # Count rules
        rule_count = session.query(Rule).count()
        print(f"  ✓ Found {rule_count} rule(s)")

        # Count actionset entries (Pattern)
        pattern_count = session.query(Pattern).count()
        print(f"  ✓ Found {pattern_count} actionset entry/entries")

        # Count conditions
        condition_count = session.query(Condition).count()
        print(f"  ✓ Found {condition_count} condition(s)")

        # Count actions
        action_count = session.query(Action).count()
        print(f"  ✓ Found {action_count} action(s)")

        if ruleset_count == 0 or rule_count == 0:
            raise Exception("No data found in database")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Tiger Cloud database setup utility")
    parser.add_argument(
        "--env-file",
        required=False,
        help="Path to .env file with database credentials (e.g., tiger-cloud-db-credentials.env)",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only test database connection, do not create schema",
    )

    args = parser.parse_args()

    if args.test_only:
        print("Testing database connection...")
        if env_file := args.env_file:
            load_database_url(env_file)
            print(f"Using credentials from: {env_file}")

        if test_connection():
            print("✓ Database connection successful!")
            return 0
        else:
            print("✗ Database connection failed!")
            return 1
    else:
        success = setup_database(args.env_file)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
