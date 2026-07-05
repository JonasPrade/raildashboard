"""add announcement_year to fulda_announcement

Revision ID: 20260628001
Revises: 20260627003
Create Date: 2026-06-28

Year-scoped Fulda-Runde importer (#46): each Kleine-Anfrage answer belongs to a
year. Backfill existing rows from the document date (fallback 2026), then make
the column NOT NULL and index it for per-year filtering.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260628001'
down_revision: Union[str, None] = '20260627003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fulda_announcement',
        sa.Column('announcement_year', sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE fulda_announcement "
        "SET announcement_year = COALESCE(EXTRACT(YEAR FROM document_date)::int, 2026) "
        "WHERE announcement_year IS NULL"
    )
    op.alter_column('fulda_announcement', 'announcement_year', nullable=False)
    op.create_index(
        op.f('ix_fulda_announcement_announcement_year'),
        'fulda_announcement', ['announcement_year'], unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_fulda_announcement_announcement_year'), table_name='fulda_announcement'
    )
    op.drop_column('fulda_announcement', 'announcement_year')
