"""add reverse-direction indexes on association tables

Follow-up to 060f7da497a8, which covered finve_to_project/text_to_project.
The remaining m:n tables have a composite primary key or unique constraint
leading with ``project_id``, so the *other* direction of every join was a
sequential scan (Postgres does not index FK columns automatically):

* ``project_to_project_group.project_group_id`` — group → projects, the map
  page's main lookup.
* ``vib_entry_project.project_id`` — derived-observation sync and forecast.
* ``fulda_announcement_to_project.project_id`` — derived-observation sync.
* ``document_to_project.document_id``,
  ``project_to_operation_point.operational_point_id``,
  ``project_to_section_of_line.section_of_line_id`` — reverse navigation.

Hand-written for the same reason as 060f7da497a8: autogenerate against the dev
DB picks up unrelated PostGIS/TIGER drift.

Revision ID: 20260731001
Revises: 060f7da497a8
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731001"
down_revision: Union[str, None] = "060f7da497a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index name, table, column)
_INDEXES = [
    ("ix_project_to_project_group_group_id", "project_to_project_group", "project_group_id"),
    ("ix_vib_entry_project_project_id", "vib_entry_project", "project_id"),
    ("ix_fulda_announcement_to_project_project_id", "fulda_announcement_to_project", "project_id"),
    ("ix_document_to_project_document_id", "document_to_project", "document_id"),
    ("ix_project_to_operation_point_op_id", "project_to_operation_point", "operational_point_id"),
    ("ix_project_to_section_of_line_sol_id", "project_to_section_of_line", "section_of_line_id"),
]


def upgrade() -> None:
    for name, table, column in _INDEXES:
        op.create_index(name, table, [column], unique=False)


def downgrade() -> None:
    for name, table, _ in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
