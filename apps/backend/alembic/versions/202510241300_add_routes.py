"""add routes table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision: str = "202510241300"
down_revision: Union[str, None] = "2025012801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36)
    geom_line_type = Geography(geometry_type="LINESTRING", srid=4326) if is_postgres else sa.LargeBinary()
    geom_poly_type = Geography(geometry_type="POLYGON", srid=4326) if is_postgres else sa.LargeBinary()
    details_type = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")
    details_default = sa.text("'{}'::jsonb") if is_postgres else sa.text("'{}'")

    op.create_table(
        "routes",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column("graph_version", sa.String(), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("geom", geom_line_type, nullable=False),
        sa.Column("bbox", geom_poly_type, nullable=True),
        sa.Column("details", details_type, nullable=False, server_default=details_default),
        sa.Column("cache_key", sa.String(), nullable=False, unique=True),
    )
    op.create_index("ix_routes_project_id", "routes", ["project_id"])
    if is_postgres:
        op.create_index("ix_routes_geom_gist", "routes", [sa.text("geom")], postgresql_using="gist")


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if is_postgres:
        op.drop_index("ix_routes_geom_gist", table_name="routes")
    op.drop_index("ix_routes_project_id", table_name="routes")
    op.drop_table("routes")
