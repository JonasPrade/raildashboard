"""add ocr_images_json to vib_draft_report

Revision ID: 20260407002
Revises: 20260407001
Create Date: 2026-04-07

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260407002"
down_revision: Union[str, None] = "20260407001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vib_draft_report", sa.Column("ocr_images_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vib_draft_report", "ocr_images_json")
