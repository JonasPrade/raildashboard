"""add progress_phase to finve

Revision ID: fd26d250fcf9
Revises: bbe060c86293
Create Date: 2026-06-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fd26d250fcf9'
down_revision: Union[str, None] = 'bbe060c86293'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('finve', sa.Column('progress_phase', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('finve', 'progress_phase')
