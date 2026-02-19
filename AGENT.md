# Contributor Guide – Schienendashboard

This file applies to the entire repository. Read it before making any substantial change.

> **Default language:** English. Write code, comments, documentation, commit messages, and PR descriptions in English. UI strings displayed to end users are in German.

---

## Repository structure

```
apps/
├── backend/   # FastAPI + SQLAlchemy + PostGIS
└── frontend/  # React + Vite + Mantine + MapLibre
```

Changes that span both apps (e.g. a new API contract) require coordinated updates to both sides. Always verify the full roundtrip works before opening a PR.

---

## Git workflow

- **Branches:** `feature/<summary>`, `fix/<bug-id>`, `docs/<topic>`, `refactor/<area>`.
- **Strategy:** `master` stays stable and deployable. Branch directly from `master`.
- **Merges:** Squash-merge feature branches. Rebase your branch onto the latest `master` before submitting a PR.
- **Commit messages:** Follow Conventional Commits:
  - `feat(map): add project route hover effect`
  - `fix(api): correct bounding-box serialisation`
  - `docs: update OSM import instructions`
  - `chore: add Makefile`

---

## Backend guidelines (`apps/backend/`)

### Architecture

The codebase follows a strict separation of concerns. Every new feature touches all relevant layers:

| Layer | Location | Responsibility |
|---|---|---|
| Routers | `dashboard_backend/api/v1/endpoints/` | HTTP endpoints, request validation |
| Schemas | `dashboard_backend/schemas/` | Pydantic request/response models |
| CRUD | `dashboard_backend/crud/` | Database queries via SQLAlchemy |
| Models | `dashboard_backend/models/` | SQLAlchemy ORM models |
| Services | `dashboard_backend/services/` | Business logic, external client calls |

- Use **type hints** in all new or modified Python functions.
- Use **SQLAlchemy ORM** for all database interactions – never raw SQL strings, never SQLite.
- The database is **PostgreSQL with the PostGIS extension**. Geometry columns and spatial operations require PostGIS.
- Group related database tables in a dedicated subdirectory (e.g. `models/osmr/`, `models/eba_data/`) to keep domain boundaries clear.

### Database migrations

Every model change requires an Alembic migration:

```bash
alembic revision --autogenerate -m "Short description"
alembic upgrade head
```

Never modify existing migration files. Always create a new revision.

### Testing (backend)

```bash
pytest
```

- Run `pytest` for every Python change (documentation-only changes are exempt).
- For database-dependent tests, use a dedicated test database and set `ENVIRONMENT=test` so `.env.test` is loaded.
- Extend `tests/api/` immediately whenever you add or change an API route.
- Summarise which tests were run in the PR description.

### Data import scripts

- Place new import scripts under `scripts/` with an `argparse`-based CLI.
- Document new import paths in `docs/` and add a short example to `apps/backend/README.md`.

---

## Frontend guidelines (`apps/frontend/`)

### Architecture

```
src/
├── features/     # Domain-specific feature modules (map, projects, documentation …)
├── components/   # Shared UI building blocks (header, error boundary)
├── shared/       # Cross-feature utilities and generated API client
├── lib/          # Infrastructure (API client config, React Query setup, auth)
├── theme.ts      # Mantine theme configuration
└── router.tsx    # Central route definitions
```

- New functional areas go into `src/features/<name>/`.
- Shared UI components (used by two or more features) go into `src/components/`.
- Global types go into `src/types/` or `shared/`. Feature-specific types stay local.

### TypeScript

- **Avoid `any`.** Use `unknown` for temporarily untyped values; add type guards to refine them.
- Enable strict mode; do not disable TypeScript checks with `@ts-ignore` without a comment explaining why.

### UI components

- Use **Mantine** for layout and UI work. Keep theme overrides in `theme.ts`.
- Extract recurring patterns into custom components under `src/components/`.

### Routing

- Register new pages in `src/router.tsx` as children of the shared `Layout` component.
- Use `React.lazy()` + `Suspense` for routes with heavy bundles.

### State management & APIs

- Local component state: React `useState`/`useReducer`.
- Shared client state: Zustand or Redux Toolkit.
- Server state: React Query (hooks live in `src/shared/api/queries.ts`).
- Wrap raw API calls in typed wrappers; keep return values strictly typed.

### Code quality (frontend)

Before committing, run:

```bash
npm run build       # TypeScript check + production build
npm run lint        # ESLint
npm run test        # Vitest unit/integration tests
```

- Aim for **80 % statement/branch coverage** minimum.
- Keep Vite chunks **below 300 kB**; use code splitting when exceeding.
- Apply `useMemo`/`useCallback` for expensive computations.

### Accessibility

- Meet **WCAG 2.1 AA** for all UI components.
- Use semantic HTML; add ARIA attributes only when necessary.
- Validate keyboard navigation and visible focus styles.
- Test with a screen reader (NVDA/VoiceOver) before significant UI releases.

### API code generation

When the backend OpenAPI schema changes, regenerate the frontend client (backend must be running):

```bash
npm run gen:api   # regenerates src/shared/api/types.gen.ts
npm run gen:zod   # regenerates src/shared/api/client.gen.ts
```

Or from the repository root: `make gen-api`.

---

## Documentation

- Keep `README.md` (root) up to date for project-wide setup and workflow changes.
- Keep `apps/backend/README.md` up to date for backend-specific setup, routing API, and data imports.
- Keep `apps/frontend/README.md` up to date for frontend-specific setup and project structure.
- Update `apps/frontend/src/features/documentation/DocumentationPage.tsx` (the in-app docs) whenever the user-facing feature scope changes.
- Backend domain knowledge, architecture decisions, and roadmaps live in `apps/backend/docs/`.

---

## Pull requests

**PR description template:**

```markdown
## Summary
- ...

## Testing
- [ ] `pytest` (backend) / `npm run build && npm run lint && npm run test` (frontend)
- [ ] Manual smoke test
- [ ] Documentation updated (README + in-app docs if applicable)
- [ ] Screenshots/demo attached (for UI changes)
- [ ] Breaking changes documented
```

- Require at least **two approvals**.
- Address reviewer feedback before merging.
- For UI changes, attach screenshots (PNG/WebP, 1440 px width) or a short screen recording (≤ 2 min).
- Place screenshots under `docs/screenshots/<feature>/` with a date or commit hash in the filename.
