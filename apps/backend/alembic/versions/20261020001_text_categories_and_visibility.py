"""text categories and visibility

docs/features/feature-text-categories.md: adds ``project_text_category`` with
the seeded categories „Info“ and „Warnung“, plus ``project_text.category_id``
and ``project_text.is_public``. Expand only: ``category_id`` stays nullable and
``is_public`` has a server default, so older code keeps inserting texts.
Existing texts get „Info“ and stay public.

Revision ID: 20261020001
Revises: 20261017001
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa

revision = "20261020001"
down_revision = "20261017001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    category = op.create_table(
        "project_text_category",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("style", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.bulk_insert(
        category,
        [
            {"name": "Info", "style": "info"},
            {"name": "Warnung", "style": "warning"},
        ],
    )

    op.add_column("project_text", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_project_text_category_id",
        "project_text",
        "project_text_category",
        ["category_id"],
        ["id"],
    )
    op.add_column(
        "project_text",
        sa.Column("is_public", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.execute(
        "UPDATE project_text SET category_id = "
        "(SELECT id FROM project_text_category WHERE name = 'Info')"
    )


def downgrade() -> None:
    op.drop_column("project_text", "is_public")
    op.drop_constraint("fk_project_text_category_id", "project_text", type_="foreignkey")
    op.drop_column("project_text", "category_id")
    op.drop_table("project_text_category")
