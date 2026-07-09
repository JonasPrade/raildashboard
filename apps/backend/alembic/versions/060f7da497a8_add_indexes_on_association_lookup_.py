"""add indexes on association lookup columns

finve_to_project is filtered by finve_id alone (finves overview, admin
assignments, haushalt confirm sync) and text_to_project by text_id alone
(_get_project_id_for_text); the existing unique indexes/constraints lead
with project_id and don't cover those lookups. Postgres does not index FK
columns automatically.

Hand-written: autogenerate against the dev DB picked up unrelated drift
(PostGIS/TIGER and legacy routing tables) and was discarded.

Revision ID: 060f7da497a8
Revises: 20260707001
Create Date: 2026-07-09 09:49:29.684542

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '060f7da497a8'
down_revision: Union[str, None] = '20260707001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_finve_to_project_finve_id', 'finve_to_project', ['finve_id'], unique=False)
    op.create_index('ix_text_to_project_text_id', 'text_to_project', ['text_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_text_to_project_text_id', table_name='text_to_project')
    op.drop_index('ix_finve_to_project_finve_id', table_name='finve_to_project')
