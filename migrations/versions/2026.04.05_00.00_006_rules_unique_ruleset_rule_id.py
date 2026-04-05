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


def _pg_constraint_exists(bind, name: str) -> bool:
    row = bind.execute(sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": name}).first()
    return row is not None


def upgrade() -> None:
    """Remove duplicate rule rows, then enforce uniqueness on (ruleset_id, rule_id)."""
    bind = op.get_bind()
    # Single huge DELETE can hold locks for a long time; delete in batches so startup/health
    # checks can make progress on slow instances. Same duplicate selection as one-shot USING.
    batch_sql = sa.text(
        """
        DELETE FROM rules
        WHERE ctid IN (
            SELECT ctid
            FROM (
                SELECT r.ctid
                FROM rules AS r
                INNER JOIN (
                    SELECT ruleset_id, rule_id, MIN(id) AS keep_id
                    FROM rules
                    GROUP BY ruleset_id, rule_id
                ) AS k
                  ON r.ruleset_id = k.ruleset_id
                 AND r.rule_id = k.rule_id
                 AND r.id <> k.keep_id
                LIMIT 10000
            ) AS batch
        )
        """
    )
    _max_batches = 1_000_000
    _one_shot = sa.text(
        """
        DELETE FROM rules AS r
        USING (
            SELECT ruleset_id, rule_id, MIN(id) AS keep_id
            FROM rules
            GROUP BY ruleset_id, rule_id
        ) AS k
        WHERE r.ruleset_id = k.ruleset_id
          AND r.rule_id = k.rule_id
          AND r.id <> k.keep_id
        """
    )
    for _ in range(_max_batches):
        res = bind.execute(batch_sql)
        rc = res.rowcount
        if rc == 0:
            break
        if rc is None or rc < 0:
            bind.execute(_one_shot)
            break
    else:
        raise RuntimeError(
            "rules deduplication exceeded batch limit; check rules table and duplicates"
        )
    if not _pg_constraint_exists(bind, "uq_rules_ruleset_rule_id"):
        op.create_unique_constraint(
            "uq_rules_ruleset_rule_id",
            "rules",
            ["ruleset_id", "rule_id"],
        )


def downgrade() -> None:
    """Drop unique constraint on (ruleset_id, rule_id)."""
    op.execute(
        sa.text(
            "ALTER TABLE rules DROP CONSTRAINT IF EXISTS uq_rules_ruleset_rule_id"
        )
    )
