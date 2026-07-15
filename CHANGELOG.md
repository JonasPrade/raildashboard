# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each production release is cut by tagging a commit `vX.Y.Z` (see AGENT.md → Release &
docs/production_setup.md → Deploy-Vertrag). Pushing the tag triggers the CI/CD pipeline
(`.github/workflows/deploy.yml`). Move entries from **[Unreleased]** into a dated version
section as part of the release commit, immediately before tagging.

## [Unreleased]

## [v0.0.8] - 2026-07-15

### Fixed
- Production (`dashboard.schienengruen.de`) was completely broken (blank page,
  `Uncaught TypeError: can't access property "useLayoutEffect" of undefined`)
  because the `manualChunks` vendor-splitting introduced in v0.0.7 put Mantine
  and React/react-dom/scheduler into two separate output chunks
  (`mantine` / `react-vendor`) that imported from each other, creating a
  circular dependency between the two chunk files. Fixed by merging both into
  a single `vendor-react` chunk in `apps/frontend/vite.config.ts` — Mantine is
  a peer-dependent UI layer used almost everywhere in the app, so there is no
  meaningful cache-granularity loss from shipping it together with React.

## [v0.0.7] - 2026-07-09

Efficiency and cleanup release: the repo-wide optimization audit
(issues #68–#92, see `docs/features/feature-code-optimization.md`).

### Changed
- Delivery performance: the frontend nginx now gzips text responses (including
  proxied `/api/` JSON/GeoJSON) and serves hashed `/assets/` with
  `Cache-Control: immutable` (`index.html`: `no-cache`); the backend container
  runs uvicorn with `--workers 2` so synchronous import/extraction requests no
  longer serialize all other traffic.
- Fulda-Runde import: OCR + LLM extraction now runs as a Celery background
  task (like the Haushalt/VIB importers) instead of inline in the request —
  the upload returns immediately and the page polls for completion. Previously
  a large PDF blocked the entire backend event loop for minutes.
- Backend performance: `GET /projects/` eager-loads project groups
  (815 → 3 queries measured), the superior-project progress aggregation loads
  its subtree/progress rows/derived-observation sources batched (cold view on
  a project with many PFA subprojects previously cost 100+ queries), importer
  lookups are batched, and HTTP-Basic requests verify against a short-lived
  per-process credential cache instead of re-running PBKDF2 every time
  (stored hashes stay at 390k iterations); user lookups load role +
  permissions in a single query. New indexes on
  `finve_to_project.finve_id` / `text_to_project.text_id`
  (migration `060f7da497a8`).
- Frontend performance: heavy libraries (maplibre, pdfjs, charts) are
  code-split out of the entry chunk and heavy pages lazy-load; the map builds
  GeoJSON features once per project and caches them, so typing in the map
  search no longer re-parses every project geometry.
- Internal consolidation (no behavior change): shared fetch-or-404 API
  dependencies, one shared LLM client, shared importer-review CRUD helpers,
  unified Haushalt upserts + changelog diffing (audit output pinned
  byte-identical by snapshot tests), extracted Haushalt parser blocks,
  generated OpenAPI types replace ~600 lines of hand-written frontend types,
  queries.ts mutation factories + central query keys, data-driven project
  property lists (a new property is one entry + the backend schema field),
  shared FinVe chart/table components and shared import-review UI building
  blocks incl. a common upload→poll state machine.

### Removed
- Legacy routing API surface (#91, option b): `POST /api/v1/route/` (old
  section-of-line routing, superseded by `/routes/calculate`),
  `PUT /projects/{id}/routes/{route_id}` and `GET /routes/{route_id}` — none
  had a frontend caller — together with their dead chain
  (`RouteService.confirm_and_replace`, `crud/routes.update_route`,
  `crud/routes.get_route_by_id`). The read-only `old_id` /
  `superior_project_old_id` fields are no longer exposed in `ProjectSchema`;
  the DB columns stay for traceability to the migrated legacy database.
- Dead code: the unused generated API clients (`client.gen.ts`, `zod.gen.ts`,
  ~6k lines), orphaned tafel/board components, the RINF model-codegen scripts
  and other unreferenced backend helpers.

### Fixed
- Favicon 404: the app now ships and references `favicon.svg`.
- Alembic autogenerate no longer proposes DROPs for PostGIS/TIGER/topology
  tables when run against the dev database.

## [v0.0.6] - 2026-07-07

### Added
- "Anleitungen" guides hub (`/admin/anleitungen`) with step-by-step guides for
  the database-maintenance workflows (Projektfortschritt foundations, Haushalt,
  Fulda-Runde, Bauportal) plus four new guide pages: VIB report import,
  media/press extraction, project creation wizard, and geometry editor — each
  with illustrative non-interactive example views ("Beispielansicht").
- In-app guide editing: guide texts are markdown sections that users with the
  new `guides.edit` capability (group "Inhalte"; admins implicitly) can override
  per section. Overrides live in the new `guide_section_override` table
  (migration `20260707001`) behind `GET/PUT/DELETE
  /api/v1/guides/{slug}/overrides[/{section_key}]` and can be reset to the
  bundled default at any time.

## [v0.0.5] - 2026-07-07

### Added
- Tag-based CI/CD pipeline (`.github/workflows/deploy.yml`): pushing a `v*` tag runs the
  quality gates (backend `pytest`, frontend `tsc` + `eslint`), builds the `backend`, `frontend`, and
  `db` images, pushes them to GHCR double-tagged `:vX.Y.Z` + `:latest`, and deploys via SSH.
- `scripts/deploy.sh` rewritten as a server-side deploy: pre-migration DB backup (aborts the
  deploy if it fails), `docker compose pull`, `up -d`, health-wait, and automatic rollback to
  the previous immutable image tag on failure.
- `docker-compose.override.yml` for local development builds, keeping the production
  `docker-compose.yml` build-free (pull-only).
- This `CHANGELOG.md`.

### Changed
- Production `docker-compose.yml` now pulls immutable images from GHCR
  (`ghcr.io/jonasprade/raildashboard-<svc>:${IMAGE_TAG}`) instead of building from a GitHub
  URL context on the server — build and run are now separate worlds.
- Renamed the release pin `APP_VERSION` → `IMAGE_TAG` in `.env.prod.example` and the compose
  file.
- `apps/backend/requirements.txt` is now pinned to exact `==` versions for reproducible builds.
- Backend runtime image upgraded to `python:3.13-slim` to match the tested interpreter.

### Fixed
- Frontend eslint errors so `eslint` can be a blocking CI gate: hoisted access-guard early
  returns below all hooks in `HaushaltsImportPage` and `VibImportPage` (react-hooks/rules-of-hooks),
  dropped an unused `_files` parameter in `ProjectTextsSection`, and replaced a ternary-as-statement
  with `if/else` in `VibStructurePreviewPage`.
- Backend test suite is now hermetic: `tests/conftest.py` provides a dummy `SESSION_SECRET_KEY`
  so `pytest` no longer depends on a developer's local `.env` (the required Settings field made
  the CI quality gate fail on a clean checkout).
