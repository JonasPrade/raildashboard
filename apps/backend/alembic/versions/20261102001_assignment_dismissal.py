"""Permanently ignored open assignments

docs/features/feature-unassigned-assignments.md → „Dauerhaft ignorieren“:
``assignment_dismissal`` hides a FinVe, VIB entry, GVFG Vorhaben or Infraplan
row from „Offene Zuordnungen“ (``kind`` + ``entry_id``, unique).

Expand only: a new table. An older backend after a rollback does not read it
and simply shows the ignored rows again.

Revision ID: 20261102001
Revises: 20261101001
Create Date: 2026-11-02
"""

from alembic import op
import sqlalchemy as sa

revision = "20261102001"
down_revision = "20261101001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assignment_dismissal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "dismissed_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("kind", "entry_id", name="uq_assignment_dismissal_kind_entry"),
    )


def downgrade() -> None:
    op.drop_table("assignment_dismissal")
