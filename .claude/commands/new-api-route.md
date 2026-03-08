---
description: Scaffold a new backend API route — walks through endpoint → schema → CRUD → make gen-api
allowed-tools: Read, Edit, Write, Glob, Grep, Bash(make gen-api:*)
argument-hint: <resource-name> [e.g. "project-note" or "budget-comment"]
---

## Context

- Existing endpoints: !`ls apps/backend/dashboard_backend/api/v1/endpoints/`
- Existing schemas: !`ls apps/backend/dashboard_backend/schemas/`
- Existing CRUD modules: !`ls apps/backend/dashboard_backend/crud/`
- API router registration: !`cat apps/backend/dashboard_backend/api/v1/api.py`

## Your task

Resource name from user: $ARGUMENTS

Walk through the following checklist interactively. After each step confirm with the user before proceeding to the next.

---

### Step 1 — Define the resource

If `$ARGUMENTS` is empty, ask the user:
1. What is the resource name? (e.g. `project-note`)
2. What HTTP methods are needed? (`GET list`, `GET detail`, `POST`, `PATCH`, `DELETE`)
3. Who can access it? (`public` | `viewer` | `editor` | `admin`)
4. Does it relate to an existing model? (show existing models from `apps/backend/dashboard_backend/models/`)

---

### Step 2 — Pydantic schema

Create `apps/backend/dashboard_backend/schemas/<resource>.py` with:
- `<Resource>Base` — shared fields
- `<Resource>Create` — fields required on creation
- `<Resource>Update` — all fields optional (for PATCH)
- `<Resource>Response` — full response including `id`, `created_at`

Follow the patterns in `apps/backend/dashboard_backend/schemas/projects/project_schema.py`.

---

### Step 3 — CRUD module

Create `apps/backend/dashboard_backend/crud/<resource>.py` with functions:
- `get_<resource>(db, id)` — single item or 404
- `get_<resources>(db, ...)` — list with optional filters
- `create_<resource>(db, data, user)` — insert + optional ChangeLog
- `update_<resource>(db, id, data, user)` — patch + optional ChangeLog
- `delete_<resource>(db, id)` — hard delete

---

### Step 4 — Endpoint file

Create `apps/backend/dashboard_backend/api/v1/endpoints/<resource>.py`.

Use `APIRouter` with prefix `/<resource>s` and appropriate tags.
Import auth dependencies: `require_editor`, `require_admin`, `get_current_user` from `dashboard_backend.core.security` as needed.

---

### Step 5 — Register router

Add the new router to `apps/backend/dashboard_backend/api/v1/api.py`:
```python
from dashboard_backend.api.v1.endpoints.<resource> import router as <resource>_router
api_router.include_router(<resource>_router, prefix="/<resource>s", tags=["<Resource>"])
```

---

### Step 6 — Regenerate frontend client

Remind the user to run:
```
make gen-api
```

Report the newly added paths visible in the regenerated `apps/frontend/src/shared/api/client.gen.ts`.
