"""add project progress and observations

Revision ID: bbe060c86293
Revises: 20260618001
Create Date: 2026-06-18 13:09:07.118183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bbe060c86293'
down_revision: Union[str, None] = '20260618001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('has_planfeststellung', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('parl_befassung_relevant', sa.Boolean(), nullable=True),
        sa.Column('lifecycle_status', sa.String(length=20), server_default='AKTIV', nullable=False),
        sa.Column('computed_phase', sa.String(length=40), nullable=True),
        sa.Column('computed_confidence', sa.Float(), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=True),
        sa.Column('manual_phase_override', sa.String(length=40), nullable=True),
        sa.Column('manual_override_note', sa.Text(), nullable=True),
        sa.Column('pf_state_override', sa.String(length=20), nullable=True),
        sa.Column('parl_state_override', sa.String(length=20), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_project_progress_id'), 'project_progress', ['id'], unique=False)
    op.create_index(op.f('ix_project_progress_project_id'), 'project_progress', ['project_id'], unique=True)

    op.create_table(
        'progress_observation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('track', sa.String(length=10), nullable=False),
        sa.Column('asserted_state', sa.String(length=40), nullable=False),
        sa.Column('observed_date', sa.Date(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('vib_entry_id', sa.Integer(), nullable=True),
        sa.Column('vib_pfa_entry_id', sa.Integer(), nullable=True),
        sa.Column('finve_id', sa.Integer(), nullable=True),
        sa.Column('is_derived', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('username_snapshot', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['finve_id'], ['finve.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vib_entry_id'], ['vib_entry.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vib_pfa_entry_id'], ['vib_pfa_entry.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_progress_observation_id'), 'progress_observation', ['id'], unique=False)
    op.create_index(op.f('ix_progress_observation_project_id'), 'progress_observation', ['project_id'], unique=False)

    op.create_table(
        'progress_track_document',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('track', sa.String(length=10), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['document.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'track', 'document_id', name='uq_progress_track_document'),
    )
    op.create_index(
        op.f('ix_progress_track_document_project_id'),
        'progress_track_document', ['project_id'], unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_progress_track_document_project_id'), table_name='progress_track_document')
    op.drop_table('progress_track_document')
    op.drop_index(op.f('ix_progress_observation_project_id'), table_name='progress_observation')
    op.drop_index(op.f('ix_progress_observation_id'), table_name='progress_observation')
    op.drop_table('progress_observation')
    op.drop_index(op.f('ix_project_progress_project_id'), table_name='project_progress')
    op.drop_index(op.f('ix_project_progress_id'), table_name='project_progress')
    op.drop_table('project_progress')
