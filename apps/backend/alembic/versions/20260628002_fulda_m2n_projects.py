"""fulda_announcement m:n project assignment

Revision ID: 20260628002
Revises: 20260628001
Create Date: 2026-06-28

Fulda-Runde importer (#46): replace the single ``project_id`` / ``suggested_project_id``
columns with an m:n link table ``fulda_announcement_to_project`` (mirrors VIB's
``vib_entry_project``). Existing confirmed matches are migrated into the link table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260628002'
down_revision: Union[str, None] = '20260628001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fulda_announcement_to_project',
        sa.Column('fulda_announcement_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['fulda_announcement_id'], ['fulda_announcement.id'],
            name='fk_fulda_a2p_announcement_id', ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'],
            name='fk_fulda_a2p_project_id', ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('fulda_announcement_id', 'project_id'),
    )

    # Migrate existing single-project matches into the link table.
    op.execute(
        "INSERT INTO fulda_announcement_to_project (fulda_announcement_id, project_id) "
        "SELECT id, project_id FROM fulda_announcement WHERE project_id IS NOT NULL"
    )

    op.drop_constraint(
        'fk_fulda_announcement_project_id', 'fulda_announcement', type_='foreignkey'
    )
    op.drop_constraint(
        'fk_fulda_announcement_suggested_project_id', 'fulda_announcement', type_='foreignkey'
    )
    op.drop_index('ix_fulda_announcement_project_id', table_name='fulda_announcement')
    op.drop_column('fulda_announcement', 'project_id')
    op.drop_column('fulda_announcement', 'suggested_project_id')


def downgrade() -> None:
    op.add_column(
        'fulda_announcement',
        sa.Column('suggested_project_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'fulda_announcement',
        sa.Column('project_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        'ix_fulda_announcement_project_id', 'fulda_announcement', ['project_id'], unique=False
    )
    op.create_foreign_key(
        'fk_fulda_announcement_project_id', 'fulda_announcement', 'project',
        ['project_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_fulda_announcement_suggested_project_id', 'fulda_announcement', 'project',
        ['suggested_project_id'], ['id'], ondelete='SET NULL',
    )
    # Collapse the link table back to one project per announcement (lossy).
    op.execute(
        "UPDATE fulda_announcement SET project_id = ("
        "SELECT project_id FROM fulda_announcement_to_project "
        "WHERE fulda_announcement_to_project.fulda_announcement_id = fulda_announcement.id "
        "LIMIT 1)"
    )
    op.drop_table('fulda_announcement_to_project')
