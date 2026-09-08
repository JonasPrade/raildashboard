# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each production release is cut by tagging a commit `vX.Y.Z` (see AGENT.md → Release &
docs/production_setup.md → Deploy-Vertrag). Pushing the tag triggers the CI/CD pipeline
(`.github/workflows/deploy.yml`). Move entries from **[Unreleased]** into a dated version
section as part of the release commit, immediately before tagging.

## [Unreleased]

### Added
- The Haushalt import now reads **all five tables** of Annex VWIB Part B, not just the Bedarfsplan
  table: Lärmsanierung, ERTMS, Kleine und Mittlere Maßnahmen and the InvKG measures are imported as
  their own sections, each with its own column mapping, and shown as separate blocks in the review.
  For the 2027 report that is 58 measures that were previously discarded.
- Measures the report lists without a FinVe number now have a stable identity: the new
  `finve.finve_key` (migration `20260908002`) holds the designation the report prints
  (`t2:SV 52/2017`, `t4:F 03 E 0793`, `t5:B0094`, or a slug of the name where the report prints no
  designation), so the same measure is recognised again in the next report year. Those FinVes get
  their id from the database and are flagged `temporary_finve_number`.
- Pages that print no horizontal rules between measures (the ERTMS table, one page of Kleine und
  Mittlere Maßnahmen) have their rows rebuilt from the text lines, reproducing the same cell shape
  the ruling-line extraction gives everywhere else.
- The Haushalt import now maps the PDF's own table header onto the canonical schema once per
  document instead of assuming the 2026 column order, so a report year that renames or moves a
  column ("Vorhalten für 2027 ff." → "Vorbehalten für 2028 ff.") no longer needs parser changes.
  Detection is deterministic first, with a single LLM call over the header texts as a fallback and
  the fixed 2026 layout as a last resort — no value ever passes through a model.
- The review page shows a "Spaltenzuordnung" panel above the table: which table of Teil B was read,
  where the mapping came from, and which PDF column each target field was taken from, with an
  explicit warning when the header could not be read or a field stayed unmapped.
- `haushalts_parse_result` keeps the document text and the column mapping of each run
  (`ocr_raw_text`, `ocr_status`, `ocr_model`, `column_map_json`, `column_map_source`;
  migration `20260908001`), so a past import stays inspectable.
- The Haushalt import can now read the report through the shared OCR stage instead of pdfplumber.
  `HAUSHALT_EXTRACTION` picks the path: `pdfplumber` (default, unchanged behaviour), `compare` (both
  run on the same PDF, pdfplumber supplies the values and the row/value diff is stored with the run
  and shown in the review) or `ocr` (OCR supplies the values, pdfplumber is the fallback). Both
  paths hand the parser the same rows of cells, so the comparison isolates the text recognition.
- `scripts/compare_haushalt_extraction.py` runs that comparison on a PDF and exits 0 only when both
  paths agree on every row and every value — the condition for switching to `ocr`.
- `OcrResult` now carries the markdown of each recognised table per page (`tables`), which is what
  lets a table source read the grid instead of the prose.

### Fixed
- The Haushalt import no longer folds the other tables of Annex VWIB Part B (Lärmsanierung, ERTMS,
  Kleine und Mittlere Maßnahmen, InvKG) into the Bedarfsplan table. Their rows carry no FinVe number
  and were appended to the last Sammel-FinVe of the first table — in the 2027 report that gave
  "SV Rest 2025" 51 instead of 3 Titel entries and 78 instead of 1 Erläuterung project. The tables
  are now detected from their page caption and each is parsed on its own.
- A "–" placeholder that overhangs its column rule is no longer read as the sign of the next column.
  On the ERTMS pages that turned a Veranschlagt value of 33.186 into -33.186; the column grid is now
  shifted a point to the right, which the report's right-aligned cells make safe.
- The closing `TABELLENSUMMEN` row of a table is recognised as a totals line instead of being
  treated as an unrecoverable Sammel-FinVe row.

### Changed
- PDF text extraction moved from `tasks/vib_ocr.py` to `services/document_ocr.py` and returns a named
  `OcrResult` (text, per-page markdown, model, status, images) instead of a 4-tuple; OCR credentials
  are read from the settings inside the service rather than passed by every caller. VIB and
  Fulda-Runde use it unchanged in behaviour. `pages` is now available for later page-accurate review.
- The OCR provenance columns are shared through `models/mixins.py::OcrSourceMixin` by both
  `vib_draft_report` and `haushalts_parse_result`.
- A parse result row is now addressed by `row_key` instead of the FinVe number, because a measure
  without a printed number has none; `ProposedFinve.id` and `ProposedBudget.fin_ve` became optional
  and are resolved on confirm from the Finve row matched or created for the key.

## [v0.0.12] - 2026-07-31

### Added
- Superior projects can now choose where their map geometry comes from: a new toggle
  "Geometrie automatisch aus Unterprojekten zusammensetzen" in the geometry editor switches
  between the aggregated geometry of the subprojects (default, previous behaviour) and a
  geometry maintained on the project itself. Backed by the new project field
  `geojson_from_subprojects` (defaults to `true` for existing rows).

### Changed
- The upward geometry cascade stops at a project that maintains its own geometry, so a change
  in a subproject no longer overwrites it. Switching the toggle back on rebuilds the geometry
  from the subprojects immediately and continues the cascade upwards.
- `PATCH /api/v1/projects/{id}` rejects a direct `geojson_representation` write on a project
  that aggregates its geometry from subprojects (HTTP 400) instead of accepting a value that
  the next change in the subtree would silently discard.

### Database
- Migration `20260731002` adds `project.geojson_from_subprojects` (boolean, `NOT NULL`,
  server default `true`), the toggle deciding whether a project with subprojects aggregates
  its geometry from them or maintains its own.

## [v0.0.11] - 2026-07-31

### Added
- `GET /api/v1/projects/options` — minimal project list (id, name, number, parent) for
  pickers and dropdowns. Ten frontend views that only render a select box now use it
  instead of `GET /api/v1/projects/`, which carries every project's
  `geojson_representation`.
- `GET /api/v1/projects/{id}/subprojects` — direct children of a project. The project
  detail page used to download the full project list just to filter it client-side.
- Optional pool settings `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE_SECONDS`
  (see `docs/environment.md`).

### Changed
- `GET /api/v1/project_groups/` eager-loads groups → projects → project groups and
  excludes drafts in SQL. It previously issued one query per group plus one per project
  (`1 + groups + groups × projects`) and loaded draft rows only to drop them during
  serialisation.
- FinVe budget history (`GET /api/v1/finves/`, `GET /api/v1/projects/{id}/finves`) loads
  `budgets → titel_entries` with `selectinload` instead of nested `joinedload`, which
  produced a row per finve × budget × titel entry with all parent columns repeated.
- Database connections are checked with `pool_pre_ping` and recycled before idle timeouts.
- Fewer per-request queries: the user list eager-loads role permissions, the progress view
  eager-loads the project's groups, and the derived-observation sync eager-loads the VIB
  report of assigned PFAs.
- Project search (`ProjectSearchSelect`) caches each project's normalised name/number, so
  typing no longer re-normalises the whole list on every keystroke.
- Import review (DB-Bauportal, Fulda-Runde): once an entry has a project assigned, the confirm
  column shows an explicit „Übernehmen" button instead of the grey `offen` badge, so the
  pending action is visible. Unassigned rows keep the `offen` badge, confirmed rows the green
  `aktiv` badge (click to revoke).

### Fixed
- `POST /api/v1/projects/{id}/changelog/revert` raised `NameError` instead of reverting the
  field (an undefined `project_id` was passed to the update).

### Database
- Migration `20260731001` adds reverse-direction indexes on the association tables
  (`project_to_project_group.project_group_id`, `vib_entry_project.project_id`,
  `fulda_announcement_to_project.project_id`, `document_to_project.document_id`,
  `project_to_operation_point.operational_point_id`,
  `project_to_section_of_line.section_of_line_id`). Their composite keys all lead with
  `project_id`, so the opposite join direction was a sequential scan.

## [v0.0.10] - 2026-07-30

### Added
- Superior project can now be set from the project edit drawer (`superior_project_id`), which
  makes the edited project a subproject of the selected one. The project search behind it
  (`ProjectSearchSelect`) ignores word order, umlauts and dashes, ranks hits by relevance,
  displays the current selection even for drafts, and hides the project itself together with
  its whole subtree.
- Delete a project from the detail page (permission `project.delete`) behind a two-step
  confirmation; the first dialog states how many subprojects would be deleted along with it.

### Changed
- `POST`/`PATCH /api/v1/projects` validate `superior_project_id`: unknown projects,
  self-references and cycles (picking one's own descendant as parent) are rejected with
  HTTP 400 instead of producing a 500 or a broken tree.
- Moving a project in the tree now recomputes the aggregated geometry of both the previous
  and the new parent chain; the upward walk stops on cyclic legacy data instead of recursing
  forever.
- `DELETE /api/v1/projects/{id}` answers a foreign-key conflict with HTTP 409 instead of a
  server error.

## [v0.0.9] - 2026-07-17

### Fixed
- Re-enabled the GraphHopper routing service in production (`docker-compose.yml`),
  now pulling `raildashboard-graphhopper` from GHCR like the other services instead of
  building on the server. It had been disabled since v0.0.5-era infra work with the
  reasoning "not required by any service yet", but the route-calculation feature
  (project creation wizard → Geometrie step) depends on it and was silently broken.
  CI build matrix (`.github/workflows/deploy.yml`) now also builds/pushes the
  `graphhopper` image.

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
