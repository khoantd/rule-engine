#!/usr/bin/env python3
"""
Print all demo/sample data used by the rule engine.

Run from project root:
  python show_demo_data.py

Useful for reviewing fixtures, database seed data, and sample inputs.
"""

import json
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent
DATA_INPUT = ROOT / "data" / "input"
TESTS_FIXTURES = ROOT / "tests" / "fixtures"


def section(title: str) -> None:
    """Print a section header."""
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def show_json_file(path: Path, label: str) -> None:
    """Load and pretty-print a JSON file."""
    if not path.exists():
        print(f"  (file not found: {path})")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"  Error: {e}")


def show_database_sample_data() -> None:
    """Show sample data created by setup_database.py (in-DB seed)."""
    section("Database sample data (from setup_database.py)")

    print("\n--- Ruleset ---")
    print(
        json.dumps(
            {
                "name": "sample_ruleset",
                "description": "Sample ruleset for testing",
                "version": "1.0",
                "is_default": True,
                "created_by": "setup_script",
            },
            indent=2,
        )
    )

    print("\n--- Rules (3 rules) ---")
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
    print(json.dumps(rules, indent=2))

    print("\n--- Actionset (sample pattern_key -> action_recommendation) ---")
    patterns = [
        {"pattern_key": "YYY", "action_recommendation": "Approved", "description": "All rules matched"},
        {"pattern_key": "YYN", "action_recommendation": "Review", "description": "Two rules matched"},
        {"pattern_key": "YNN", "action_recommendation": "Reject", "description": "One rule matched"},
        {"pattern_key": "NNN", "action_recommendation": "Reject", "description": "No rules matched"},
    ]
    print(json.dumps(patterns, indent=2))

    print("\n--- Conditions (from data/input/conditions_config.json) ---")
    conditions_path = ROOT / "data" / "input" / "conditions_config.json"
    if conditions_path.exists():
        with open(conditions_path, "r", encoding="utf-8") as f:
            cond_data = json.load(f)
        cond_list = cond_data.get("conditions_set", [])
        print(f"  {len(cond_list)} condition(s) seeded from file")
        print(json.dumps(cond_list[:3], indent=2))
        if len(cond_list) > 3:
            print(f"  ... and {len(cond_list) - 3} more")
    else:
        print("  (file not found)")

    print("\n--- Actions (demo actions) ---")
    actions = [
        {"action_id": "ACT_APPROVED_EMAIL", "name": "Send approval email", "action_type": "notification", "pattern_key": "YYY"},
        {"action_id": "ACT_REVIEW_TASK", "name": "Create review task", "action_type": "task", "pattern_key": "YYN"},
        {"action_id": "ACT_REJECT_NOTIFY", "name": "Notify on reject", "action_type": "notification", "pattern_key": "YNN"},
        {"action_id": "ACT_AUDIT_LOG", "name": "Audit log entry", "action_type": "audit", "pattern_key": None},
    ]
    print(json.dumps(actions, indent=2))


def show_test_fixtures() -> None:
    """Show test fixtures (rules + conditions + sample input)."""
    section("Test fixtures (tests/fixtures & conftest)")

    print("\n--- tests/fixtures/rules_config.json ---")
    show_json_file(TESTS_FIXTURES / "rules_config.json", "rules_config")

    print("\n--- tests/fixtures/conditions_config.json ---")
    show_json_file(TESTS_FIXTURES / "conditions_config.json", "conditions_config")

    print("\n--- Sample input data (conftest sample_input_data) ---")
    sample_input = {
        "status": "open",
        "priority": "15",
        "type": "bug",
        "issue": 35,
        "title": "Superman",
        "publisher": "DC",
    }
    print(json.dumps(sample_input, indent=2))


def show_data_input() -> None:
    """Show data/input config files (used by rule engine)."""
    section("Data input configs (data/input)")

    print("\n--- rules_config.json ---")
    show_json_file(DATA_INPUT / "rules_config.json", "rules_config")

    print("\n--- conditions_config.json ---")
    show_json_file(DATA_INPUT / "conditions_config.json", "conditions_config")

    # Optional: list DMN files
    dmn_files = list(DATA_INPUT.glob("*.dmn"))
    if dmn_files:
        print("\n--- DMN files ---")
        for f in dmn_files:
            print(f"  {f.name}")


def main() -> int:
    """Print all demo data."""
    print("Rule Engine – Demo Data")
    show_database_sample_data()
    show_test_fixtures()
    show_data_input()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
