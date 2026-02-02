"""Add pattern_id to actions (1 pattern has many actions)

Revision ID: 002_add_pattern_id_to_actions
Revises: 001_initial_schema
Create Date: 2025-02-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_pattern_id_to_actions"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "actions",
        sa.Column("pattern_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_actions_pattern_id_patterns",
        "actions",
        "patterns",
        ["pattern_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_actions_pattern", "actions", ["pattern_id"])


def downgrade() -> None:
    op.drop_index("idx_actions_pattern", table_name="actions")
    op.drop_constraint(
        "fk_actions_pattern_id_patterns", "actions", type_="foreignkey"
    )
    op.drop_column("actions", "pattern_id")
