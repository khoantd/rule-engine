"""Widen action_result column from VARCHAR(10) to VARCHAR(500).

Revision ID: 004_widen_action_result
Revises: 003_add_attributes_table
Create Date: 2026-02-02

Fixes StringDataRightTruncation when storing rule action recommendations
longer than 10 characters (e.g. 'Strong engagement signals detected - prioritize outreach').
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_widen_action_result"
down_revision: Union[str, None] = "003_add_attributes_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen action_result to VARCHAR(500) on rules and rule_versions."""
    op.alter_column(
        "rules",
        "action_result",
        existing_type=sa.String(length=10),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
    op.alter_column(
        "rule_versions",
        "action_result",
        existing_type=sa.String(length=10),
        type_=sa.String(length=500),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert action_result to VARCHAR(10). Values longer than 10 chars will truncate."""
    op.alter_column(
        "rules",
        "action_result",
        existing_type=sa.String(length=500),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
    op.alter_column(
        "rule_versions",
        "action_result",
        existing_type=sa.String(length=500),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
