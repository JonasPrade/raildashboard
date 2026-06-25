"""add project_id to vib_pfa_entry

Revision ID: 91c0ee036d2e
Revises: fd26d250fcf9
Create Date: 2026-06-19

Links each VIB Planfeststellungsabschnitt (PFA) row to a leaf subproject so the
per-section planning status lands on the subproject instead of being flattened
onto the parent. Nullable + ON DELETE SET NULL: dropping a project only unlinks
the PFA, it does not delete the VIB record.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '91c0ee036d2e'
down_revision: Union[str, None] = 'fd26d250fcf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('vib_pfa_entry', sa.Column('project_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_vib_pfa_entry_project_id'), 'vib_pfa_entry', ['project_id'], unique=False
    )
    op.create_foreign_key(
        'fk_vib_pfa_entry_project_id',
        'vib_pfa_entry',
        'project',
        ['project_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_vib_pfa_entry_project_id', 'vib_pfa_entry', type_='foreignkey')
    op.drop_index(op.f('ix_vib_pfa_entry_project_id'), table_name='vib_pfa_entry')
    op.drop_column('vib_pfa_entry', 'project_id')
