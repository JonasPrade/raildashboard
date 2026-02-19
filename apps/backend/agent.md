# Contributor Guidance – Backend

> The authoritative contributor guide is **`AGENT.md` at the repository root**. Read that first.

This file contains backend-specific reminders that complement the root guide.

## Architecture quick reference

| Layer | Location | Responsibility |
|---|---|---|
| Routers | `dashboard_backend/api/v1/endpoints/` | HTTP endpoints, request validation |
| Schemas | `dashboard_backend/schemas/` | Pydantic request/response models |
| CRUD | `dashboard_backend/crud/` | Database queries via SQLAlchemy |
| Models | `dashboard_backend/models/` | SQLAlchemy ORM models |
| Services | `dashboard_backend/services/` | Business logic, external client calls |

## Key rules

- Use **type hints** in all new or modified Python functions.
- Use **SQLAlchemy ORM** for all database interactions – never raw SQL, never SQLite.
- The database is **PostgreSQL with PostGIS**. Geometry columns require PostGIS.
- Group related tables in a dedicated subdirectory (e.g. `models/osmr/`, `models/eba_data/`).
- Create a **dedicated Alembic migration** for every model change.
- Run `pytest` for every Python change; extend `tests/api/` when adding or changing routes.
- New import scripts go under `scripts/` with an `argparse` CLI; document them in `docs/` and `README.md`.
