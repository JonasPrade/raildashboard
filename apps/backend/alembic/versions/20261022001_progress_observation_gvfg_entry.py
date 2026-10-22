"""progress observation gvfg entry

docs/features/feature-project-progress.md → "Planungsstand aus dem
GVFG-Bundesprogramm": adds the nullable provenance column
``progress_observation.gvfg_entry_id`` for observations derived from a GVFG
edition. Expand only: older code ignores the column.

Revision ID: 20261022001
Revises: 20261021004
Create Date: 2026-10-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20261022001"
down_revision = "20261021004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("progress_observation", sa.Column("gvfg_entry_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_progress_observation_gvfg_entry_id", "progress_observation", "gvfg_entry",
        ["gvfg_entry_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_progress_observation_gvfg_entry_id", "progress_observation", type_="foreignkey")
    op.drop_column("progress_observation", "gvfg_entry_id")
