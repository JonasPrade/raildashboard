"""infraplan kpi display settings

docs/features/feature-infraplan-import.md ("Öffentliche Seite"): how /infraplan
draws a KPI moves from frontend constants onto ``infraplan_kpi`` so it can be
changed in the admin settings — ``chart_layout``, ``total_series``,
``companion_key``/``companion_label`` and ``zoomed_axis``. Expand only: all
columns are nullable or have a server default. The rules the frontend used
so far are written onto the existing rows by key (a no-op where a KPI does
not exist yet; new installs get them from the seed).

Revision ID: 20261021001
Revises: 20261020002
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021001"
down_revision = "20261020002"
branch_labels = None
depends_on = None


SETTINGS = [
    ("etcs_strecken_km", {"total_series": "Gesamtnetz", "companion_key": "etcs_ausruestungsgrad", "companion_label": "Ausrüstungsgrad"}),
    ("elektrifizierungsgrad", {"companion_key": "elektrifizierungsgrad_prozent", "companion_label": "Anteil am Gesamtnetz"}),
    ("barrierefreie_bahnsteige", {"chart_layout": "split"}),
    ("bp_einreichung_pf_unterlagen", {"chart_layout": "grouped"}),
    ("mittelherkunft_mitteleinsatz", {"chart_layout": "flow"}),
    ("stellwerksbesetzungsquote", {"zoomed_axis": True}),
]


def upgrade() -> None:
    op.add_column("infraplan_kpi", sa.Column("chart_layout", sa.String(length=20), nullable=True))
    op.add_column("infraplan_kpi", sa.Column("total_series", sa.String(length=100), nullable=True))
    op.add_column("infraplan_kpi", sa.Column("companion_key", sa.String(length=100), nullable=True))
    op.add_column("infraplan_kpi", sa.Column("companion_label", sa.String(length=100), nullable=True))
    op.add_column(
        "infraplan_kpi",
        sa.Column("zoomed_axis", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    kpi = sa.table(
        "infraplan_kpi",
        sa.column("key", sa.String),
        sa.column("chart_layout", sa.String),
        sa.column("total_series", sa.String),
        sa.column("companion_key", sa.String),
        sa.column("companion_label", sa.String),
        sa.column("zoomed_axis", sa.Boolean),
    )
    for key, values in SETTINGS:
        op.execute(kpi.update().where(kpi.c.key == key).values(**values))


def downgrade() -> None:
    op.drop_column("infraplan_kpi", "zoomed_axis")
    op.drop_column("infraplan_kpi", "companion_label")
    op.drop_column("infraplan_kpi", "companion_key")
    op.drop_column("infraplan_kpi", "total_series")
    op.drop_column("infraplan_kpi", "chart_layout")
