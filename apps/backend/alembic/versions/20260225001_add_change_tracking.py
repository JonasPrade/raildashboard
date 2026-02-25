"""add change tracking tables

Revision ID: 20260225001
Revises: 202510241300
Create Date: 2026-02-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260225001"
down_revision: Union[str, None] = "202510241300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "change_log",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("username_snapshot", sa.String(length=50), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("action", sa.String(length=20), nullable=False, server_default="PATCH"),
    )

    op.create_table(
        "change_log_entry",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "changelog_id",
            sa.Integer(),
            sa.ForeignKey("change_log.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("change_log_entry")
    op.drop_table("change_log")
