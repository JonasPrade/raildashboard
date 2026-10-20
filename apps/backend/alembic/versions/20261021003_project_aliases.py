"""project aliases

docs/features/feature-infraplan-import.md → "Ausbau für den Import 2027":
adds ``project.aliases`` (JSON list of other names and ids such as "DT 38",
matched by the Infraplan import and found by the project search). Expand
only: the column is nullable, older code ignores it.

Revision ID: 20261021003
Revises: 20261021002
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021003"
down_revision = "20261021002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project", sa.Column("aliases", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "aliases")
