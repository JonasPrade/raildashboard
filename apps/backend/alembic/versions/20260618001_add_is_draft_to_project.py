"""add is_draft to project

Revision ID: 20260618001
Revises: fd1890f1f281
Create Date: 2026-06-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260618001"
down_revision: Union[str, None] = "fd1890f1f281"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing projects are finalized (server_default "false"), so they stay
    # visible in the public list. New wizard projects are created as drafts.
    op.add_column(
        "project",
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("project", "is_draft")
