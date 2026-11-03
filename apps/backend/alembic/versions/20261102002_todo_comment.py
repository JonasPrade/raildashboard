"""Comments on tasks (Aufgaben)

docs/features/feature-tasks.md → „Kommentare“: ``todo_comment`` holds progress
notes on a task (author snapshot, created/edited timestamps). Deleting a task
deletes its comments.

Expand only: a new table. An older backend after a rollback does not read it.

Revision ID: 20261102002
Revises: 20261102001
Create Date: 2026-11-02
"""

from alembic import op
import sqlalchemy as sa

revision = "20261102002"
down_revision = "20261102001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "todo_comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "todo_id",
            sa.Integer(),
            sa.ForeignKey("todo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("username_snapshot", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("edited_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_todo_comment_id", "todo_comment", ["id"])
    op.create_index("ix_todo_comment_todo_id", "todo_comment", ["todo_id"])


def downgrade() -> None:
    op.drop_index("ix_todo_comment_todo_id", table_name="todo_comment")
    op.drop_index("ix_todo_comment_id", table_name="todo_comment")
    op.drop_table("todo_comment")
