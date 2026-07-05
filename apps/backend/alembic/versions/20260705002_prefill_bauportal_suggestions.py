"""pre-fill existing bauportal suggestions into the assignment

The DB-Bauportal review UI now shows the fuzzy suggestion by pre-filling it into
``project_id`` (unconfirmed), the same way the import task does for freshly
fetched rows. Rows imported before that change still carry the suggestion only
in ``suggested_project_id`` with ``project_id`` NULL, so their suggestion is
invisible in the new UI. Backfill them once — this reproduces exactly what a
re-fetch would produce, without contacting the network.

Revision ID: 20260705002
Revises: 20260705001
Create Date: 2026-07-05
"""

from alembic import op

revision = "20260705002"
down_revision = "20260705001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE bauportal_status
        SET project_id = suggested_project_id
        WHERE project_id IS NULL
          AND confirmed = false
          AND suggested_project_id IS NOT NULL
        """
    )


def downgrade() -> None:
    # Clear only the still-unconfirmed pre-fills (a confirmed match is a
    # deliberate assignment and must survive a downgrade).
    op.execute(
        """
        UPDATE bauportal_status
        SET project_id = NULL
        WHERE confirmed = false
          AND project_id IS NOT NULL
          AND project_id = suggested_project_id
        """
    )
