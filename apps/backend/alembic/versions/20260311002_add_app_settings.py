"""add app_settings table

Revision ID: 20260311002
Revises: 20260311001
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = '20260311002'
down_revision = '20260311001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('map_group_mode', sa.String(20), nullable=False, server_default='preconfigured',
                  comment="'preconfigured' = use is_default_selected groups; 'all' = show all projects without group filter"),
    )
    # Insert the singleton row
    op.execute("INSERT INTO app_settings (id, map_group_mode) VALUES (1, 'preconfigured')")


def downgrade():
    op.drop_table('app_settings')
