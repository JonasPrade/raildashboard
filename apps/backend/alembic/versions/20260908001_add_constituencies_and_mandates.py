"""add constituencies, mandates and project links

Revision ID: 20260908001
Revises: 20260731002
Create Date: 2026-09-08

Autogenerate also reported pre-existing drift between the models and the
migration history (unique constraints on association tables, ``routes.details``
JSONB vs JSON, ``ix_users_id``, two nullable flags on ``project_group``). None of
that belongs to this feature, so it is deliberately left out of this revision.
"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260908001"
down_revision: Union[str, None] = "20260731002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliament_period",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("parliament_label", sa.String(length=200), nullable=True),
        sa.Column("parliament_external_id", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_parliament_period_external_id"),
        "parliament_period",
        ["external_id"],
        unique=True,
    )

    op.create_table(
        "politician",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("first_name", sa.String(length=150), nullable=True),
        sa.Column("last_name", sa.String(length=150), nullable=True),
        sa.Column("party_label", sa.String(length=150), nullable=True),
        sa.Column("abgeordnetenwatch_url", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_politician_external_id"), "politician", ["external_id"], unique=True)
    op.create_index(op.f("ix_politician_last_name"), "politician", ["last_name"], unique=False)

    op.create_table(
        "constituency",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parliament_period_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("election_year", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.Integer(), nullable=True),
        sa.Column("geometry_source", sa.String(length=300), nullable=True),
        sa.Column(
            "geom",
            # The spatial index is created explicitly below so the migration
            # states it rather than relying on a GeoAlchemy2 side effect.
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["parliament_period_id"], ["parliament_period.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parliament_period_id", "number", name="uq_constituency_period_number"
        ),
    )
    op.create_index(
        op.f("ix_constituency_external_id"), "constituency", ["external_id"], unique=False
    )
    op.create_index("ix_constituency_number", "constituency", ["number"], unique=False)
    op.create_index(
        op.f("ix_constituency_parliament_period_id"),
        "constituency",
        ["parliament_period_id"],
        unique=False,
    )
    # Carries the ``&&`` prefilter of the project intersection: without it every
    # recompute would scan all 299 outlines.
    op.create_index(
        "idx_constituency_geom",
        "constituency",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "committee",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("parliament_period_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["parliament_period_id"], ["parliament_period.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_committee_external_id"), "committee", ["external_id"], unique=True)
    op.create_index(op.f("ix_committee_key"), "committee", ["key"], unique=False)
    op.create_index(
        op.f("ix_committee_parliament_period_id"),
        "committee",
        ["parliament_period_id"],
        unique=False,
    )

    op.create_table(
        "mandate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("politician_id", sa.Integer(), nullable=False),
        sa.Column("parliament_period_id", sa.Integer(), nullable=False),
        sa.Column("constituency_id", sa.Integer(), nullable=True),
        sa.Column("mandate_type", sa.String(length=30), nullable=True),
        sa.Column("is_direct_mandate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("fraction_label", sa.String(length=200), nullable=True),
        sa.Column("info", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["constituency_id"], ["constituency.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["parliament_period_id"], ["parliament_period.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["politician_id"], ["politician.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mandate_constituency_id"), "mandate", ["constituency_id"], unique=False)
    op.create_index(op.f("ix_mandate_external_id"), "mandate", ["external_id"], unique=True)
    op.create_index(op.f("ix_mandate_fraction_label"), "mandate", ["fraction_label"], unique=False)
    op.create_index(
        op.f("ix_mandate_parliament_period_id"), "mandate", ["parliament_period_id"], unique=False
    )
    op.create_index(
        "ix_mandate_period_constituency",
        "mandate",
        ["parliament_period_id", "constituency_id"],
        unique=False,
    )
    op.create_index(op.f("ix_mandate_politician_id"), "mandate", ["politician_id"], unique=False)

    op.create_table(
        "committee_membership",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mandate_id", sa.Integer(), nullable=False),
        sa.Column("committee_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("role_label", sa.String(length=50), nullable=True),
        sa.Column("role_rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["committee_id"], ["committee.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mandate_id"], ["mandate.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mandate_id", "committee_id", name="uq_committee_membership"),
    )
    op.create_index(
        op.f("ix_committee_membership_committee_id"),
        "committee_membership",
        ["committee_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_committee_membership_mandate_id"),
        "committee_membership",
        ["mandate_id"],
        unique=False,
    )

    op.create_table(
        "parliament_import_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("parliament_period_id", sa.Integer(), nullable=True),
        sa.Column("stats", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("triggered_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parliament_period_id"], ["parliament_period.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_parliament_import_run_kind"), "parliament_import_run", ["kind"], unique=False
    )

    op.create_table(
        "project_to_constituency",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("constituency_id", sa.Integer(), nullable=False),
        sa.Column("length_km", sa.Float(), nullable=False),
        sa.Column("share", sa.Float(), nullable=False),
        sa.Column("overlap_kind", sa.String(length=10), nullable=False),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["constituency_id"], ["constituency.id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project.id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("project_id", "constituency_id"),
    )
    op.create_index(
        "ix_project_to_constituency_constituency_id",
        "project_to_constituency",
        ["constituency_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_to_constituency_constituency_id", table_name="project_to_constituency"
    )
    op.drop_table("project_to_constituency")
    op.drop_index(op.f("ix_parliament_import_run_kind"), table_name="parliament_import_run")
    op.drop_table("parliament_import_run")
    op.drop_index(op.f("ix_committee_membership_mandate_id"), table_name="committee_membership")
    op.drop_index(op.f("ix_committee_membership_committee_id"), table_name="committee_membership")
    op.drop_table("committee_membership")
    op.drop_index(op.f("ix_mandate_politician_id"), table_name="mandate")
    op.drop_index("ix_mandate_period_constituency", table_name="mandate")
    op.drop_index(op.f("ix_mandate_parliament_period_id"), table_name="mandate")
    op.drop_index(op.f("ix_mandate_fraction_label"), table_name="mandate")
    op.drop_index(op.f("ix_mandate_external_id"), table_name="mandate")
    op.drop_index(op.f("ix_mandate_constituency_id"), table_name="mandate")
    op.drop_table("mandate")
    op.drop_index(op.f("ix_committee_parliament_period_id"), table_name="committee")
    op.drop_index(op.f("ix_committee_key"), table_name="committee")
    op.drop_index(op.f("ix_committee_external_id"), table_name="committee")
    op.drop_table("committee")
    op.drop_index("idx_constituency_geom", table_name="constituency", postgresql_using="gist")
    op.drop_index(op.f("ix_constituency_parliament_period_id"), table_name="constituency")
    op.drop_index("ix_constituency_number", table_name="constituency")
    op.drop_index(op.f("ix_constituency_external_id"), table_name="constituency")
    op.drop_table("constituency")
    op.drop_index(op.f("ix_politician_last_name"), table_name="politician")
    op.drop_index(op.f("ix_politician_external_id"), table_name="politician")
    op.drop_table("politician")
    op.drop_index(op.f("ix_parliament_period_external_id"), table_name="parliament_period")
    op.drop_table("parliament_period")
