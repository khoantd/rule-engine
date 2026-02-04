"""
Create workflows and workflow_stages tables.

Revision ID: 005_workflows
Revises: 20260203_consumer_usage
Create Date: 2026-02-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_workflows"
down_revision: Union[str, None] = "20260203_consumer_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database to add workflow definition tables."""
    op.create_table(
        "workflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflows")),
        sa.UniqueConstraint("name", name=op.f("uq_workflows_name")),
    )
    op.create_index(
        op.f("idx_workflows_is_active"),
        "workflows",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "workflow_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            name=op.f("fk_workflow_stages_workflow_id_workflows"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_stages")),
    )
    op.create_index(
        op.f("idx_workflow_stages_workflow_position"),
        "workflow_stages",
        ["workflow_id", "position"],
        unique=False,
    )
    op.create_index(
        op.f("idx_workflow_stages_workflow_name"),
        "workflow_stages",
        ["workflow_id", "name"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database by removing workflow definition tables."""
    op.drop_index(
        op.f("idx_workflow_stages_workflow_name"),
        table_name="workflow_stages",
    )
    op.drop_index(
        op.f("idx_workflow_stages_workflow_position"),
        table_name="workflow_stages",
    )
    op.drop_table("workflow_stages")

    op.drop_index(
        op.f("idx_workflows_is_active"),
        table_name="workflows",
    )
    op.drop_table("workflows")

