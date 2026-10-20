"""split the Elektrifizierung charts, KPI descriptions

docs/features/feature-infraplan-import.md ("Öffentliche Seite"): the share of
the network (``elektrifizierungsgrad_prozent``) is no longer drawn into the
km chart of ``elektrifizierungsgrad`` but gets a chart of its own right next
to it — the km are an annual figure, the share a cumulative stock, and one
chart for both misleads. Data only: clears the companion link (only where it
still is the seeded one, an admin's own setting stays), puts the share right
after the km KPI and adds a description to both where none is set. The
Kapazitätsauslastung gets its definition from the Infraplan 2026 the same
way; /infraplan shows descriptions as a tooltip next to the KPI name.

Revision ID: 20261021002
Revises: 20261021001
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021002"
down_revision = "20261021001"
branch_labels = None
depends_on = None

KM_KEY = "elektrifizierungsgrad"
SHARE_KEY = "elektrifizierungsgrad_prozent"
SHARE_LABEL = "Anteil am Gesamtnetz"
DESCRIPTIONS = {
    KM_KEY: "Je Jahr neu elektrifizierte Strecken-km",
    SHARE_KEY: "Anteil der elektrifizierten Strecken am Gesamtnetz, kumulierter Stand je Jahr",
    "kapazitaetsauslastung": (
        "Anteil der gefahrenen Trassenkilometer in überausgelasteten Netzabschnitten "
        "(Auslastung über 125 %, Auslastungsstufen 5 und 6 der DB InfraGO) an allen "
        "Trassenkilometern, jährlich in Prozent."
    ),
}

kpi = sa.table(
    "infraplan_kpi",
    sa.column("key", sa.String),
    sa.column("description", sa.Text),
    sa.column("sort_order", sa.Integer),
    sa.column("companion_key", sa.String),
    sa.column("companion_label", sa.String),
)


def upgrade() -> None:
    op.execute(
        kpi.update()
        .where(kpi.c.key == KM_KEY, kpi.c.companion_key == SHARE_KEY)
        .values(companion_key=None, companion_label=None)
    )
    km_order = sa.select(kpi.c.sort_order).where(kpi.c.key == KM_KEY).scalar_subquery()
    op.execute(kpi.update().where(kpi.c.key == SHARE_KEY).values(sort_order=km_order + 5))
    for key, description in DESCRIPTIONS.items():
        op.execute(kpi.update().where(kpi.c.key == key, kpi.c.description.is_(None)).values(description=description))


def downgrade() -> None:
    op.execute(
        kpi.update()
        .where(kpi.c.key == KM_KEY, kpi.c.companion_key.is_(None))
        .values(companion_key=SHARE_KEY, companion_label=SHARE_LABEL)
    )
    for key, description in DESCRIPTIONS.items():
        op.execute(kpi.update().where(kpi.c.key == key, kpi.c.description == description).values(description=None))
