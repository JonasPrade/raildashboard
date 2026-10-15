"""add infraplan import tables

Stage 1 of docs/features/feature-infraplan-import.md: parse drafts, confirmed
years with their table entries and project links, KPI definitions and values,
plus the nullable provenance column ``progress_observation.infraplan_entry_id``.
Purely additive (expand only), so older code keeps working against the
expanded schema. Grants the new ``infraplan.import`` capability to the editor
system role. Generated with ``make migrate-create``; unrelated drift that
autogenerate reported was removed.

Revision ID: 20261015001
Revises: 20261014001
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "20261015001"
down_revision = "20261014001"
branch_labels = None
depends_on = None

_EDITOR_PERMISSIONS = ("infraplan.import",)


def upgrade() -> None:
    op.create_table('infraplan_kpi',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('unit', sa.String(length=50), nullable=True),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('category', sa.String(length=20), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_index(op.f('ix_infraplan_kpi_id'), 'infraplan_kpi', ['id'], unique=False)
    op.create_table('infraplan_parse_result',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('result_json', sa.JSON(), nullable=True),
    sa.Column('warnings_json', sa.JSON(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('pdf_path', sa.String(length=255), nullable=True),
    sa.Column('kpi_pages_json', sa.JSON(), nullable=True),
    sa.Column('task_id', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('username_snapshot', sa.String(length=100), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(), nullable=True),
    sa.Column('confirmed_by_snapshot', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_infraplan_parse_result_id'), 'infraplan_parse_result', ['id'], unique=False)
    op.create_index(op.f('ix_infraplan_parse_result_year'), 'infraplan_parse_result', ['year'], unique=False)
    op.create_table('infraplan_report',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('published_on', sa.Date(), nullable=True),
    sa.Column('parse_result_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['parse_result_id'], ['infraplan_parse_result.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_infraplan_report_id'), 'infraplan_report', ['id'], unique=False)
    op.create_index(op.f('ix_infraplan_report_year'), 'infraplan_report', ['year'], unique=True)
    op.create_table('infraplan_entry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('report_id', sa.Integer(), nullable=False),
    sa.Column('section', sa.String(length=10), nullable=False),
    sa.Column('lfd_nr', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('project_numbers', sa.JSON(), nullable=True),
    sa.Column('primary_number', sa.String(length=50), nullable=True),
    sa.Column('bezeichnung', sa.Text(), nullable=True),
    sa.Column('massnahme', sa.Text(), nullable=True),
    sa.Column('laender', sa.String(length=255), nullable=True),
    sa.Column('state_raw', sa.String(length=255), nullable=True),
    sa.Column('lph_from', sa.Integer(), nullable=True),
    sa.Column('lph_to', sa.Integer(), nullable=True),
    sa.Column('under_construction', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('baurecht', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('ibn_raw', sa.String(length=100), nullable=True),
    sa.Column('ibn_year', sa.Integer(), nullable=True),
    sa.Column('ibn_qualifier', sa.String(length=10), nullable=True),
    sa.Column('cost_mio', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('cost_kind', sa.String(length=20), nullable=True),
    sa.Column('cost_ref_raw', sa.String(length=255), nullable=True),
    sa.Column('cost_ref_entry_id', sa.Integer(), nullable=True),
    sa.Column('parl_raw', sa.String(length=255), nullable=True),
    sa.Column('parl_state', sa.String(length=20), nullable=True),
    sa.Column('footnote_refs', sa.JSON(), nullable=True),
    sa.Column('footnotes', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['cost_ref_entry_id'], ['infraplan_entry.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['infraplan_report.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('report_id', 'section', 'lfd_nr', name='uq_infraplan_entry_report_section_lfd')
    )
    op.create_index(op.f('ix_infraplan_entry_id'), 'infraplan_entry', ['id'], unique=False)
    op.create_index(op.f('ix_infraplan_entry_primary_number'), 'infraplan_entry', ['primary_number'], unique=False)
    op.create_index(op.f('ix_infraplan_entry_report_id'), 'infraplan_entry', ['report_id'], unique=False)
    op.create_table('infraplan_kpi_value',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('report_id', sa.Integer(), nullable=False),
    sa.Column('kpi_id', sa.Integer(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('value_kind', sa.String(length=10), nullable=False),
    sa.Column('series', sa.String(length=100), nullable=True),
    sa.Column('value', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('source_page', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='UNGEPRUEFT', nullable=False),
    sa.Column('entered_by_snapshot', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['kpi_id'], ['infraplan_kpi.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['report_id'], ['infraplan_report.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('report_id', 'kpi_id', 'year', 'value_kind', 'series', name='uq_infraplan_kpi_value', postgresql_nulls_not_distinct=True)
    )
    op.create_index(op.f('ix_infraplan_kpi_value_id'), 'infraplan_kpi_value', ['id'], unique=False)
    op.create_index(op.f('ix_infraplan_kpi_value_kpi_id'), 'infraplan_kpi_value', ['kpi_id'], unique=False)
    op.create_index(op.f('ix_infraplan_kpi_value_report_id'), 'infraplan_kpi_value', ['report_id'], unique=False)
    op.create_table('infraplan_entry_project',
    sa.Column('entry_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('assigned_by_snapshot', sa.String(length=100), nullable=True),
    sa.Column('assignment_source', sa.String(length=10), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['entry_id'], ['infraplan_entry.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('entry_id', 'project_id')
    )
    op.create_index('ix_infraplan_entry_project_project_id', 'infraplan_entry_project', ['project_id'], unique=False)
    op.add_column('progress_observation', sa.Column('infraplan_entry_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_progress_observation_infraplan_entry_id', 'progress_observation', 'infraplan_entry',
        ['infraplan_entry_id'], ['id'], ondelete='SET NULL',
    )

    # Grant the new capability to the editor system role (idempotent).
    editor_values = ", ".join(f"('{key}')" for key in _EDITOR_PERMISSIONS)
    op.execute(
        sa.text(
            f"""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT r.id, k.permission_key
            FROM roles r
            JOIN (VALUES {editor_values}) AS k(permission_key) ON true
            WHERE r.name = 'editor'
            ON CONFLICT (role_id, permission_key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    editor_values = ", ".join(f"'{key}'" for key in _EDITOR_PERMISSIONS)
    op.execute(
        sa.text(f"DELETE FROM role_permissions WHERE permission_key IN ({editor_values})")
    )
    op.drop_constraint('fk_progress_observation_infraplan_entry_id', 'progress_observation', type_='foreignkey')
    op.drop_column('progress_observation', 'infraplan_entry_id')
    op.drop_index('ix_infraplan_entry_project_project_id', table_name='infraplan_entry_project')
    op.drop_table('infraplan_entry_project')
    op.drop_index(op.f('ix_infraplan_kpi_value_report_id'), table_name='infraplan_kpi_value')
    op.drop_index(op.f('ix_infraplan_kpi_value_kpi_id'), table_name='infraplan_kpi_value')
    op.drop_index(op.f('ix_infraplan_kpi_value_id'), table_name='infraplan_kpi_value')
    op.drop_table('infraplan_kpi_value')
    op.drop_index(op.f('ix_infraplan_entry_report_id'), table_name='infraplan_entry')
    op.drop_index(op.f('ix_infraplan_entry_primary_number'), table_name='infraplan_entry')
    op.drop_index(op.f('ix_infraplan_entry_id'), table_name='infraplan_entry')
    op.drop_table('infraplan_entry')
    op.drop_index(op.f('ix_infraplan_report_year'), table_name='infraplan_report')
    op.drop_index(op.f('ix_infraplan_report_id'), table_name='infraplan_report')
    op.drop_table('infraplan_report')
    op.drop_index(op.f('ix_infraplan_parse_result_year'), table_name='infraplan_parse_result')
    op.drop_index(op.f('ix_infraplan_parse_result_id'), table_name='infraplan_parse_result')
    op.drop_table('infraplan_parse_result')
    op.drop_index(op.f('ix_infraplan_kpi_id'), table_name='infraplan_kpi')
    op.drop_table('infraplan_kpi')
