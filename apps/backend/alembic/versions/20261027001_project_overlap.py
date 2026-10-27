"""project overlap tables

docs/features/feature-map-overlapping-geometries.md → B1: ``project_map_geometry``
(bounding box, line length, geometry hash and lane per project) and
``project_overlap`` (pairs of projects sharing a track).

Expand only: two new tables, nothing on ``project`` changes. The migration
fills nothing; the backend starts the initial fill when it finds the tables
empty, and until then the map draws every project on lane 0 as before.

Revision ID: 20261027001
Revises: 20261023002
Create Date: 2026-10-27
"""

from alembic import op
import sqlalchemy as sa

revision = "20261027001"
down_revision = "20261023002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_map_geometry",
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", onupdate="CASCADE", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("min_lon", sa.Float(), nullable=False),
        sa.Column("min_lat", sa.Float(), nullable=False),
        sa.Column("max_lon", sa.Float(), nullable=False),
        sa.Column("max_lat", sa.Float(), nullable=False),
        sa.Column("line_km", sa.Float(), nullable=False),
        sa.Column("geometry_hash", sa.String(length=40), nullable=False),
        sa.Column("lane", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_project_map_geometry_bbox",
        "project_map_geometry",
        ["min_lon", "max_lon", "min_lat", "max_lat"],
    )
    op.create_table(
        "project_overlap",
        sa.Column(
            "project_a_id",
            sa.Integer(),
            sa.ForeignKey("project.id", onupdate="CASCADE", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "project_b_id",
            sa.Integer(),
            sa.ForeignKey("project.id", onupdate="CASCADE", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("shared_km", sa.Float(), nullable=False),
        sa.Column("share_a", sa.Float(), nullable=False),
        sa.Column("share_b", sa.Float(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("project_a_id < project_b_id", name="ck_project_overlap_order"),
    )
    op.create_index("ix_project_overlap_project_b_id", "project_overlap", ["project_b_id"])


def downgrade() -> None:
    op.drop_index("ix_project_overlap_project_b_id", table_name="project_overlap")
    op.drop_table("project_overlap")
    op.drop_index("ix_project_map_geometry_bbox", table_name="project_map_geometry")
    op.drop_table("project_map_geometry")
