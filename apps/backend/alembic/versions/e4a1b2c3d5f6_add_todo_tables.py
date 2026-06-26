"""add todo (Aufgaben) tables

Revision ID: e4a1b2c3d5f6
Revises: c7e1a2b3d4f5
Create Date: 2026-06-26

Introduces the ``todo`` and ``todo_assignee`` tables for the to-do feature and
grants the new ``todo.create/edit/delete`` capabilities to the editor system
role (mirrors ``core.permissions`` / ``seed_system_roles``). Hand-written to
avoid the PostGIS/tiger drift that autogenerate drags in.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e4a1b2c3d5f6"
down_revision: Union[str, None] = "c7e1a2b3d4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EDITOR_TODO_PERMISSIONS = ("todo.create", "todo.edit", "todo.delete")


def upgrade() -> None:
    op.create_table(
        "todo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="MEDIUM"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_by_username", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_todo_id"), "todo", ["id"], unique=False)
    op.create_index(op.f("ix_todo_project_id"), "todo", ["project_id"], unique=False)

    op.create_table(
        "todo_assignee",
        sa.Column("todo_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["todo.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("todo_id", "user_id"),
    )

    # Grant the new capabilities to the editor system role (idempotent).
    editor_values = ", ".join(f"('{key}')" for key in _EDITOR_TODO_PERMISSIONS)
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
    editor_values = ", ".join(f"'{key}'" for key in _EDITOR_TODO_PERMISSIONS)
    op.execute(
        sa.text(
            f"DELETE FROM role_permissions WHERE permission_key IN ({editor_values})"
        )
    )
    op.drop_table("todo_assignee")
    op.drop_index(op.f("ix_todo_project_id"), table_name="todo")
    op.drop_index(op.f("ix_todo_id"), table_name="todo")
    op.drop_table("todo")
