"""add vib tables (VibReport, VibEntry, VibPfaEntry)

Revision ID: 20260313001
Revises: 20260311003
Create Date: 2026-03-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '20260313001'
down_revision: Union[str, None] = '20260311003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'vib_report',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('year', sa.Integer(), nullable=False, index=True, unique=True),
        sa.Column('drucksache_nr', sa.String(50), nullable=True),
        sa.Column('report_date', sa.Date(), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            'imported_by_user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )

    op.create_table(
        'vib_entry',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'vib_report_id',
            sa.Integer(),
            sa.ForeignKey('vib_report.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'project_id',
            sa.Integer(),
            sa.ForeignKey('project.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column('vib_section', sa.String(20), nullable=True),
        sa.Column('vib_lfd_nr', sa.String(20), nullable=True),
        sa.Column('vib_name_raw', sa.String(500), nullable=False),
        sa.Column('category', sa.String(20), nullable=False, server_default='laufend'),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('bauaktivitaeten', sa.Text(), nullable=True),
        sa.Column('teilinbetriebnahmen', sa.Text(), nullable=True),
        sa.Column('verkehrliche_zielsetzung', sa.Text(), nullable=True),
        sa.Column('durchgefuehrte_massnahmen', sa.Text(), nullable=True),
        sa.Column('noch_umzusetzende_massnahmen', sa.Text(), nullable=True),
        sa.Column('strecklaenge_km', sa.Float(), nullable=True),
        sa.Column('gesamtkosten_mio_eur', sa.Float(), nullable=True),
        sa.Column('entwurfsgeschwindigkeit', sa.String(50), nullable=True),
        sa.Column('ai_extracted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ai_result', sa.Text(), nullable=True),
    )

    op.create_table(
        'vib_pfa_entry',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'vib_entry_id',
            sa.Integer(),
            sa.ForeignKey('vib_entry.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('abschnitt_label', sa.String(100), nullable=True),
        sa.Column('nr_pfa', sa.String(50), nullable=True),
        sa.Column('oertlichkeit', sa.String(200), nullable=True),
        sa.Column('entwurfsplanung', sa.String(100), nullable=True),
        sa.Column('abschluss_finve', sa.String(100), nullable=True),
        sa.Column('datum_pfb', sa.String(100), nullable=True),
        sa.Column('baubeginn', sa.String(100), nullable=True),
        sa.Column('inbetriebnahme', sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('vib_pfa_entry')
    op.drop_table('vib_entry')
    op.drop_table('vib_report')
