"""add sonstiges to vib_entry

Revision ID: f77c3078826f
Revises: 070f64d16220
Create Date: 2026-04-14 20:08:44.454906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f77c3078826f'
down_revision: Union[str, None] = '070f64d16220'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vib_entry", sa.Column("sonstiges", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vib_entry", "sonstiges")
