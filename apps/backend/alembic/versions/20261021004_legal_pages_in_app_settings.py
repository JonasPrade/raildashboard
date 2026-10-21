"""legal pages in app settings

docs/features/feature-idt-design.md → "Impressum und Datenschutz (W8)": adds
``impressum_url``/``impressum_markdown`` and ``datenschutz_url``/
``datenschutz_markdown`` to the ``app_settings`` singleton. A URL sends the
footer link and the route outside, otherwise the Markdown is shown as its
own page. Expand only: all columns are nullable, older code ignores them.

Revision ID: 20261021004
Revises: 20261021003
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021004"
down_revision = "20261021003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_settings", sa.Column("impressum_url", sa.String(length=500), nullable=True))
    op.add_column("app_settings", sa.Column("impressum_markdown", sa.Text(), nullable=True))
    op.add_column("app_settings", sa.Column("datenschutz_url", sa.String(length=500), nullable=True))
    op.add_column("app_settings", sa.Column("datenschutz_markdown", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_settings", "datenschutz_markdown")
    op.drop_column("app_settings", "datenschutz_url")
    op.drop_column("app_settings", "impressum_markdown")
    op.drop_column("app_settings", "impressum_url")
