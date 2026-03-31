"""add planungsstand and project_status to vib_entry

Revision ID: 20260331001
Revises: 20260315001
Create Date: 2026-03-31

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260331001"
down_revision: Union[str, None] = "20260326001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vib_entry", sa.Column("planungsstand", sa.Text(), nullable=True))
    op.add_column("vib_entry", sa.Column("project_status", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("vib_entry", "project_status")
    op.drop_column("vib_entry", "planungsstand")
