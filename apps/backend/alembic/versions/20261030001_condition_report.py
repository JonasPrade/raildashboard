"""InfraGO-Zustandsbericht tables

docs/features/feature-zustandsbericht.md → "Datenmodell": ``condition_report``
(one per year), ``condition_asset_class`` (shared by all years, the 2025
classes are created on first use) and ``condition_value`` (long format).
Grants the new ``condition.import`` capability to the editor system role.

Expand only: three new tables, nothing existing changes.

Revision ID: 20261030001
Revises: 20261027001
Create Date: 2026-10-30
"""

from alembic import op
import sqlalchemy as sa

revision = "20261030001"
down_revision = "20261027001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "condition_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("price_basis", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ENTWURF"),
        sa.Column("accepted_mismatches", sa.JSON(), nullable=True),
        sa.Column("created_by_snapshot", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("released_by_snapshot", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_condition_report_id", "condition_report", ["id"])
    op.create_index("ix_condition_report_year", "condition_report", ["year"], unique=True)

    op.create_table(
        "condition_asset_class",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("trade", sa.String(length=10), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_condition_asset_class_id", "condition_asset_class", ["id"])

    op.create_table(
        "condition_value",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "report_id",
            sa.Integer(),
            sa.ForeignKey("condition_report.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=10), nullable=False),
        sa.Column("region", sa.String(length=2), nullable=True),
        sa.Column(
            "asset_class_id",
            sa.Integer(),
            sa.ForeignKey("condition_asset_class.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("metric", sa.String(length=30), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column("reference_year", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(14, 3), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="UNGEPRUEFT"),
        sa.Column("entered_by_snapshot", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "report_id", "domain", "scope", "region", "asset_class_id", "metric", "grade",
            "reference_year",
            name="uq_condition_value",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index("ix_condition_value_id", "condition_value", ["id"])
    op.create_index("ix_condition_value_report_id", "condition_value", ["report_id"])
    op.create_index("ix_condition_value_asset_class_id", "condition_value", ["asset_class_id"])

    # Grant the new capability to the editor system role (idempotent).
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT r.id, 'condition.import' FROM roles r WHERE r.name = 'editor'
            ON CONFLICT (role_id, permission_key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM role_permissions WHERE permission_key = 'condition.import'"))
    op.drop_table("condition_value")
    op.drop_table("condition_asset_class")
    op.drop_table("condition_report")
