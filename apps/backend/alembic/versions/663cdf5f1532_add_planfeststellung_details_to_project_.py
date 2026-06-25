"""add planfeststellung details to project_progress

Revision ID: 663cdf5f1532
Revises: a1b2c3d4e5f6
Create Date: 2026-06-25

Free-text note, link to the Planfeststellungsbeschluss and the relevant date
for the Planfeststellung track. Mirrors the parliamentary involvement details
(see a1b2c3d4e5f6). The PF state itself remains pf_state_override, so no extra
column is needed for it.

Hand-written add_column migration (autogenerate is unusable here because the
database also carries the PostGIS/Tiger geocoder schema, which is not modelled
in SQLAlchemy and would otherwise be dropped).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '663cdf5f1532'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_progress', sa.Column('pf_text', sa.Text(), nullable=True))
    op.add_column('project_progress', sa.Column('pf_beschluss_url', sa.String(length=1000), nullable=True))
    op.add_column('project_progress', sa.Column('pf_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_progress', 'pf_date')
    op.drop_column('project_progress', 'pf_beschluss_url')
    op.drop_column('project_progress', 'pf_text')
