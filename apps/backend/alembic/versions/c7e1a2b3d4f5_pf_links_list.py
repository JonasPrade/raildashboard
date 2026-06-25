"""replace pf_beschluss_url with a commented pf_links list

Revision ID: c7e1a2b3d4f5
Revises: 663cdf5f1532
Create Date: 2026-06-25

Planfeststellung references move from a single URL (pf_beschluss_url) + document-id
linking to a JSON list of commented links: ``[{"url": str, "comment": str|None}]``.
Existing single links are carried over as one entry.

Hand-written (autogenerate is unusable here — the database also carries the
PostGIS/Tiger geocoder schema, which is not modelled in SQLAlchemy).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7e1a2b3d4f5'
down_revision: Union[str, None] = '663cdf5f1532'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_progress', sa.Column('pf_links', sa.JSON(), nullable=True))
    # Carry an existing single PFB link over into the new list.
    op.execute(
        """
        UPDATE project_progress
        SET pf_links = json_build_array(
            json_build_object('url', pf_beschluss_url, 'comment', 'Planfeststellungsbeschluss')
        )
        WHERE pf_beschluss_url IS NOT NULL AND pf_beschluss_url <> ''
        """
    )
    op.drop_column('project_progress', 'pf_beschluss_url')


def downgrade() -> None:
    op.add_column(
        'project_progress',
        sa.Column('pf_beschluss_url', sa.String(length=1000), nullable=True),
    )
    op.execute(
        """
        UPDATE project_progress
        SET pf_beschluss_url = (pf_links->0->>'url')
        WHERE pf_links IS NOT NULL AND json_array_length(pf_links) > 0
        """
    )
    op.drop_column('project_progress', 'pf_links')
