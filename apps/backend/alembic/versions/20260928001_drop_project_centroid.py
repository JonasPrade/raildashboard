"""drop project.centroid

The column was only ever written by the one-off import from the old database
and never maintained afterwards, so it was empty or stale for every project
created or edited since. Its single reader, the initial centre of the detail
map, now fits the map to the project geometry instead (#136).

Revision ID: 20260928001
Revises: 20260910001
Create Date: 2026-09-28
"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "20260928001"
down_revision = "20261007001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The initial migration only sketched this GiST index (commented out); drop it
    # if a database carries it anyway.
    op.execute("DROP INDEX IF EXISTS idx_project_centroid")
    op.drop_column("project", "centroid")


def downgrade() -> None:
    # The values are gone; the column comes back empty.
    op.add_column(
        "project",
        sa.Column(
            "centroid",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
    )
