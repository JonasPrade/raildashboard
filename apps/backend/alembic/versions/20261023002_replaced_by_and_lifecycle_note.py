"""successor of an archived project; reason and date of a lifecycle status

docs/features/feature-project-archive.md → „Ersetzt durch“ (#261):

- ``project.replaced_by_project_id`` (FK project, ON DELETE SET NULL): the
  project that replaced an archived one;
- ``project_progress.lifecycle_note`` / ``lifecycle_date``: reason and start
  date of PAUSIERT / ABGEBROCHEN.

Expand only: all columns are nullable, older code ignores them.

Revision ID: 20261023002
Revises: 20261023001
Create Date: 2026-10-23
"""

from alembic import op
import sqlalchemy as sa

revision = "20261023002"
down_revision = "20261023001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project", sa.Column("replaced_by_project_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_project_replaced_by_project_id",
        "project",
        "project",
        ["replaced_by_project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_project_replaced_by_project_id", "project", ["replaced_by_project_id"])
    op.add_column("project_progress", sa.Column("lifecycle_note", sa.Text(), nullable=True))
    op.add_column("project_progress", sa.Column("lifecycle_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_progress", "lifecycle_date")
    op.drop_column("project_progress", "lifecycle_note")
    op.drop_index("ix_project_replaced_by_project_id", table_name="project")
    op.drop_constraint("fk_project_replaced_by_project_id", "project", type_="foreignkey")
    op.drop_column("project", "replaced_by_project_id")
