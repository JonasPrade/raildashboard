"""add is_visible to project_group

Revision ID: 20260311003
Revises: 20260311002
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = '20260311003'
down_revision = '20260311002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'project_group',
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true',
                  comment='if false, this group is hidden from the map entirely'),
    )


def downgrade():
    op.drop_column('project_group', 'is_visible')
