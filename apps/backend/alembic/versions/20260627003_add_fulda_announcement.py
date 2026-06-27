"""add fulda_announcement table + provenance FK on progress_observation

Revision ID: 20260627003
Revises: 20260627002
Create Date: 2026-06-27

Fulda-Runde importer (#46): raw table for Kleine-Anfrage announcements plus a
nullable provenance FK so materialised FULDA_RUNDE observations point back.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260627003'
down_revision: Union[str, None] = '20260627002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fulda_announcement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_label', sa.String(length=255), nullable=True),
        sa.Column('document_date', sa.Date(), nullable=True),
        sa.Column('raw_name', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=40), nullable=True),
        sa.Column('announced_phase', sa.String(length=40), nullable=True),
        sa.Column('expected_date', sa.Date(), nullable=True),
        sa.Column('suggested_project_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('confirmed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('username_snapshot', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ['suggested_project_id'], ['project.id'],
            name='fk_fulda_announcement_suggested_project_id', ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'],
            name='fk_fulda_announcement_project_id', ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'], ['users.id'],
            name='fk_fulda_announcement_created_by_user_id', ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_fulda_announcement_id'), 'fulda_announcement', ['id'], unique=False)
    op.create_index(
        op.f('ix_fulda_announcement_project_id'), 'fulda_announcement', ['project_id'], unique=False
    )

    op.add_column(
        'progress_observation',
        sa.Column('fulda_announcement_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_progress_observation_fulda_announcement_id',
        'progress_observation', 'fulda_announcement',
        ['fulda_announcement_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_progress_observation_fulda_announcement_id', 'progress_observation', type_='foreignkey'
    )
    op.drop_column('progress_observation', 'fulda_announcement_id')
    op.drop_index(op.f('ix_fulda_announcement_project_id'), table_name='fulda_announcement')
    op.drop_index(op.f('ix_fulda_announcement_id'), table_name='fulda_announcement')
    op.drop_table('fulda_announcement')
