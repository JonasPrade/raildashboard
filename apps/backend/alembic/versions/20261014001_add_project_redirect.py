"""add project_redirect

Redirects from a merged (deleted) project id to the project it was merged into,
see docs/features/feature-project-merge.md. Purely additive, so older code keeps
working against the expanded schema. Written by hand: autogenerate needs a
PostGIS database and reports unrelated drift.

Revision ID: 20261014001
Revises: 20261012001
Create Date: 2026-10-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20261014001"
down_revision = "20261012001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_redirect",
        sa.Column("old_project_id", sa.Integer(), primary_key=True),
        sa.Column(
            "new_project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("old_name", sa.String(), nullable=True),
        sa.Column("merged_at", sa.DateTime(), nullable=False),
        sa.Column(
            "merged_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_project_redirect_new_project_id", "project_redirect", ["new_project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_project_redirect_new_project_id", table_name="project_redirect")
    op.drop_table("project_redirect")
