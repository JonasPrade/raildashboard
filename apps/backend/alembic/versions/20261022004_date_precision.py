"""date precision of planning-state dates

docs/features/feature-project-progress.md → „Datumsqualifikation“:

- ``progress_observation.date_precision`` (EXACT | MONTH | YEAR | NOT_BEFORE |
  ASSUMED, server default EXACT — every existing row stays EXACT) and the
  optional free-text ``date_label``;
- ``project_group.assumed_build_months``: assumed construction period of the
  group's projects without a published closure period (HLK: 6 months);
- ``project_progress.construction_start_*`` / ``commissioning_*``: cached
  forecast dates with their precision for the list filters.

Expand only: new columns are nullable or have a server default, older code
ignores them. No observation is changed or deleted.

Revision ID: 20261022004
Revises: 20261022003
Create Date: 2026-10-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20261022004"
down_revision = "20261022003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "progress_observation",
        sa.Column("date_precision", sa.String(12), nullable=False, server_default="EXACT"),
    )
    op.add_column("progress_observation", sa.Column("date_label", sa.String(120), nullable=True))
    op.add_column("project_group", sa.Column("assumed_build_months", sa.Integer(), nullable=True))
    op.add_column("project_progress", sa.Column("construction_start_date", sa.Date(), nullable=True))
    op.add_column(
        "project_progress", sa.Column("construction_start_precision", sa.String(12), nullable=True)
    )
    op.add_column("project_progress", sa.Column("commissioning_date", sa.Date(), nullable=True))
    op.add_column(
        "project_progress", sa.Column("commissioning_precision", sa.String(12), nullable=True)
    )
    # Corridor renewals without a published closure period: 6 months.
    op.execute("UPDATE project_group SET assumed_build_months = 6 WHERE short_name = 'HLK'")


def downgrade() -> None:
    op.drop_column("project_progress", "commissioning_precision")
    op.drop_column("project_progress", "commissioning_date")
    op.drop_column("project_progress", "construction_start_precision")
    op.drop_column("project_progress", "construction_start_date")
    op.drop_column("project_group", "assumed_build_months")
    op.drop_column("progress_observation", "date_label")
    op.drop_column("progress_observation", "date_precision")
