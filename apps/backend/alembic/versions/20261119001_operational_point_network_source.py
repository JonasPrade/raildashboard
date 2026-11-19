"""Operational points: network and source

docs/features/feature-routing.md → "Gleisarten (S-Bahn, U-Bahn, Straßenbahn,
Schmalspur)": stops of subway, light rail and tram networks are imported from OSM
next to the RINF operational points, so every point says which network it belongs to
and where it came from:

* ``operational_point.network`` — rail | light_rail | subway | tram (default rail);
* ``operational_point.source`` — rinf | osm (default rinf).

Expand only: both columns carry a server default, so an older backend that does not
know them keeps inserting rows after a rollback.

Revision ID: 20261119001
Revises: 20261102002
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20261119001"
down_revision = "20261102002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "operational_point",
        sa.Column("network", sa.String(), nullable=False, server_default="rail"),
    )
    op.add_column(
        "operational_point",
        sa.Column("source", sa.String(), nullable=False, server_default="rinf"),
    )
    op.create_index("ix_operational_point_network", "operational_point", ["network"])


def downgrade() -> None:
    op.drop_index("ix_operational_point_network", table_name="operational_point")
    op.drop_column("operational_point", "source")
    op.drop_column("operational_point", "network")
