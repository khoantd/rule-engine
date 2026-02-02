"""
Add rule versioning and A/B testing tables.

Revision ID: add_rule_versioning_ab_testing
Revises: 
Create Date: 2026-02-01

This migration adds:
- rule_versions table for tracking rule history
- rule_ab_tests table for A/B test management
- test_assignments table for A/B test assignments
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_rule_versioning_ab_testing"
down_revision: Union[str, None] = "002_add_pattern_id_to_actions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database to add new tables."""

    # Add A/B test columns to execution_logs table
    op.add_column(
        "execution_logs", sa.Column("ab_test_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "execution_logs",
        sa.Column("ab_test_variant", sa.String(length=50), nullable=True),
    )

    # Create rule_versions table
    op.create_table(
        "rule_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("rule_name", sa.String(length=255), nullable=False),
        sa.Column("attribute", sa.String(length=255), nullable=False),
        sa.Column("condition", sa.String(length=50), nullable=False),
        sa.Column("constant", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("rule_point", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("action_result", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ruleset_id"],
            ["rulesets.id"],
            name=op.f("fk_rule_versions_ruleset_id_rulesets"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "weight >= 0", name="check_rule_version_weight_non_negative"
        ),
        sa.CheckConstraint(
            "rule_point >= 0", name="check_rule_version_point_non_negative"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_versions")),
    )

    # Create indexes for rule_versions
    op.create_index(
        op.f("idx_rule_versions_rule_id"),
        "rule_versions",
        ["rule_id", "version_number"],
        unique=False,
    )
    op.create_index(
        op.f("idx_rule_versions_ruleset"),
        "rule_versions",
        ["ruleset_id", "version_number"],
        unique=False,
    )
    op.create_index(
        op.f("idx_rule_versions_is_current"),
        "rule_versions",
        ["is_current"],
        unique=False,
    )

    # Create rule_ab_tests table
    op.create_table(
        "rule_ab_tests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.String(length=255), nullable=False),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("traffic_split_a", sa.Float(), nullable=True),
        sa.Column("traffic_split_b", sa.Float(), nullable=True),
        sa.Column("variant_a_version", sa.String(length=50), nullable=False),
        sa.Column("variant_a_description", sa.Text(), nullable=True),
        sa.Column("variant_b_version", sa.String(length=50), nullable=False),
        sa.Column("variant_b_description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_hours", sa.Integer(), nullable=True),
        sa.Column("min_sample_size", sa.Integer(), nullable=True),
        sa.Column("confidence_level", sa.Float(), nullable=True),
        sa.Column("winning_variant", sa.String(length=10), nullable=True),
        sa.Column("statistical_significance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ruleset_id"],
            ["rulesets.id"],
            name=op.f("fk_rule_ab_tests_ruleset_id_rulesets"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "traffic_split_a >= 0 and traffic_split_a <= 1", name="check_split_a_valid"
        ),
        sa.CheckConstraint(
            "traffic_split_b >= 0 and traffic_split_b <= 1", name="check_split_b_valid"
        ),
        sa.CheckConstraint(
            "abs(traffic_split_a + traffic_split_b - 1.0) < 0.01",
            name="check_split_sum",
        ),
        sa.CheckConstraint(
            "confidence_level > 0 and confidence_level <= 1",
            name="check_confidence_level",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_ab_tests")),
        sa.UniqueConstraint("test_id", name=op.f("uq_rule_ab_tests_test_id")),
    )

    # Create indexes for rule_ab_tests
    op.create_index(
        op.f("idx_rule_ab_tests_rule_id"), "rule_ab_tests", ["rule_id"], unique=False
    )
    op.create_index(
        op.f("idx_rule_ab_tests_status"), "rule_ab_tests", ["status"], unique=False
    )
    op.create_index(
        op.f("idx_rule_ab_tests_timing"),
        "rule_ab_tests",
        ["start_time", "end_time"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rule_ab_tests_test_id"), "rule_ab_tests", ["test_id"], unique=False
    )

    # Create test_assignments table
    op.create_table(
        "test_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ab_test_id", sa.Integer(), nullable=False),
        sa.Column("assignment_key", sa.String(length=255), nullable=False),
        sa.Column("variant", sa.String(length=10), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("execution_count", sa.Integer(), nullable=True),
        sa.Column("last_execution_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ab_test_id"],
            ["rule_ab_tests.id"],
            name=op.f("fk_test_assignments_ab_test_id_rule_ab_tests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_assignments")),
        sa.UniqueConstraint(
            "ab_test_id",
            "assignment_key",
            name=op.f("uq_test_assignments_ab_test_id_assignment_key"),
        ),
    )

    # Create indexes for test_assignments
    op.create_index(
        op.f("idx_test_assignments_test_key"),
        "test_assignments",
        ["ab_test_id", "assignment_key"],
        unique=True,
    )
    op.create_index(
        op.f("idx_test_assignments_variant"),
        "test_assignments",
        ["ab_test_id", "variant"],
        unique=False,
    )

    # Create index for execution_logs A/B test tracking
    op.create_index(
        "idx_execution_logs_ab_test",
        "execution_logs",
        ["ab_test_id", "ab_test_variant"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database to remove new tables."""

    # Remove A/B test columns from execution_logs table
    op.drop_index("idx_execution_logs_ab_test", table_name="execution_logs")
    op.drop_column("execution_logs", "ab_test_variant")
    op.drop_column("execution_logs", "ab_test_id")

    # Drop test_assignments table
    op.drop_index(op.f("idx_test_assignments_variant"), table_name="test_assignments")
    op.drop_index(op.f("idx_test_assignments_test_key"), table_name="test_assignments")
    op.drop_table("test_assignments")

    # Drop rule_ab_tests table
    op.drop_index(op.f("ix_rule_ab_tests_test_id"), table_name="rule_ab_tests")
    op.drop_index(op.f("idx_rule_ab_tests_timing"), table_name="rule_ab_tests")
    op.drop_index(op.f("idx_rule_ab_tests_status"), table_name="rule_ab_tests")
    op.drop_index(op.f("idx_rule_ab_tests_rule_id"), table_name="rule_ab_tests")
    op.drop_table("rule_ab_tests")

    # Drop rule_versions table
    op.drop_index(op.f("idx_rule_versions_is_current"), table_name="rule_versions")
    op.drop_index(op.f("idx_rule_versions_ruleset"), table_name="rule_versions")
    op.drop_index(op.f("idx_rule_versions_rule_id"), table_name="rule_versions")
    op.drop_table("rule_versions")
