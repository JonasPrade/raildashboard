"""fix routes.project_id type: UUID → Integer FK

Revision ID: 20260413001
Revises: 20260408001
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260413001"
down_revision: Union[str, None] = "20260408001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Drop existing index on project_id
    op.drop_index("ix_routes_project_id", table_name="routes")

    if is_postgres:
        # Drop old UUID column and add Integer FK column
        op.drop_column("routes", "project_id")
        op.add_column(
            "routes",
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("project.id", ondelete="CASCADE"),
                nullable=False,
            ),
        )
    else:
        # SQLite: drop UUID string column, add Integer column
        op.drop_column("routes", "project_id")
        op.add_column(
            "routes",
            sa.Column("project_id", sa.Integer(), nullable=False),
        )

    op.create_index("ix_routes_project_id", "routes", ["project_id"])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_index("ix_routes_project_id", table_name="routes")
    op.drop_column("routes", "project_id")

    uuid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36)
    op.add_column("routes", sa.Column("project_id", uuid_type, nullable=False))
    op.create_index("ix_routes_project_id", "routes", ["project_id"])
