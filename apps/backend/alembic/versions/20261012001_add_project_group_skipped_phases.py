"""add project_group.skipped_phases

Planning phases a group's projects usually skip (e.g. corridor renewals without
Planfeststellung skip Vorplanung/Genehmigungsplanung), see
docs/features/feature-project-progress.md (#164). Additive with a server default,
so older code keeps working against the expanded schema. Written by hand:
autogenerate needs a PostGIS database and reports unrelated drift.

Revision ID: 20261012001
Revises: 20260928001
Create Date: 2026-10-12
"""

import sqlalchemy as sa
from alembic import op

revision = "20261012001"
down_revision = "20260928001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_group",
        sa.Column(
            "skipped_phases",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="MainPhase values (VORPLANUNG/GENEHMIGUNGSPLANUNG) its projects "
            "usually skip, e.g. corridor renewals without Planfeststellung",
        ),
    )


def downgrade() -> None:
    op.drop_column("project_group", "skipped_phases")
