"""add haushalt_year to finve_to_project for SV-FinVe year tracking

Revision ID: 20260310001
Revises: 20260308001
Create Date: 2026-03-10 00:00:00.000000

The finve_to_project table is restructured so that:
- Regular FinVes use haushalt_year = NULL (permanent link, one row per project/finve pair)
- Sammelfinanzierungsvereinbarungen use haushalt_year = <year> (one row per project/finve/year)

This preserves the full history of which projects were in a SV-FinVe each year.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260310001"
down_revision: Union[str, None] = "20260308001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add surrogate primary key column
    op.add_column("finve_to_project", sa.Column("id", sa.Integer(), nullable=True))
    op.execute("CREATE SEQUENCE IF NOT EXISTS finve_to_project_id_seq")
    op.execute(
        "UPDATE finve_to_project SET id = nextval('finve_to_project_id_seq')"
    )
    op.alter_column("finve_to_project", "id", nullable=False)
    op.execute(
        "ALTER SEQUENCE finve_to_project_id_seq OWNED BY finve_to_project.id"
    )

    # 2. Add haushalt_year column (NULL = permanent / regular FinVe)
    op.add_column(
        "finve_to_project",
        sa.Column("haushalt_year", sa.Integer(), nullable=True),
    )

    # 3. Drop old composite primary key and unique constraint
    op.drop_constraint("uq_finve_to_project", "finve_to_project", type_="unique")
    op.execute("ALTER TABLE finve_to_project DROP CONSTRAINT finve_to_project_pkey")

    # 4. Set the new surrogate PK (using sequence default)
    op.execute(
        "ALTER TABLE finve_to_project ALTER COLUMN id SET DEFAULT "
        "nextval('finve_to_project_id_seq')"
    )
    op.execute("ALTER TABLE finve_to_project ADD PRIMARY KEY (id)")

    # 5. Create partial unique indexes
    op.execute(
        """
        CREATE UNIQUE INDEX uq_finve_to_project_permanent
        ON finve_to_project (project_id, finve_id)
        WHERE haushalt_year IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_finve_to_project_yearly
        ON finve_to_project (project_id, finve_id, haushalt_year)
        WHERE haushalt_year IS NOT NULL
        """
    )


def downgrade() -> None:
    # Remove partial indexes
    op.execute("DROP INDEX IF EXISTS uq_finve_to_project_yearly")
    op.execute("DROP INDEX IF EXISTS uq_finve_to_project_permanent")

    # Remove haushalt_year column (only rows with NULL year should exist after downgrade)
    op.drop_column("finve_to_project", "haushalt_year")

    # Restore old composite PK and unique constraint
    op.execute("ALTER TABLE finve_to_project DROP CONSTRAINT finve_to_project_pkey")
    op.drop_column("finve_to_project", "id")
    op.execute(
        "ALTER TABLE finve_to_project ADD PRIMARY KEY (project_id, finve_id)"
    )
    op.create_unique_constraint(
        "uq_finve_to_project", "finve_to_project", ["project_id", "finve_id"]
    )
