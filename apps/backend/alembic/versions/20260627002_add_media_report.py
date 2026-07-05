"""add media_report table + provenance FK on progress_observation

Revision ID: 20260627002
Revises: 20260627001
Create Date: 2026-06-27

Medien/Presse importer (#48): editor-owned raw table for press reports plus a
nullable provenance FK so materialised MEDIEN observations point back to the
source report.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260627002'
down_revision: Union[str, None] = '20260627001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'media_report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('publication', sa.String(length=255), nullable=True),
        sa.Column('published_date', sa.Date(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('quote', sa.Text(), nullable=True),
        sa.Column('asserted_phase', sa.String(length=40), nullable=True),
        sa.Column('observed_date', sa.Date(), nullable=True),
        sa.Column('suggested_project_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('confirmed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('username_snapshot', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ['suggested_project_id'], ['project.id'],
            name='fk_media_report_suggested_project_id', ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'],
            name='fk_media_report_project_id', ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'], ['users.id'],
            name='fk_media_report_created_by_user_id', ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_media_report_id'), 'media_report', ['id'], unique=False)
    op.create_index(
        op.f('ix_media_report_project_id'), 'media_report', ['project_id'], unique=False
    )

    op.add_column(
        'progress_observation',
        sa.Column('media_report_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_progress_observation_media_report_id',
        'progress_observation', 'media_report',
        ['media_report_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_progress_observation_media_report_id', 'progress_observation', type_='foreignkey'
    )
    op.drop_column('progress_observation', 'media_report_id')
    op.drop_index(op.f('ix_media_report_project_id'), table_name='media_report')
    op.drop_index(op.f('ix_media_report_id'), table_name='media_report')
    op.drop_table('media_report')
