"""add is_default_selected to project_group

Revision ID: 20260311001
Revises: 20260310001
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = '20260311001'
down_revision = '20260310001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'project_group',
        sa.Column('is_default_selected', sa.Boolean(), nullable=False, server_default='false',
                  comment='if true, this group is pre-selected on the map when no ?group= URL param is present'),
    )


def downgrade():
    op.drop_column('project_group', 'is_default_selected')
