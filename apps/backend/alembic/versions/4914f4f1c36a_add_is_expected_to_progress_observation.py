"""add is_expected to progress_observation

Revision ID: 4914f4f1c36a
Revises: e4a1b2c3d5f6
Create Date: 2026-06-26 09:48:54.802483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4914f4f1c36a'
down_revision: Union[str, None] = 'e4a1b2c3d5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'progress_observation',
        sa.Column(
            'is_expected',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('progress_observation', 'is_expected')
