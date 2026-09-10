"""add stage-1 text and column mapping to haushalts_parse_result

Brings the Haushalt importer in line with the shared PDF pipeline: the run now
keeps the document text it was parsed from (``ocr_*``, same three columns the
VIB draft already had, now shared via ``models.mixins.OcrSourceMixin``) and the
column layout the values were transferred through (``column_map_*``).

All columns are nullable — rows from earlier runs keep NULL and the review UI
falls back to showing no mapping for them.

Revision ID: 20260908001
Revises: 20260731002
Create Date: 2026-09-08
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908001"
down_revision = "20260731002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("haushalts_parse_result", sa.Column("ocr_raw_text", sa.Text(), nullable=True))
    op.add_column("haushalts_parse_result", sa.Column("ocr_status", sa.String(length=20), nullable=True))
    op.add_column("haushalts_parse_result", sa.Column("ocr_model", sa.String(length=100), nullable=True))
    op.add_column("haushalts_parse_result", sa.Column("column_map_json", sa.JSON(), nullable=True))
    op.add_column(
        "haushalts_parse_result", sa.Column("column_map_source", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("haushalts_parse_result", "column_map_source")
    op.drop_column("haushalts_parse_result", "column_map_json")
    op.drop_column("haushalts_parse_result", "ocr_model")
    op.drop_column("haushalts_parse_result", "ocr_status")
    op.drop_column("haushalts_parse_result", "ocr_raw_text")
