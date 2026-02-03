"""create consumer_rule_usage table

Revision ID: 20260203_consumer_rule_usage
Revises: 
Create Date: 2026-02-03 23:03:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260203_consumer_usage'
down_revision = '004_widen_action_result'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'consumer_rule_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('consumer_id', sa.String(length=255), nullable=False),
        sa.Column('rule_id', sa.String(length=255), nullable=False),
        sa.Column('ruleset_id', sa.Integer(), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_executed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_consumer_rule_usage_consumer_id'), 'consumer_rule_usage', ['consumer_id'], unique=False)
    op.create_index(op.f('idx_consumer_rule_usage_rule_id'), 'consumer_rule_usage', ['rule_id'], unique=False)
    # Compound index for frequent lookups
    op.create_index('idx_consumer_usage_lookup', 'consumer_rule_usage', ['consumer_id', 'rule_id'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_consumer_usage_lookup', table_name='consumer_rule_usage')
    op.drop_index(op.f('idx_consumer_rule_usage_rule_id'), table_name='consumer_rule_usage')
    op.drop_index(op.f('idx_consumer_rule_usage_consumer_id'), table_name='consumer_rule_usage')
    op.drop_table('consumer_rule_usage')
