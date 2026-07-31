"""add project.geojson_from_subprojects

Toggle deciding how a project with subprojects gets its map geometry: aggregated
from the subprojects (default, the previous unconditional behaviour) or maintained
on the project itself. Existing rows default to ``true`` and therefore keep their
current behaviour.

Revision ID: 20260731002
Revises: 20260731001
Create Date: 2026-07-31
"""

import sqlalchemy as sa
from alembic import op

revision = "20260731002"
down_revision = "20260731001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project",
        sa.Column(
            "geojson_from_subprojects",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("project", "geojson_from_subprojects")
