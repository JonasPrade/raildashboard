"""project archive flag

docs/features/feature-project-archive.md: ``project.is_archived`` (server
default false — every existing project stays visible), ``archived_reason``
and ``archived_at``.

Expand only: new columns are nullable or have a server default, older code
ignores them.

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
        "project",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("project", sa.Column("archived_reason", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("archived_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "archived_at")
    op.drop_column("project", "archived_reason")
    op.drop_column("project", "is_archived")
