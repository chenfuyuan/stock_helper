"""add_vendor_to_llm_configs

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-09 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add vendor column to llm_configs table
    op.add_column('llm_configs', sa.Column('vendor', sa.String(), nullable=True))
    
    # Update existing rows with a default value if any exist
    op.execute("UPDATE llm_configs SET vendor = 'Unknown' WHERE vendor IS NULL")
    
    # Now set it to NOT NULL
    op.alter_column('llm_configs', 'vendor', nullable=False)


def downgrade() -> None:
    # Remove vendor column from llm_configs table
    op.drop_column('llm_configs', 'vendor')
