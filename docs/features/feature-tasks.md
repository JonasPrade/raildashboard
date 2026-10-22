# Feature: Aufgaben / To-Dos

## Goal

Give logged-in users a lightweight way to remember and coordinate work on
projects ("rework PFA 3", "check financing of project X") and to jot down quick
standalone notes. Tasks are shown in a central dashboard and on the project
detail page, can carry a status, priority and due date, and can be assigned to
one or more users.

> **Naming note:** the URL/code namespace `tasks` is already taken by the Celery
> job-status endpoints (`GET /api/v1/tasks/{task_id}`). To avoid a collision the
> feature is named **`todo`** on the code level (table `todo`/`todo_assignee`,
> route prefix `/todos`, capability keys `todo.*`). All **user-facing strings
> stay German "Aufgaben"**.

## Scope

- A task has: title (required), optional free-text description, status, priority,
  optional due date, an optional link to a project, zero or more assignees and
  zero or more tags.
- **Project link is optional**: a task either belongs to exactly one project or
  is a free standalone note (`project_id = NULL`).
- **Assignment is m:n**: a task can be assigned to several users.
- **Status**: `OPEN` / `IN_PROGRESS` / `DONE`.
- **Priority**: `LOW` / `MEDIUM` / `HIGH`.
- **Visibility**: tasks are visible to **logged-in users only** (no public GET);
  every logged-in user sees all tasks (team coordination).
- **Editing rights** are capability-gated:
  - `todo.create` — create tasks
  - `todo.edit` — edit any field incl. status and assignees
  - `todo.delete` — delete tasks
  - viewing requires only a valid session (`require_auth`), no capability.
- Completing a task (status → `DONE`) stamps `completed_at`; moving it back
  clears the stamp. Completed tasks stay visible (no hard delete on completion).

## Tags

- **Tags are free labels, m:n** (`todo_tag`, `todo_tag_link`). They are written
  as names: an unknown name creates the tag, matching is case-insensitive (the
  first spelling stays). Names are trimmed, at most 50 characters.
- **`@LLM`** is seeded with the description „Die Aufgabe ist ganz oder teilweise
  vom LLM über MCP zu erledigen.“ The LLM finds its work with
  `list_todos(tag="@LLM")`. Before tags existed the marker stood in the title;
  migration `20261022001` moved it into the tag and removed it from the title
  (downgrade puts `@LLM ` back in front).
- Tags have no management UI yet (rename/delete/description); unused tags stay
  in the list with count 0.
- **Open:** many tasks have one part for Jonas and one for the LLM. Whether a
  second tag as precondition is enough or sub-tasks fit better is not decided
  yet (#173); until then the split is written in the description.

## Verlauf (history)

Every create, update and delete of a task is logged in its **own** history —
`todo_change_log` (event: who, when, action `CREATE`/`PATCH`/`DELETE`/`MIGRATION`,
title snapshot) with one `todo_change_log_entry` per changed field (old/new as
text; assignees and tags as a sorted, comma-separated list of names). The
project `change_log` is not used: it requires a project, which standalone tasks
lack. `todo_id` is `SET NULL` on delete, so the history survives the task. An
update that changes nothing writes no row. The edit drawer shows the history
under the form.

## Desired behaviour

### Central page `/tasks` ("Aufgaben")
- Nav link "Aufgaben" shown only when logged in.
- Three columns / groups: Offen, In Arbeit, Erledigt.
- Filters: text search (title + description), tag, assignee, project, "nur meine Aufgaben".
- Quick-add input ("kurz notieren") that creates an `OPEN`, `MEDIUM` task with
  just a title.
- Each card shows title, priority badge, tags, due date (overdue highlighted in red),
  linked project (as a link), and assignee initials.
- Cards open an edit drawer (full form) for users with `todo.edit`.

### Project detail section ("Aufgaben")
- A compact section listing the tasks of that project (`project_id == id`).
- Visible to logged-in users only (like the version history section).
- "+ Aufgabe" button pre-fills the project in the create drawer.

## Data model

### `todo`
| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `title` | varchar(300) | not null |
| `description` | text | nullable |
| `status` | varchar(20) | not null, default `OPEN` |
| `priority` | varchar(10) | not null, default `MEDIUM` |
| `due_date` | date | nullable |
| `project_id` | int FK→project.id | nullable, `ON DELETE SET NULL`, indexed |
| `created_by_id` | int FK→users.id | nullable, `ON DELETE SET NULL` |
| `created_by_username` | varchar(50) | nullable snapshot (survives user deletion) |
| `created_at` | datetime | default utcnow |
| `updated_at` | datetime | default utcnow, onupdate utcnow |
| `completed_at` | datetime | nullable; set when status→DONE |

### `todo_tag` / `todo_tag_link` (m:n)
| column | type | notes |
|---|---|---|
| `todo_tag.id` | int PK | |
| `todo_tag.name` | varchar(50) | unique |
| `todo_tag.description` | text | nullable |
| `todo_tag.created_at` | datetime | |
| `todo_tag_link.todo_id` | int FK→todo.id PK | `ON DELETE CASCADE` |
| `todo_tag_link.tag_id` | int FK→todo_tag.id PK | `ON DELETE CASCADE`, indexed |

### `todo_change_log` / `todo_change_log_entry`
See „Verlauf“ above; mirrors `text_change_log` / `text_change_log_entry`.

### `todo_assignee` (m:n)
| column | type | notes |
|---|---|---|
| `todo_id` | int FK→todo.id PK | `ON DELETE CASCADE` |
| `user_id` | int FK→users.id PK | `ON DELETE CASCADE` |

## API (prefix `/api/v1/todos`)
- `GET /` — list, query filters `status`, `priority`, `assignee_id`,
  `project_id`, `created_by_id`, `include_done` (default true), `tag` (name,
  case-insensitive), `q` (text search in title and description). Auth required.
- `GET /tags` — all tags with `todo_count`. Auth required.
- `GET /{id}` — single task. Auth required.
- `GET /{id}/history` — change history, newest first. Auth required.
- `POST /` — create. Requires `todo.create`.
- `PATCH /{id}` — partial update incl. `assignee_ids` and `tags` (each replaces
  the full set), with `clear_due_date`
  and `clear_project` sentinels for nullable fields. Requires `todo.edit`.
- `DELETE /{id}` — delete. Requires `todo.delete`.
- Helper: `GET /api/v1/users/options` — minimal `{id, username}` list for the
  assignee picker, gated by `require_auth` (any logged-in user; the full
  `GET /users/` needs `user.manage`).

## MCP

`create_todo` / `update_todo` take `tags` (names; `update_todo` replaces the
set, `[]` removes all). `list_todos` filters by `tag`, searches with `search`
and pages with `limit`/`offset` (`total` counts all matches). `list_todo_tags`
lists every tag with description and count.

## Acceptance criteria
- [ ] A logged-in editor can create a task with only a title via quick-add.
- [ ] A task can be linked to a project or left standalone.
- [ ] A task can be assigned to multiple users; assignees render on the card.
- [ ] Status can be moved Offen → In Arbeit → Erledigt; `completed_at` is set on
      Erledigt and cleared when moved back.
- [ ] Priority (Niedrig/Mittel/Hoch) and an optional due date can be set; an
      overdue, non-done task is visually highlighted.
- [ ] A viewer (logged in, no `todo.*`) sees tasks read-only; an anonymous user
      gets 401 on the tasks API and no nav link.
- [ ] The project detail page shows that project's tasks for logged-in users and
      lets eligible users add one pre-linked to the project.
- [ ] Deleting a project sets its tasks' `project_id` to NULL (tasks survive).
- [ ] Tags can be set, removed and used as a filter; „@LLM“ exists with its
      description; former „@LLM“ titles carry the tag without the prefix.
- [ ] Tag changes (and every other change) show up in the task's history.

## Technical notes
- Enums live in `models/todos/todo_enums.py` (`TodoStatus`, `TodoPriority`) for
  defaults/validation; schemas use `Literal[...]` for clean TS codegen (mirrors
  the progress feature).
- Migration is **hand-written** (`make migrate-create` autogenerate drags in
  pre-existing PostGIS/tiger drift — see project memory).
- New tables must be added to `tests/api/conftest.py::TABLES` in FK order
  (`Todo` then `TodoAssignee`, `TodoTag`, `TodoTagLink`, `TodoChangeLog`,
  `TodoChangeLogEntry`); the `project` table is intentionally absent there,
  so API tests exercise standalone (`project_id=None`) tasks.
- Editors hold `todo.create/edit/delete` (seeded into the editor system role).
