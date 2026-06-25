"""add parliamentary involvement details to project_progress

Revision ID: a1b2c3d4e5f6
Revises: 91c0ee036d2e
Create Date: 2026-06-21

Free-text note, Bundestags-Drucksache link and date for the parliamentary
involvement track. The "Beschluss" itself remains the PARL track state
(parl_state_override), so no extra column is needed for it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '91c0ee036d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_progress', sa.Column('parl_befassung_text', sa.Text(), nullable=True))
    op.add_column('project_progress', sa.Column('parl_drucksache_url', sa.String(length=1000), nullable=True))
    op.add_column('project_progress', sa.Column('parl_befassung_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_progress', 'parl_befassung_date')
    op.drop_column('project_progress', 'parl_drucksache_url')
    op.drop_column('project_progress', 'parl_befassung_text')
