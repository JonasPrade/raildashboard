"""replace project_status string with three boolean status columns

Revision ID: 20260401001
Revises: 20260331001
Create Date: 2026-04-01

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260401001"
down_revision: Union[str, None] = "20260331001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vib_entry", sa.Column("status_planung", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("vib_entry", sa.Column("status_bau", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("vib_entry", sa.Column("status_abgeschlossen", sa.Boolean(), nullable=False, server_default="false"))

    # Migrate existing project_status string values
    op.execute(
        "UPDATE vib_entry SET status_planung = true WHERE project_status = 'Planung'"
    )
    op.execute(
        "UPDATE vib_entry SET status_bau = true WHERE project_status = 'Bau'"
    )

    op.drop_column("vib_entry", "project_status")


def downgrade() -> None:
    op.add_column("vib_entry", sa.Column("project_status", sa.String(20), nullable=True))
    op.execute(
        "UPDATE vib_entry SET project_status = 'Planung' WHERE status_planung = true AND status_bau = false"
    )
    op.execute(
        "UPDATE vib_entry SET project_status = 'Bau' WHERE status_bau = true"
    )
    op.drop_column("vib_entry", "status_abgeschlossen")
    op.drop_column("vib_entry", "status_bau")
    op.drop_column("vib_entry", "status_planung")
