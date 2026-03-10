"""add is_sammel_finve to finve

Revision ID: 20260308001
Revises: 20260306001
Create Date: 2026-03-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260308001"
down_revision: Union[str, None] = "20260306001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "finve",
        sa.Column("is_sammel_finve", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("finve", "is_sammel_finve")
