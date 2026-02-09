"""create_llm_config_table

Revision ID: 132a14db05ac
Revises: d25e5d13455c
Create Date: 2026-02-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '132a14db05ac'
down_revision = 'd25e5d13455c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('llm_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alias', sa.String(), nullable=False),
        sa.Column('provider_type', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=False),
        sa.Column('base_url', sa.String(), nullable=True),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_configs_alias'), 'llm_configs', ['alias'], unique=True)
    op.create_index(op.f('ix_llm_configs_id'), 'llm_configs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_llm_configs_id'), table_name='llm_configs')
    op.drop_index(op.f('ix_llm_configs_alias'), table_name='llm_configs')
    op.drop_table('llm_configs')
