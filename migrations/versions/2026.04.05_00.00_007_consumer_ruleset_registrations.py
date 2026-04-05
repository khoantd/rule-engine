"""
Consumer ruleset registrations and execution_logs.consumer_id.

Revision ID: 007_consumer_ruleset_registrations
Revises: 006_rules_unique_ruleset_rule_id
Create Date: 2026-04-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_consumer_ruleset_registrations"
down_revision: Union[str, None] = "006_rules_unique_ruleset_rule_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consumer_ruleset_registrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consumer_id", sa.String(length=255), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ruleset_id"], ["rulesets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consumer_id", "ruleset_id", name="uq_consumer_ruleset_registration"),
    )
    op.create_index("idx_crr_consumer_id", "consumer_ruleset_registrations", ["consumer_id"])
    op.create_index("idx_crr_ruleset_id", "consumer_ruleset_registrations", ["ruleset_id"])
    op.create_index(
        "idx_crr_consumer_ruleset_status",
        "consumer_ruleset_registrations",
        ["consumer_id", "status"],
    )

    op.add_column(
        "execution_logs",
        sa.Column("consumer_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "idx_execution_logs_consumer_id",
        "execution_logs",
        ["consumer_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_execution_logs_consumer_id", table_name="execution_logs")
    op.drop_column("execution_logs", "consumer_id")

    op.drop_index("idx_crr_consumer_ruleset_status", table_name="consumer_ruleset_registrations")
    op.drop_index("idx_crr_ruleset_id", table_name="consumer_ruleset_registrations")
    op.drop_index("idx_crr_consumer_id", table_name="consumer_ruleset_registrations")
    op.drop_table("consumer_ruleset_registrations")
