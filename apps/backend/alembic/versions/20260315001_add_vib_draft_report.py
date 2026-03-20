"""add vib_draft_report table

Revision ID: 20260315001
Revises: 20260313001
Create Date: 2026-03-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '20260315001'
down_revision: Union[str, None] = '20260313001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'vib_draft_report',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.String(200), nullable=False, index=True, unique=True),
        sa.Column('year', sa.Integer(), nullable=False, index=True),
        sa.Column('raw_result_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            'created_by_user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table('vib_draft_report')
