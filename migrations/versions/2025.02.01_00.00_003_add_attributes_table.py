"""Add attributes (facts) table for condition definitions

Revision ID: 003_add_attributes_table
Revises: add_rule_versioning_ab_testing
Create Date: 2025-02-01

This migration adds the attributes table for managing attribute/fact definitions
that can be referenced when defining conditions.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = "003_add_attributes_table"
down_revision: Union[str, None] = "add_rule_versioning_ab_testing"
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

    if not _table_exists(connection, "attributes"):
        op.create_table(
            "attributes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("attribute_id", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("data_type", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("updated_by", sa.String(length=255), nullable=True),
            sa.Column("tags", JSON(), nullable=True),
            sa.Column("metadata", JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("attribute_id"),
        )
        op.create_index("idx_attributes_attribute_id", "attributes", ["attribute_id"])
        op.create_index("idx_attributes_data_type", "attributes", ["data_type"])
        op.create_index("idx_attributes_status", "attributes", ["status"])


def downgrade() -> None:
    op.drop_index("idx_attributes_status", table_name="attributes")
    op.drop_index("idx_attributes_data_type", table_name="attributes")
    op.drop_index("idx_attributes_attribute_id", table_name="attributes")
    op.drop_table("attributes")
