"""replace vib_entry.project_id FK with vib_entry_project m2n table

Revision ID: 20260408001
Revises: 20260407002
Create Date: 2026-04-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260408001"
down_revision: Union[str, None] = "20260407002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vib_entry_project",
        sa.Column(
            "vib_entry_id",
            sa.Integer(),
            sa.ForeignKey("vib_entry.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )

    # Migrate existing single-project links into the new association table
    op.execute(
        "INSERT INTO vib_entry_project (vib_entry_id, project_id) "
        "SELECT id, project_id FROM vib_entry WHERE project_id IS NOT NULL"
    )

    op.drop_column("vib_entry", "project_id")


def downgrade() -> None:
    op.add_column(
        "vib_entry",
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Restore one project_id per entry (take any linked project — order not guaranteed)
    op.execute(
        "UPDATE vib_entry SET project_id = ("
        "  SELECT project_id FROM vib_entry_project"
        "  WHERE vib_entry_project.vib_entry_id = vib_entry.id"
        "  LIMIT 1"
        ")"
    )

    op.drop_table("vib_entry_project")
