"""add confirmed flag to bauportal_status

Bring the DB-Bauportal importer in line with the Fulda-Runde importer: the fuzzy
suggestion is pre-filled into ``project_id`` on import, but a derived BAUPORTAL
observation is only materialised once an editor confirms the match. Existing
matched rows (``project_id`` set) were effectively confirmed under the old
one-step flow, so backfill ``confirmed = true`` for them to preserve their
observations.

Revision ID: 20260705001
Revises: 20260630001
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa

revision = "20260705001"
down_revision = "20260630001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bauportal_status",
        sa.Column(
            "confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Existing matched rows were auto-confirmed under the old flow → keep them.
    op.execute(
        "UPDATE bauportal_status SET confirmed = true WHERE project_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("bauportal_status", "confirmed")
