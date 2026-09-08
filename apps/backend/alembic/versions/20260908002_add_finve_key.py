"""add finve.finve_key

Identity for measures the budget report lists without a FinVe number: the tables
of Annex VWIB Part B beyond the Bedarfsplan table identify their entries by a
string ("t4:F 03 E 0793", "t5:B0094"). NULL for every FinVe that has a real
number, so existing rows are unaffected.

Revision ID: 20260908002
Revises: 20260908001
Create Date: 2026-09-08
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908002"
down_revision = "20260908001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("finve", sa.Column("finve_key", sa.String(length=120), nullable=True))
    op.create_index("ix_finve_finve_key", "finve", ["finve_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_finve_finve_key", table_name="finve")
    op.drop_column("finve", "finve_key")
