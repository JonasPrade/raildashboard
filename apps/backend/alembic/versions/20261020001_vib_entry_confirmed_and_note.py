"""vib entry confirmed flag, assignment note and page

docs/features/feature-vib-import.md → Phase 7: the VIB is read in by an agent
over MCP. Entries written that way stay unconfirmed until an editor (or the
agent's confirm step) confirms them; only confirmed entries materialise
progress observations. Existing entries are backfilled as confirmed (server
default) so the current progress does not change. Expand only.

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
    op.add_column(
        "vib_entry",
        sa.Column("confirmed", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column("vib_entry", sa.Column("assignment_note", sa.Text(), nullable=True))
    op.add_column("vib_entry", sa.Column("page", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("vib_entry", "page")
    op.drop_column("vib_entry", "assignment_note")
    op.drop_column("vib_entry", "confirmed")
