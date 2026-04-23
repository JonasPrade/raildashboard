"""widen vib_pfa_entry text columns to Text

Revision ID: 070f64d16220
Revises: 20260413001
Create Date: 2026-04-14 19:33:24.288804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "070f64d16220"
down_revision: Union[str, None] = "20260413001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("vib_pfa_entry", "abschnitt_label",
                    existing_type=sa.VARCHAR(length=100), type_=sa.Text(), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "oertlichkeit",
                    existing_type=sa.VARCHAR(length=200), type_=sa.Text(), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "entwurfsplanung",
                    existing_type=sa.VARCHAR(length=100), type_=sa.Text(), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "abschluss_finve",
                    existing_type=sa.VARCHAR(length=100), type_=sa.Text(), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "datum_pfb",
                    existing_type=sa.VARCHAR(length=100), type_=sa.Text(), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "baubeginn",
                    existing_type=sa.VARCHAR(length=100), type_=sa.Text(), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "inbetriebnahme",
                    existing_type=sa.VARCHAR(length=100), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("vib_pfa_entry", "inbetriebnahme",
                    existing_type=sa.Text(), type_=sa.VARCHAR(length=100), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "baubeginn",
                    existing_type=sa.Text(), type_=sa.VARCHAR(length=100), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "datum_pfb",
                    existing_type=sa.Text(), type_=sa.VARCHAR(length=100), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "abschluss_finve",
                    existing_type=sa.Text(), type_=sa.VARCHAR(length=100), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "entwurfsplanung",
                    existing_type=sa.Text(), type_=sa.VARCHAR(length=100), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "oertlichkeit",
                    existing_type=sa.Text(), type_=sa.VARCHAR(length=200), existing_nullable=True)
    op.alter_column("vib_pfa_entry", "abschnitt_label",
                    existing_type=sa.Text(), type_=sa.VARCHAR(length=100), existing_nullable=True)
