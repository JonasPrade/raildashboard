"""add ocr_raw_text, ocr_status, ocr_model to vib_draft_report

Revision ID: 20260407001
Revises: 20260401001
Create Date: 2026-04-07

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260407001"
down_revision: Union[str, None] = "20260401001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vib_draft_report", sa.Column("ocr_raw_text", sa.Text(), nullable=True))
    op.add_column("vib_draft_report", sa.Column("ocr_status", sa.String(20), nullable=True))
    op.add_column("vib_draft_report", sa.Column("ocr_model", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("vib_draft_report", "ocr_model")
    op.drop_column("vib_draft_report", "ocr_status")
    op.drop_column("vib_draft_report", "ocr_raw_text")
