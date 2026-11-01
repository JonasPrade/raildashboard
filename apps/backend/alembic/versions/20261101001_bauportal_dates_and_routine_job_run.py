"""Bauportal observation dates and the routine job run table

docs/features/feature-routine-abrufe.md → "Technische Schritte" 1:

* ``bauportal_status.status_changed_at`` (set only when ``status_raw``
  changes) and ``bauportal_status.last_seen_at`` (set on every fetch), both
  back-filled from ``fetched_at``;
* ``routine_job_run`` — one row per run of a scheduled routine job
  (``job`` = ``bauportal``, ``progress_recompute``, …), decided 2026-11-01
  instead of a Bauportal-only run table.

Expand only: ``fetched_at`` stays until the contract release (#325). Both new
columns carry a server default, so an older backend that does not know them
keeps inserting rows after a rollback.

Revision ID: 20261101001
Revises: 20261030001
Create Date: 2026-11-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20261101001"
down_revision = "20261030001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bauportal_status",
        sa.Column(
            "status_changed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.add_column(
        "bauportal_status",
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "UPDATE bauportal_status SET status_changed_at = fetched_at, last_seen_at = fetched_at"
    )

    op.create_table(
        "routine_job_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("stats", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "triggered_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_routine_job_run_job", "routine_job_run", ["job"])


def downgrade() -> None:
    op.drop_index("ix_routine_job_run_job", table_name="routine_job_run")
    op.drop_table("routine_job_run")
    op.drop_column("bauportal_status", "last_seen_at")
    op.drop_column("bauportal_status", "status_changed_at")
