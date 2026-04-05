"""
Deduplicate rules per (ruleset_id, rule_id) and add unique constraint.

Revision ID: 006_rules_unique_ruleset_rule_id
Revises: 005_workflows
Create Date: 2026-04-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_rules_unique_ruleset_rule_id"
down_revision: Union[str, None] = "005_workflows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove duplicate rule rows, then enforce uniqueness on (ruleset_id, rule_id)."""
    bind = op.get_bind()
    # Keep the lowest primary key for each (ruleset_id, rule_id) pair.
    bind.execute(
        sa.text(
            """
            DELETE FROM rules
            WHERE id NOT IN (
                SELECT MIN(id) FROM rules GROUP BY ruleset_id, rule_id
            )
            """
        )
    )
    op.create_unique_constraint(
        "uq_rules_ruleset_rule_id",
        "rules",
        ["ruleset_id", "rule_id"],
    )


def downgrade() -> None:
    """Drop unique constraint on (ruleset_id, rule_id)."""
    op.drop_constraint("uq_rules_ruleset_rule_id", "rules", type_="unique")
