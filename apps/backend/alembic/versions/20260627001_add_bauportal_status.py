"""add bauportal_status table + provenance FK on progress_observation

Revision ID: 20260627001
Revises: 4914f4f1c36a
Create Date: 2026-06-27

DB-Bauportal importer (#47): raw table for fetched Bauportal projects plus a
nullable provenance FK so materialised BAUPORTAL observations can point back to
the source record (regenerated on resync, history survives via SET NULL).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260627001'
down_revision: Union[str, None] = '4914f4f1c36a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bauportal_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bauportal_id', sa.Integer(), nullable=False),
        sa.Column('parent_bauportal_id', sa.Integer(), nullable=True),
        sa.Column('shorttitle', sa.String(length=500), nullable=False),
        sa.Column('status_raw', sa.String(length=120), nullable=True),
        sa.Column('projecttime_raw', sa.String(length=120), nullable=True),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('raw_json', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('suggested_project_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['suggested_project_id'], ['project.id'],
            name='fk_bauportal_status_suggested_project_id', ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'],
            name='fk_bauportal_status_project_id', ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bauportal_status_id'), 'bauportal_status', ['id'], unique=False)
    op.create_index(
        op.f('ix_bauportal_status_bauportal_id'), 'bauportal_status', ['bauportal_id'], unique=True
    )
    op.create_index(
        op.f('ix_bauportal_status_project_id'), 'bauportal_status', ['project_id'], unique=False
    )

    op.add_column(
        'progress_observation',
        sa.Column('bauportal_status_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_progress_observation_bauportal_status_id',
        'progress_observation', 'bauportal_status',
        ['bauportal_status_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_progress_observation_bauportal_status_id', 'progress_observation', type_='foreignkey'
    )
    op.drop_column('progress_observation', 'bauportal_status_id')
    op.drop_index(op.f('ix_bauportal_status_project_id'), table_name='bauportal_status')
    op.drop_index(op.f('ix_bauportal_status_bauportal_id'), table_name='bauportal_status')
    op.drop_index(op.f('ix_bauportal_status_id'), table_name='bauportal_status')
    op.drop_table('bauportal_status')
