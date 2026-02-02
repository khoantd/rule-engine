"""Initial schema creation

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-02-01 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    """Return True if the table exists (idempotent migrations)."""
    result = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :name)"
        ),
        {"name": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    connection = op.get_bind()

    # Create rulesets table (skip if already exists, e.g. from setup_database.py)
    if not _table_exists(connection, "rulesets"):
        op.create_table(
            "rulesets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("version", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("tenant_id", sa.String(length=255), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("updated_by", sa.String(length=255), nullable=True),
            sa.Column("tags", JSON(), nullable=True),
            sa.Column("metadata", JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
            sa.CheckConstraint("version != ''", name="check_ruleset_version_not_empty"),
        )
        op.create_index("idx_rulesets_status", "rulesets", ["status"])
        op.create_index("idx_rulesets_version", "rulesets", ["version"])

    # Create rules table
    if not _table_exists(connection, "rules"):
        op.create_table(
            "rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("rule_id", sa.String(length=255), nullable=False),
            sa.Column("rule_name", sa.String(length=255), nullable=False),
            sa.Column("attribute", sa.String(length=255), nullable=False),
            sa.Column("condition", sa.String(length=50), nullable=False),
            sa.Column("constant", sa.Text(), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("weight", sa.Float(), nullable=False),
            sa.Column("rule_point", sa.Integer(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("action_result", sa.String(length=10), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("version", sa.String(length=50), nullable=False),
            sa.Column("ruleset_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("updated_by", sa.String(length=255), nullable=True),
            sa.Column("tags", JSON(), nullable=True),
            sa.Column("metadata", JSON(), nullable=True),
            sa.ForeignKeyConstraint(["ruleset_id"], ["rulesets.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint("weight >= 0", name="check_weight_non_negative"),
            sa.CheckConstraint("rule_point >= 0", name="check_rule_point_non_negative"),
        )
        op.create_index("idx_rules_rule_id", "rules", ["rule_id"])
        op.create_index("idx_rules_attribute", "rules", ["attribute"])
        op.create_index("idx_rules_priority", "rules", ["priority"])
        op.create_index("idx_rules_status", "rules", ["status"])
        op.create_index("idx_rules_ruleset", "rules", ["ruleset_id", "priority"])

    # Create conditions table
    if not _table_exists(connection, "conditions"):
        op.create_table(
            "conditions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("condition_id", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("attribute", sa.String(length=255), nullable=False),
            sa.Column("operator", sa.String(length=50), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("updated_by", sa.String(length=255), nullable=True),
            sa.Column("tags", JSON(), nullable=True),
            sa.Column("metadata", JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("condition_id"),
        )
        op.create_index("idx_conditions_condition_id", "conditions", ["condition_id"])
        op.create_index("idx_conditions_attribute", "conditions", ["attribute"])
        op.create_index("idx_conditions_status", "conditions", ["status"])

    # Create actions table
    if not _table_exists(connection, "actions"):
        op.create_table(
            "actions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("action_id", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("action_type", sa.String(length=50), nullable=False),
            sa.Column("configuration", JSON(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("updated_by", sa.String(length=255), nullable=True),
            sa.Column("tags", JSON(), nullable=True),
            sa.Column("metadata", JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("action_id"),
        )
        op.create_index("idx_actions_action_id", "actions", ["action_id"])
        op.create_index("idx_actions_action_type", "actions", ["action_type"])
        op.create_index("idx_actions_status", "actions", ["status"])

    # Create patterns table
    if not _table_exists(connection, "patterns"):
        op.create_table(
            "patterns",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pattern_key", sa.String(length=50), nullable=False),
            sa.Column("action_recommendation", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("ruleset_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["ruleset_id"], ["rulesets.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_patterns_ruleset", "patterns", ["ruleset_id"])
        op.create_index("idx_patterns_key", "patterns", ["pattern_key"])

    # Create execution_logs table (time-series data for TimescaleDB)
    if not _table_exists(connection, "execution_logs"):
        op.create_table(
            "execution_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.String(length=255), nullable=False),
        sa.Column("input_data", JSON(), nullable=False),
        sa.Column("output_data", JSON(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=True),
        sa.Column("total_points", sa.Float(), nullable=True),
        sa.Column("pattern_result", sa.String(length=50), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_execution_logs_timestamp", "execution_logs", ["timestamp"])
        op.create_index(
            "idx_execution_logs_execution_id", "execution_logs", ["execution_id"]
        )
        op.create_index("idx_execution_logs_success", "execution_logs", ["success"])


def downgrade() -> None:
    # Drop execution_logs table
    op.drop_table("execution_logs")

    # Drop patterns table
    op.drop_index("idx_patterns_key", table_name="patterns")
    op.drop_index("idx_patterns_ruleset", table_name="patterns")
    op.drop_table("patterns")

    # Drop actions table
    op.drop_index("idx_actions_status", table_name="actions")
    op.drop_index("idx_actions_action_type", table_name="actions")
    op.drop_index("idx_actions_action_id", table_name="actions")
    op.drop_table("actions")

    # Drop conditions table
    op.drop_index("idx_conditions_status", table_name="conditions")
    op.drop_index("idx_conditions_attribute", table_name="conditions")
    op.drop_index("idx_conditions_condition_id", table_name="conditions")
    op.drop_table("conditions")

    # Drop rules table
    op.drop_index("idx_rules_ruleset", table_name="rules")
    op.drop_index("idx_rules_status", table_name="rules")
    op.drop_index("idx_rules_priority", table_name="rules")
    op.drop_index("idx_rules_attribute", table_name="rules")
    op.drop_index("idx_rules_rule_id", table_name="rules")
    op.drop_table("rules")

    # Drop rulesets table
    op.drop_index("idx_rulesets_version", table_name="rulesets")
    op.drop_index("idx_rulesets_status", table_name="rulesets")
    op.drop_table("rulesets")
