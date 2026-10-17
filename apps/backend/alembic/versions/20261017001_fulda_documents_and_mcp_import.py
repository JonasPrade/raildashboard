"""fulda documents and mcp import

docs/features/feature-fulda-import.md: the Fulda-Runde is now read by an agent
over MCP. Adds ``fulda_document`` and the provenance columns of
``fulda_announcement`` (expand only — the old ``source_label`` /
``document_date`` / ``announced_phase`` columns stay for older code), deletes
all existing Fulda announcements together with their derived observations
(decision W6: the years are re-read from 2019 on) and grants the new
``fulda.import`` capability to the editor system role.

Revision ID: 20261017001
Revises: 20261015002
Create Date: 2026-10-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20261017001"
down_revision = "20261015002"
branch_labels = None
depends_on = None

_EDITOR_PERMISSIONS = ("fulda.import",)


def upgrade() -> None:
    op.create_table(
        "fulda_document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("drucksache", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("document_date", sa.Date(), nullable=False),
        sa.Column("dip_url", sa.String(length=500), nullable=True),
        sa.Column(
            "answer_status",
            sa.String(length=20),
            server_default="VOLLSTAENDIG",
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("username_snapshot", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drucksache"),
    )
    op.create_index("ix_fulda_document_id", "fulda_document", ["id"], unique=False)
    op.create_index("ix_fulda_document_year", "fulda_document", ["year"], unique=False)

    # Old data goes first (W6): derived observations would otherwise survive
    # as orphans (their FK is SET NULL), links go by CASCADE.
    op.execute(
        sa.text(
            "DELETE FROM progress_observation "
            "WHERE fulda_announcement_id IS NOT NULL "
            "OR (is_derived AND source_type = 'FULDA_RUNDE')"
        )
    )
    op.execute(sa.text("DELETE FROM fulda_announcement"))

    op.add_column("fulda_announcement", sa.Column("document_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_fulda_announcement_document_id", "fulda_announcement", ["document_id"], unique=False
    )
    op.create_foreign_key(
        "fk_fulda_announcement_document_id",
        "fulda_announcement",
        "fulda_document",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column(
        "fulda_announcement", sa.Column("question_ref", sa.String(length=100), nullable=True)
    )
    op.add_column("fulda_announcement", sa.Column("page", sa.Integer(), nullable=True))
    op.add_column("fulda_announcement", sa.Column("raw_text", sa.Text(), nullable=True))
    op.add_column(
        "fulda_announcement", sa.Column("attributed_to", sa.String(length=20), nullable=True)
    )
    op.add_column("fulda_announcement", sa.Column("assignment_note", sa.Text(), nullable=True))

    # Grant the new capability to the editor system role (idempotent).
    editor_values = ", ".join(f"('{key}')" for key in _EDITOR_PERMISSIONS)
    op.execute(
        sa.text(
            f"""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT r.id, k.permission_key
            FROM roles r
            JOIN (VALUES {editor_values}) AS k(permission_key) ON true
            WHERE r.name = 'editor'
            ON CONFLICT (role_id, permission_key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    editor_values = ", ".join(f"'{key}'" for key in _EDITOR_PERMISSIONS)
    op.execute(
        sa.text(f"DELETE FROM role_permissions WHERE permission_key IN ({editor_values})")
    )
    op.drop_column("fulda_announcement", "assignment_note")
    op.drop_column("fulda_announcement", "attributed_to")
    op.drop_column("fulda_announcement", "raw_text")
    op.drop_column("fulda_announcement", "page")
    op.drop_column("fulda_announcement", "question_ref")
    op.drop_constraint(
        "fk_fulda_announcement_document_id", "fulda_announcement", type_="foreignkey"
    )
    op.drop_index("ix_fulda_announcement_document_id", table_name="fulda_announcement")
    op.drop_column("fulda_announcement", "document_id")
    op.drop_index("ix_fulda_document_year", table_name="fulda_document")
    op.drop_index("ix_fulda_document_id", table_name="fulda_document")
    op.drop_table("fulda_document")
