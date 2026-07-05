"""add abschnitt to fulda_announcement

The Fulda-Runde answer lists each project with an Abschnitt (the table's second
column, or the part after the colon in the bullet-list questions). In the
dashboard the Abschnitt becomes the subproject, so it must be stored per row.

Revision ID: 20260630001
Revises: 20260628002
Create Date: 2026-06-30
"""

from alembic import op
import sqlalchemy as sa

revision = "20260630001"
down_revision = "20260628002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fulda_announcement",
        sa.Column("abschnitt", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fulda_announcement", "abschnitt")
