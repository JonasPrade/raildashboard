"""add text_attachment table

Revision ID: 20260326001
Revises: 20260315001
Create Date: 2026-03-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260326001"
down_revision: Union[str, None] = "20260315001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "text_attachment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "text_id",
            sa.Integer(),
            sa.ForeignKey("project_text.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("text_attachment")
