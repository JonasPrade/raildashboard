"""lifecycle ERSETZT: successor, reason and date on project_progress

docs/features/feature-project-replacement.md:

- ``project_progress.replaced_by_project_id`` (FK project, ON DELETE SET NULL):
  successor of a project whose lifecycle is ERSETZT;
- ``project_progress.lifecycle_note`` / ``lifecycle_date``: reason and start
  date of any lifecycle status other than AKTIV.

``lifecycle_status`` is a plain String(20), so the new value ERSETZT needs no
schema change. Expand only: all columns are nullable, older code ignores them.

Revision ID: 20261023001
Revises: 20261022004
Create Date: 2026-10-23
"""

from alembic import op
import sqlalchemy as sa

revision = "20261023001"
down_revision = "20261022004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_progress", sa.Column("replaced_by_project_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_project_progress_replaced_by_project_id",
        "project_progress",
        "project",
        ["replaced_by_project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_project_progress_replaced_by_project_id",
        "project_progress",
        ["replaced_by_project_id"],
    )
    op.add_column("project_progress", sa.Column("lifecycle_note", sa.Text(), nullable=True))
    op.add_column("project_progress", sa.Column("lifecycle_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_progress", "lifecycle_date")
    op.drop_column("project_progress", "lifecycle_note")
    op.drop_index("ix_project_progress_replaced_by_project_id", table_name="project_progress")
    op.drop_constraint(
        "fk_project_progress_replaced_by_project_id", "project_progress", type_="foreignkey"
    )
    op.drop_column("project_progress", "replaced_by_project_id")
