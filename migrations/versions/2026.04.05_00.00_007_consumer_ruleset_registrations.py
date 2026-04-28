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


def _table_exists(bind, table_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :name)"
            ),
            {"name": table_name},
        ).scalar()
    )


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c)"
            ),
            {"t": table_name, "c": column_name},
        ).scalar()
    )


def _index_exists(bind, index_name: str) -> bool:
    row = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"),
        {"n": index_name},
    ).first()
    return row is not None


def upgrade() -> None:
    bind = op.get_bind()

    # Default Alembic creates version_num as VARCHAR(32). This revision id is 34 characters,
    # so stamping the DB fails with "value too long for type character varying(32)" unless widened.
    if _table_exists(bind, "alembic_version"):
        op.execute(
            sa.text(
                "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )

    if not _table_exists(bind, "consumer_ruleset_registrations"):
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

    if _table_exists(bind, "consumer_ruleset_registrations"):
        if not _index_exists(bind, "idx_crr_consumer_id"):
            op.create_index("idx_crr_consumer_id", "consumer_ruleset_registrations", ["consumer_id"])
        if not _index_exists(bind, "idx_crr_ruleset_id"):
            op.create_index("idx_crr_ruleset_id", "consumer_ruleset_registrations", ["ruleset_id"])
        if not _index_exists(bind, "idx_crr_consumer_ruleset_status"):
            op.create_index(
                "idx_crr_consumer_ruleset_status",
                "consumer_ruleset_registrations",
                ["consumer_id", "status"],
            )

    if not _column_exists(bind, "execution_logs", "consumer_id"):
        op.add_column(
            "execution_logs",
            sa.Column("consumer_id", sa.String(length=255), nullable=True),
        )
    # Large execution_logs (e.g. Timescale): a normal CREATE INDEX blocks writers and can run
    # for a very long time. CONCURRENTLY must run outside a transaction (autocommit_block).
    if not _index_exists(bind, "idx_execution_logs_consumer_id"):
        with op.get_context().autocommit_block():
            op.execute(sa.text("SET statement_timeout = 0"))
            op.create_index(
                "idx_execution_logs_consumer_id",
                "execution_logs",
                ["consumer_id"],
                postgresql_concurrently=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("DROP INDEX IF EXISTS idx_execution_logs_consumer_id"))
    if _column_exists(bind, "execution_logs", "consumer_id"):
        op.drop_column("execution_logs", "consumer_id")

    op.execute(sa.text("DROP INDEX IF EXISTS idx_crr_consumer_ruleset_status"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_crr_ruleset_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_crr_consumer_id"))
    if _table_exists(bind, "consumer_ruleset_registrations"):
        op.drop_table("consumer_ruleset_registrations")
