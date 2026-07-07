"""add guide_section_override table

Stores per-section markdown replacements for the in-app guide pages
("Anleitungen"). Guide content ships as versioned defaults in the frontend
bundle; users with the ``guides.edit`` capability can override single sections
here. Deleting a row falls back to the bundled default.

Revision ID: 20260707001
Revises: 20260705002
Create Date: 2026-07-07
"""

import sqlalchemy as sa
from alembic import op

revision = "20260707001"
down_revision = "20260705002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guide_section_override",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guide_slug", sa.String(length=100), nullable=False),
        sa.Column("section_key", sa.String(length=100), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("username_snapshot", sa.String(length=50), nullable=True),
        sa.UniqueConstraint("guide_slug", "section_key", name="uq_guide_section"),
    )
    op.create_index(
        "ix_guide_section_override_guide_slug",
        "guide_section_override",
        ["guide_slug"],
    )
    op.create_index(
        "ix_guide_section_override_id", "guide_section_override", ["id"]
    )


def downgrade() -> None:
    op.drop_index("ix_guide_section_override_id", table_name="guide_section_override")
    op.drop_index(
        "ix_guide_section_override_guide_slug", table_name="guide_section_override"
    )
    op.drop_table("guide_section_override")
