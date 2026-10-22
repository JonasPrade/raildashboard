"""todo tags and todo history

docs/features/feature-tasks.md → "Tags" and "Verlauf": adds ``todo_tag`` and
``todo_tag_link`` (m:n) plus the per-task change log ``todo_change_log`` /
``todo_change_log_entry``. Seeds the tag ``@LLM`` and moves the ``@LLM``
marker out of task titles (and a leading marker line out of descriptions) into
that tag (logged as a ``MIGRATION`` change). Also seeds ``@Jonas`` for the
part of a task that Jonas does first; ``@LLM`` tasks whose description has a
"Für Jonas:" part get it too.

Expand only: new tables, older code ignores them. The only touched existing
data is the marker; downgrade puts it back in front of the title before
dropping the tables.

Revision ID: 20261022003
Revises: 20261022002
Create Date: 2026-10-22
"""

import re
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "20261022003"
down_revision = "20261022002"
branch_labels = None
depends_on = None


LLM_TAG = "@LLM"
LLM_TAG_DESCRIPTION = (
    "Die Aufgabe ist ganz oder teilweise vom LLM über MCP zu erledigen."
)
JONAS_TAG = "@Jonas"
JONAS_TAG_DESCRIPTION = (
    "Ein Teil der Aufgabe liegt bei Jonas und kommt zuerst. Mit „@LLM“ zusammen: "
    "Das LLM beginnt erst, wenn „@Jonas“ entfernt ist."
)

# "@LLM" as its own token, with an optional trailing ":"/"-"/"–" and the
# surrounding spaces; also "[@LLM]" / "(@LLM)".
_MARKER = re.compile(r"\s*[\[(]?@LLM\b[\])]?\s*[:\-–]?\s*", re.IGNORECASE)


def strip_llm_marker(title: str) -> str:
    """Remove the ``@LLM`` marker from a title; keep the title if nothing else is left."""

    stripped = _MARKER.sub(" ", title).strip(" :-–")
    stripped = " ".join(stripped.split())
    return stripped or title


# A description that opens with "@LLM" on its own line.
_LEADING_LINE = re.compile(r"\A\s*@LLM[ \t]*(\r?\n)+", re.IGNORECASE)


def strip_llm_line(description: str | None) -> str | None:
    """Remove a leading ``@LLM`` line from a description (``None`` if nothing is left)."""

    if description is None:
        return None
    stripped = _LEADING_LINE.sub("", description)
    if stripped == description:
        return description
    return stripped.strip() or None


def upgrade() -> None:
    op.create_table(
        "todo_tag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_todo_tag_id"), "todo_tag", ["id"])

    op.create_table(
        "todo_tag_link",
        sa.Column("todo_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["todo.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["todo_tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("todo_id", "tag_id"),
    )
    op.create_index(op.f("ix_todo_tag_link_tag_id"), "todo_tag_link", ["tag_id"])

    op.create_table(
        "todo_change_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("todo_id", sa.Integer(), nullable=True),
        sa.Column("todo_title_snapshot", sa.String(length=300), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username_snapshot", sa.String(length=50), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["todo.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_todo_change_log_id"), "todo_change_log", ["id"])
    op.create_index(op.f("ix_todo_change_log_todo_id"), "todo_change_log", ["todo_id"])

    op.create_table(
        "todo_change_log_entry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("changelog_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["changelog_id"], ["todo_change_log.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_todo_change_log_entry_id"), "todo_change_log_entry", ["id"])
    op.create_index(
        op.f("ix_todo_change_log_entry_changelog_id"), "todo_change_log_entry", ["changelog_id"]
    )

    bind = op.get_bind()
    now = datetime.utcnow()
    insert_tag = sa.text(
        "INSERT INTO todo_tag (name, description, created_at) "
        "VALUES (:name, :description, :now) RETURNING id"
    )
    tag_id = bind.execute(
        insert_tag, {"name": LLM_TAG, "description": LLM_TAG_DESCRIPTION, "now": now}
    ).scalar_one()
    jonas_tag_id = bind.execute(
        insert_tag, {"name": JONAS_TAG, "description": JONAS_TAG_DESCRIPTION, "now": now}
    ).scalar_one()

    rows = bind.execute(
        sa.text(
            "SELECT id, title, description FROM todo "
            "WHERE title ILIKE '%@llm%' OR description ILIKE '@llm%'"
        )
    ).fetchall()
    for todo_id, title, description in rows:
        new_title = strip_llm_marker(title)
        new_description = strip_llm_line(description)
        tag_ids = [tag_id]
        tag_names = LLM_TAG
        if "für jonas" in (description or "").lower():
            tag_ids.append(jonas_tag_id)
            tag_names = f"{JONAS_TAG}, {LLM_TAG}"
        for linked in tag_ids:
            bind.execute(
                sa.text("INSERT INTO todo_tag_link (todo_id, tag_id) VALUES (:todo_id, :tag_id)"),
                {"todo_id": todo_id, "tag_id": linked},
            )
        bind.execute(
            sa.text("UPDATE todo SET title = :title, description = :description WHERE id = :id"),
            {"title": new_title, "description": new_description, "id": todo_id},
        )
        log_id = bind.execute(
            sa.text(
                "INSERT INTO todo_change_log (todo_id, todo_title_snapshot, timestamp, action) "
                "VALUES (:todo_id, :title, :now, 'MIGRATION') RETURNING id"
            ),
            {"todo_id": todo_id, "title": new_title, "now": now},
        ).scalar_one()
        entries = [("tags", None, tag_names)]
        if new_title != title:
            entries.append(("title", title, new_title))
        if new_description != description:
            entries.append(("description", description, new_description))
        for field, old, new in entries:
            bind.execute(
                sa.text(
                    "INSERT INTO todo_change_log_entry "
                    "(changelog_id, field_name, old_value, new_value) "
                    "VALUES (:log_id, :field, :old, :new)"
                ),
                {"log_id": log_id, "field": field, "old": old, "new": new},
            )


def downgrade() -> None:
    # Put the marker back so the older code still shows which tasks are for the LLM.
    op.execute(
        """
        UPDATE todo SET title = LEFT('@LLM ' || todo.title, 300)
        FROM todo_tag_link l JOIN todo_tag t ON t.id = l.tag_id
        WHERE l.todo_id = todo.id AND t.name = '@LLM' AND todo.title NOT ILIKE '%@llm%'
        """
    )
    op.drop_index(op.f("ix_todo_change_log_entry_changelog_id"), table_name="todo_change_log_entry")
    op.drop_index(op.f("ix_todo_change_log_entry_id"), table_name="todo_change_log_entry")
    op.drop_table("todo_change_log_entry")
    op.drop_index(op.f("ix_todo_change_log_todo_id"), table_name="todo_change_log")
    op.drop_index(op.f("ix_todo_change_log_id"), table_name="todo_change_log")
    op.drop_table("todo_change_log")
    op.drop_index(op.f("ix_todo_tag_link_tag_id"), table_name="todo_tag_link")
    op.drop_table("todo_tag_link")
    op.drop_index(op.f("ix_todo_tag_id"), table_name="todo_tag")
    op.drop_table("todo_tag")
