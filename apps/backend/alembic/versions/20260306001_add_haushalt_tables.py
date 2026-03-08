"""add haushalt tables (HaushaltTitel, BudgetTitelEntry, HaushaltsParseResult,
FinveChangeLog, BudgetChangeLog, UnmatchedBudgetRow)

Revision ID: 20260306001
Revises: 20260227001
Create Date: 2026-03-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260306001"
down_revision: Union[str, None] = "20260227001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1a — haushalt_titel: lookup table for Haushaltskapitel/Titel
    op.create_table(
        "haushalt_titel",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("titel_key", sa.String(50), unique=True, nullable=False),
        sa.Column("kapitel", sa.String(20), nullable=False),
        sa.Column("titel_nr", sa.String(20), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("is_nachrichtlich", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 1b — budget_titel_entry: normalized per-titel sub-entries per budget row
    op.create_table(
        "budget_titel_entry",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "budget_id",
            sa.Integer(),
            sa.ForeignKey("budgets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "titel_id",
            sa.Integer(),
            sa.ForeignKey("haushalt_titel.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("cost_estimate_last_year", sa.Integer(), nullable=True),
        sa.Column("cost_estimate_aktuell", sa.Integer(), nullable=True),
        sa.Column("verausgabt_bis", sa.Integer(), nullable=True),
        sa.Column("bewilligt", sa.Integer(), nullable=True),
        sa.Column("ausgabereste_transferred", sa.Integer(), nullable=True),
        sa.Column("veranschlagt", sa.Integer(), nullable=True),
        sa.Column("vorhalten_future", sa.Integer(), nullable=True),
        sa.UniqueConstraint("budget_id", "titel_id", name="uq_budget_titel"),
    )

    # 1c — haushalts_parse_result: persisted raw PDF parser output
    op.create_table(
        "haushalts_parse_result",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("haushalt_year", sa.Integer(), nullable=False, index=True),
        sa.Column("pdf_filename", sa.String(255), nullable=False),
        sa.Column("parsed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "parsed_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("username_snapshot", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_by_snapshot", sa.String(100), nullable=True),
    )

    # 1d — finve_change_log + finve_change_log_entry
    op.create_table(
        "finve_change_log",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "finve_id",
            sa.Integer(),
            sa.ForeignKey("finve.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("haushalt_year", sa.Integer(), nullable=False),
        sa.Column("username_snapshot", sa.String(100), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("action", sa.String(20), nullable=False),
    )

    op.create_table(
        "finve_change_log_entry",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "changelog_id",
            sa.Integer(),
            sa.ForeignKey("finve_change_log.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
    )

    # 1e — budget_change_log + budget_change_log_entry
    op.create_table(
        "budget_change_log",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "budget_id",
            sa.Integer(),
            sa.ForeignKey("budgets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("haushalt_year", sa.Integer(), nullable=False),
        sa.Column("username_snapshot", sa.String(100), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("action", sa.String(20), nullable=False),
    )

    op.create_table(
        "budget_change_log_entry",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "changelog_id",
            sa.Integer(),
            sa.ForeignKey("budget_change_log.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
    )

    # 1f — unmatched_budget_row: persistent storage for unassignable PDF rows
    op.create_table(
        "unmatched_budget_row",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("haushalt_year", sa.Integer(), nullable=False, index=True),
        sa.Column("raw_finve_number", sa.String(50), nullable=False),
        sa.Column("raw_name", sa.String(500), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "resolved_finve_id",
            sa.Integer(),
            sa.ForeignKey("finve.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by_snapshot", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("unmatched_budget_row")
    op.drop_table("budget_change_log_entry")
    op.drop_table("budget_change_log")
    op.drop_table("finve_change_log_entry")
    op.drop_table("finve_change_log")
    op.drop_table("haushalts_parse_result")
    op.drop_table("budget_titel_entry")
    op.drop_table("haushalt_titel")
