"""add GVFG-Bundesprogramm tables

Editions of the GVFG-Bundesprogramm, their Vorhaben with ∑/A/B/C amount lines,
the m:n link to projects and the staged parse results, see
docs/features/feature-gvfg-import.md. Grants the new ``gvfg.import`` capability
to the editor system role (mirrors ``core.permissions``). Purely additive. Written by hand:
autogenerate needs a PostGIS database and reports unrelated drift.

Revision ID: 20261015001
Revises: 20261014001
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "20261015001"
down_revision = "20261014001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gvfg_program",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year_from", sa.Integer(), nullable=False, unique=True),
        sa.Column("year_to", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("stand", sa.Date(), nullable=True),
        sa.Column("periods", sa.JSON(), nullable=False),
        sa.Column("has_annex", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "gvfg_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "program_id",
            sa.Integer(),
            sa.ForeignKey("gvfg_program.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(20), nullable=False),
        sa.Column("key_raw", sa.String(40), nullable=False),
        sa.Column("land", sa.String(40), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("part", sa.String(20), nullable=False),
        sa.Column("nr", sa.String(10), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("lph", sa.String(20), nullable=True),
        sa.Column("funding_type", sa.String(100), nullable=True),
        sa.Column("funding_rate", sa.Integer(), nullable=True),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("construction_start", sa.Integer(), nullable=True),
        sa.Column("commissioning_planned", sa.Integer(), nullable=True),
        sa.Column("commissioning_actual", sa.Integer(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.UniqueConstraint("program_id", "key", name="uq_gvfg_entry_program_key"),
    )
    op.create_index("ix_gvfg_entry_program_id", "gvfg_entry", ["program_id"])
    op.create_index("ix_gvfg_entry_key", "gvfg_entry", ["key"])
    op.create_table(
        "gvfg_entry_amount",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("gvfg_entry.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(5), nullable=False),
        sa.Column("computed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cost_total", sa.Numeric(14, 2), nullable=True),
        sa.Column("cost_eligible", sa.Numeric(14, 2), nullable=True),
        sa.Column("aid_total", sa.Numeric(14, 2), nullable=True),
        sa.Column("periods", sa.JSON(), nullable=False),
    )
    op.create_index("ix_gvfg_entry_amount_entry_id", "gvfg_entry_amount", ["entry_id"])
    op.create_table(
        "gvfg_entry_project",
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("gvfg_entry.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_gvfg_entry_project_project_id", "gvfg_entry_project", ["project_id"])
    op.create_table(
        "gvfg_parse_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pdf_filename", sa.String(255), nullable=False),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.Column("is_annex", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(), nullable=False),
        sa.Column(
            "parsed_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("username_snapshot", sa.String(100), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_by_snapshot", sa.String(100), nullable=True),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT r.id, 'gvfg.import' FROM roles r WHERE r.name = 'editor'
            ON CONFLICT (role_id, permission_key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM role_permissions WHERE permission_key = 'gvfg.import'"))
    op.drop_table("gvfg_parse_result")
    op.drop_index("ix_gvfg_entry_project_project_id", table_name="gvfg_entry_project")
    op.drop_table("gvfg_entry_project")
    op.drop_index("ix_gvfg_entry_amount_entry_id", table_name="gvfg_entry_amount")
    op.drop_table("gvfg_entry_amount")
    op.drop_index("ix_gvfg_entry_key", table_name="gvfg_entry")
    op.drop_index("ix_gvfg_entry_program_id", table_name="gvfg_entry")
    op.drop_table("gvfg_entry")
    op.drop_table("gvfg_program")
