"""add_description_to_llm_configs

Revision ID: a1b2c3d4e5f6
Revises: 132a14db05ac
Create Date: 2026-02-09 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '132a14db05ac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add description column to llm_configs table
    op.add_column('llm_configs', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove description column from llm_configs table
    op.drop_column('llm_configs', 'description')
