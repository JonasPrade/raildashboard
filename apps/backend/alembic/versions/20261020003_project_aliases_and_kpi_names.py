"""project aliases, KPI names for km/% pairs

docs/features/feature-infraplan-import.md → "Ausbau für den Import 2027":
adds ``project.aliases`` (JSON list of other names and ids such as "DT 38",
matched by the Infraplan import and found by the project search). Expand
only: the column is nullable, older code ignores it.

The charts that show km and % become two KPIs each; the % definitions were
created ad hoc during the 2026 import. Their display names, units and order
are set here where the rows exist (missing ones are created on first use by
``crud.infraplan.ensure_default_kpis``). Keys stay, so the stored values
keep their KPI.

Revision ID: 20261020003
Revises: 20261020002
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa

revision = "20261020003"
down_revision = "20261020002"
branch_labels = None
depends_on = None

KPI_UPDATES = (
    ("elektrifizierungsgrad", "Elektrifizierte Streckenkilometer", "km", 20),
    ("elektrifizierungsgrad_prozent", "Elektrifizierungsgrad", "%", 25),
    ("etcs_strecken_km", "ETCS-Streckenkilometer", "km", 70),
    ("etcs_ausruestungsgrad", "ETCS-Ausrüstungsgrad", "%", 75),
)


def upgrade() -> None:
    op.add_column("project", sa.Column("aliases", sa.JSON(), nullable=True))
    kpi = sa.table(
        "infraplan_kpi",
        sa.column("key", sa.String),
        sa.column("name", sa.String),
        sa.column("unit", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    for key, name, unit, sort_order in KPI_UPDATES:
        op.execute(
            kpi.update()
            .where(kpi.c.key == key)
            .values(name=name, unit=unit, sort_order=sort_order)
        )


def downgrade() -> None:
    # The KPI names stay; they are data, not schema.
    op.drop_column("project", "aliases")
