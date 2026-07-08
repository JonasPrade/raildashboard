# Feature: Code Optimization (Redundancy, Dead Code, Runtime Performance)

**Goal:** Reduce code redundancy so changes become easier to implement, remove
code that is no longer needed, and speed up system runtimes. **No feature
behavior or feature scope changes** — every item below is a pure refactoring,
cleanup, or performance improvement.

**Origin:** Repo-wide audit on 2026-07-07 (five parallel analysis passes:
backend redundancy, backend performance/dead code, frontend redundancy,
frontend performance/dead code, infrastructure). Every finding was verified by
reading the code or by repo-wide grep before being listed here.

Findings are grouped into **Quick Wins (QW)**, **Medium (M)** and **Large (L)**
work packages plus **Decision (D)** items that need a user call. Issue codes
below are stable; the GitHub issues reference these anchors.

**Verification baseline for all items:** backend tests
(`cd apps/backend && .venv/bin/python -m pytest`), frontend build
(`npm run build` in `apps/frontend`), and — for parser refactors — golden
output via `scripts/dump_parse_result.py` / `scripts/dump_vib_parse_result.py`
before/after.

---

## Quick Wins

### QW-1 Frontend bundle splitting

**Problem:** The production entry chunk is 2.93 MB minified / 839 KB gzip;
lazy route chunks are only 4–23 KB because everything heavy lands in the entry:

- `src/main.tsx:7` imports `pdfjs` from `react-pdf` at app entry (plus its CSS),
  though it is only used by `features/projects/PdfPreviewModal.tsx` (~400 KB).
- `src/main.tsx:16` loads the PDF worker from the unpkg CDN at runtime —
  external dependency, breaks offline/behind firewalls.
- `src/router.tsx:9` imports `ProjectDetail` eagerly — the only one of 30
  routes not using `lazyWithRetry`. It transitively pulls in
  `@mantine/charts`/recharts (~500 KB, via `FinveSection.tsx`),
  `react-markdown`/micromark (via `VibSection.tsx`) and `terra-draw` (via
  `GeometryManagementModal → GeometryEditor`).
- `vite.config.ts` has no `build.rollupOptions.output.manualChunks`, so any
  one-line change invalidates the entire cached bundle.

**Solution:**
1. Move the `pdfjs` import + `GlobalWorkerOptions` setup + react-pdf CSS out of
   `main.tsx` into `PdfPreviewModal.tsx`; lazy-load that modal.
2. Bundle the worker locally:
   `import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url"`.
3. Convert `ProjectDetail` to a `lazyWithRetry` route like all others;
   optionally lazy-load `GeometryManagementModal` (opens on click only).
4. Add `manualChunks` for `maplibre-gl`, `@mantine/*`, `react`+`react-dom`.
   `maplibre-gl` stays in the initial load path (MapPage is the index route).

Expected: roughly 1 MB less minified entry JS (~300 KB gzip).

### QW-2 Delivery: gzip + cache headers + uvicorn workers

**Problem:** `apps/frontend/nginx.conf` serves everything uncompressed and
without cache headers — hashed immutable Vite assets are re-downloaded and API
responses (project list with GeoJSON geometries!) go over the wire
uncompressed. The backend has no `GZipMiddleware` either (`main.py`). Uvicorn
runs with the default single worker (`apps/backend/Dockerfile` CMD).

**Solution:** In nginx: `gzip on` for text/JS/CSS/JSON/GeoJSON (incl. proxied
`/api/` responses), `location /assets/` with
`Cache-Control: public, max-age=31536000, immutable`, `index.html` with
`no-cache`. Add `--workers 2` (or make it configurable) to the uvicorn CMD.
Backend `GZipMiddleware` is redundant if nginx compresses proxied responses —
verify with `curl -H 'Accept-Encoding: gzip'` and only add it if nginx does not
cover the API path. Update `docs/production_setup.md` + `CHANGELOG.md`
(deploy-relevant).

### QW-3 N+1 and payload on `GET /projects/`

**Problem:** `crud/projects/projects.py:get_projects`/`get_draft_projects`
query without eager loading; the response schema `ProjectSchema` contains
`project_groups`, a default-lazy relationship → 1+N queries per list call on
the highest-traffic public endpoint. Every row also carries
`geojson_representation` (Text; full FeatureCollections) whether needed or
not. Additionally `patch_project`/revert fetch the project twice
(`endpoints/projects.py:162` + again inside `update_project`).

**Solution:** Add `.options(selectinload(Project.project_groups))` to both
functions (2 queries total). Pass the already-loaded project into the update
path instead of re-fetching. Evaluate (measure first) a slim list schema or
`deferred()` for `geojson_representation` as a follow-up — only if the map
does not rely on this endpoint for geometry.

### QW-4 Duplicate auth dependencies on import endpoints

**Problem:** Five routers declare `dependencies=[_require_editor]` **and**
`current_user: User = Depends(require_permission("…"))` on the same endpoint
(`vib_import.py:98+105`, `haushalt_import.py:43+47`, `fulda_import.py:31+35`,
`media_import.py:30+33`, `guides.py:36+41`). `require_permission()` returns a
fresh closure per call, so FastAPI cannot cache the sub-dependency — the full
auth check incl. DB lookup runs twice per request.

**Solution:** Drop the redundant `dependencies=[...]` wherever `current_user`
is already taken via `require_permission(...)`; keep exactly one auth
dependency per endpoint. No permission semantics change (both checks enforce
the same or weaker role).

### QW-5 Frontend dead code removal + small fixes

**Problem (all verified by repo-wide grep):**

- `src/shared/api/client.gen.ts` (4,092 lines) and `zod.gen.ts` (1,955 lines)
  are imported nowhere (the app uses hand-written `client.ts`); they import
  `zod`/`@zodios/core` which are not declared in `package.json` — a build
  landmine.
- Empty files: `src/types.ts`, `src/lib/api.ts`,
  `src/components/ErrorFallback.tsx`, `src/features/stations/StationPicker.tsx`.
- Dead: `features/haushalt-import/components/TitelBreakdown.tsx`,
  `public/vite.svg`; `features/projects/ProjectGroupsPage.tsx` page component
  (route is a redirect; only the named `ProjectCard` export is used).
- Unused exports in `queries.ts`: `useLinkTrackDocument`,
  `useUnlinkTrackDocument`, `useProjectRoutes`, `getProjectRoutesQueryOptions`,
  `updateProjectProgress`, `useFuldaYears`, `useStartVibAiExtraction`; unused
  `components/tafel` exports (`KpiCard`, `MiniBoard`, `Ticker`, `FlapText`).
- `package.json`: `openapi-typescript`/`openapi-zod-client` are CLI tools in
  `dependencies`; `@types/maplibre-gl` is deprecated (maplibre v5 ships types).
- `index.html:5` references `/favicon.svg` which does not exist → 404 on every
  page load.
- `useRevertProjectField` (`queries.ts:648`) does not invalidate
  `["project", id]` → detail view can stay stale up to 5 min after a revert.

**Solution:** Delete the dead files/exports (extract `ProjectCard` into its own
file first), drop the `gen:zod` script + `openapi-zod-client`, move
`openapi-typescript` to devDependencies, remove `@types/maplibre-gl`, add a
favicon (or drop the link), add the missing invalidation. Keep `recharts`
(peer dep of `@mantine/charts`).

### QW-6 Backend dead code removal

**Problem (all verified by repo-wide grep):** `crud/users.py:count_users` and
`update_user_role` (superseded by `update_user`) have zero callers;
`core/security.py:21` `PasswordHasher` alias unused; commented-out
relationship `models/projects/project.py:123`; stale path comment
`crud/projects/projects.py:1`; `scripts/run_generation.py` +
`scripts/generate_rinf_models/` are one-time codegen whose input data
(`data/rinf_era/`) no longer exists in the repo and nothing references them.
`RouteService.create_and_store` (`services/route_service.py:28`) is only
called by its own tests (production uses the two-phase
`calculate_only`/`confirm_and_store` flow).

**Solution:** Delete the dead functions/alias/comments and the two codegen
script trees. For `create_and_store`: remove method + its two tests (it is
test-only code). Keep: `scripts/import_rinf_data/` (documented seeding tool),
user-admin scripts and dump scripts (wired into Makefile/docs),
`/tasks/debug` endpoint, VIB image endpoints (roadmap item).

### QW-7 Frontend shared helpers: formatters, permission guard, phase meta

**Problem:**
- The T€ currency formatter is defined 4× (`FinveSection.tsx:25`,
  `FinveOverviewPage.tsx:29`, `TitelBreakdown.tsx:6`, plus inline chart
  lambdas); German date/timestamp formatting is inlined at 15+ call sites with
  drifting options — some render Europe/Berlin, some don't.
- The literal "Kein Zugriff" `Container>Alert` block plus
  `const { can } = useAuth(); if (!can(...))` is copy-pasted in 13 pages.
- `PHASE_LABEL` is re-declared in `BauportalImportPage.tsx:33` (identical to
  `phaseMeta.ts:MAIN_PHASE_LABEL`); `PHASE_COLOR` exists twice with
  **different palettes** (`BauportalImportPage.tsx:41` says
  `GENEHMIGUNGSPLANUNG: "blue"`, `progress/SubprojectsTable.tsx:17` says
  `"indigo"`) — same phase renders different colors in different views;
  `PHASE_OPTIONS` is built independently 4×.

**Solution:** New `shared/format.ts` (`formatTEuro`, `formatNumber`,
`formatDate`, `formatDateTime` with Berlin TZ baked in); a
`<RequirePermission perm="…">` wrapper component; move phase color/options
into `features/projects/components/progress/phaseMeta.ts` (canonical module)
and delete local copies. Bauportal badge colors change to the canonical
palette — that is the fix, not a regression.

---

## Medium work packages

### M-1 Fulda import must not block the event loop

**Problem:** `api/v1/endpoints/fulda_import.py:32-47` (`parse_fulda`) is
`async def` and synchronously runs Mistral-OCR + LLM extraction inline
(`crud/fulda.py:parse_and_store`). Because the endpoint is async, this runs
**on the event loop**: the whole backend stops serving all requests for the
duration of OCR+LLM (minutes for large PDFs). The Haushalt importer already
does this correctly (Celery task + task polling). Related:
`media_import.py`/`bauportal_import.py` run network fetch + LLM inline in sync
endpoints — they hold a threadpool worker and DB session but at least don't
block the loop.

**Solution:** Move the Fulda parse to a Celery task mirroring
`parse_haushalt_pdf` (return `TaskLaunchResponse`, frontend polls
`GET /tasks/{id}` — the `useImportTask` pattern from M-9 fits). Interim
mitigation if needed: make the endpoint sync (`def`) so it runs in the
threadpool. For media/bauportal: set tight httpx timeouts; Celery migration
optional. Frontend flow change for Fulda (upload → poll → redirect) must keep
identical user-visible behavior aside from non-blocking progress.

### M-2 Importer + progress N+1 queries and fat fuzzy-matching queries

**Problem:**
- `crud/media.py:list_entries` calls `_project_name_map(db, …)` **per row**;
  sibling `crud/bauportal.py` already batches one map for all rows.
- `crud/fulda.py:list_entries`/`confirm_year`/`delete_year` lazy-load
  `row.projects` per row (m:n) — no `selectinload`.
- `crud/projects/progress.py:sync_derived_observations` (lines 216-243)
  queries VIB entries without eager loads, then touches `entry.report` and
  `entry.pfa_entries` per entry (2 lazy SELECTs each); confirm flows call
  `recompute_progress` per affected project → hundreds of queries per
  year-confirm.
- Fuzzy matching loads the **entire** project table as full ORM objects
  incl. `geojson_representation` (`crud/fulda.py:parse_and_store`,
  `crud/media.py:create_from_input`) though only
  `id`/`name`/`superior_project_id` are needed.

**Solution:** Batch the media name map like bauportal; add
`selectinload(FuldaAnnouncement.projects)` to the three Fulda queries; add
`joinedload(VibEntry.report), selectinload(VibEntry.pfa_entries)` in
`sync_derived_observations`; switch matcher inputs to column tuples /
`load_only` (verify matcher signatures only read id/name/superior first).
Batch-recompute (loading shared inputs once) is L-4.

### M-3 VIB entry field set: one base schema instead of eight copies

**Problem:** The ~18-field VIB content block is written out five times as
near-identical Pydantic classes (`schemas/vib.py`: `VibEntryProposed:37`,
`VibConfirmEntryInput:103`, `VibEntryForProjectSchema:201`,
`VibEntryUpdateSchema:264`, `VibEntrySchema:296` — the
`entwurfsgeschwindigkeit` validator is copy-pasted twice) and three more times
as field-by-field mappers (`endpoints/vib_import.py:484` `_entry_to_schema`,
`endpoints/projects.py:126` `get_project_vib`, `crud/vib.py:158` ORM
construction; `crud/vib.py:264` `_SCALAR_FIELDS` repeats the names again).
`VibPfaEntry` mapping is duplicated verbatim at `crud/vib.py:192` and `:310`.
In `tasks/vib.py:476-527` the PFA row construction is tripled. Adding one VIB
field currently requires ~8 edits — and the open Phase-5 parser bugs will
require exactly that.

**Solution:** Introduce `VibEntryFieldsBase(BaseModel)` (precedent:
`schemas/projects/project_fields_base.py`) that all five schemas inherit;
replace `_entry_to_schema` and the `projects.py` block with
`VibEntrySchema.model_validate(entry)` (+ 2 computed fields); build the ORM
object via `model_dump(include=…)`; extract `_pfa_from_schema()` and a
`_pfa_row()` helper in `tasks/vib.py`. Guard with
`scripts/dump_vib_parse_result.py` golden output and existing API tests.

### M-4 Shared fetch-or-404 dependencies

**Problem:** The three-line "fetch object, raise 404" block is repeated 17×
for projects alone (`endpoints/projects.py` ×10, `project_texts.py` ×3+3,
`project_progress.py` wraps it locally as `_view_or_404`), 5× for VIB drafts
(`vib_import.py`), with a mix of German/English 404 messages — 66
`HTTPException(status_code=404` total across endpoints.

**Solution:** FastAPI path dependencies in a new `api/deps.py`:
`get_project_or_404`, `get_draft_or_404`, `get_text_or_404`. Endpoints take
`project: Project = Depends(get_project_or_404)`. Removes ~50 lines,
standardizes 404 wording, creates one hook point for future visibility rules.
No response shape changes.

### M-5 One shared LLM client instead of three copies

**Problem:** `_call_llm` is copy-pasted verbatim (17 lines) in
`tasks/vib_ai_extraction.py:75`, `tasks/fulda_extraction.py:152`,
`tasks/media_extraction.py:101`; fulda/media also share the same "empty
result → bail if unconfigured → format prompt → try/except log+return empty"
scaffold. Rate-limit/error labeling (`_summarise_error`,
`vib_ai_extraction.py:98`) exists in only one of the three.

**Solution:** New `services/llm.py` with `call_llm_json(system_prompt,
prompt) -> dict` (+ optional best-effort wrapper and shared error
summarizing). The three task modules import it; behavior (model, temperature
0, json_object format) unchanged. Timeout/retry policy becomes single-site.

### M-6 Importer review CRUD: shared helpers (fulda/media/bauportal)

**Problem:** Three review CRUDs are structural copies:
`_project_name_map` verbatim in `crud/media.py:80` and `crud/bauportal.py:31`;
`update_entry` skeleton (fetch → validate project ids → `_EDITABLE_FIELDS`
setattr loop → commit → `recompute_progress` old∪new → `_entry_dict`) in all
three; `delete_entry` and `confirm_*` loops likewise; project-existence
validation differs only in exception type (`ValueError` vs
`ProjectNotFoundError`) → endpoints map errors inconsistently. A fourth
importer would start as a fourth copy.

**Solution:** New `crud/_importer_common.py`: `project_name_map(db, ids)`,
`ensure_projects_exist(db, ids)` (one exception type),
`apply_editable_fields(row, payload, fields)`, `recompute_for(db, *ids)`.
Keep feature-specific row shapes; only the repeated pieces move. Align the
"confirmed requires project" rule only if behavior is already identical —
otherwise leave per-importer rules untouched (no behavior change).

### M-7 queries.ts mutation boilerplate

**Problem:** `shared/api/queries.ts` (2,090 lines): 37 identical
`method/headers/body: JSON.stringify` blocks, 81 `invalidateQueries` calls
mostly following "mutate → invalidate 1-4 fixed keys", a ~20-line
optimistic-update block copy-pasted between `useUpdateBauportalEntry:1443` and
`useUpdateFuldaEntry:1664`, and query keys as scattered string literals
(`["fulda-entries"]` etc. 6-9× each — a typo silently breaks invalidation).

**Solution (incremental layers):** 1) `jsonBody(payload)` helper (or `json:`
option on `api()`); 2) `useInvalidatingMutation(mutationFn, keys)` factory for
the ~50 standard mutations; 3) `makeOptimisticListUpdate<T>` for the
bauportal/fulda pair; 4) central `queryKeys` object. Pure mechanics, no
cache-semantics changes.

### M-8 FinVe card/charts/TitelTable shared components

**Problem:** ~250 lines duplicated between
`features/projects/components/FinveSection.tsx` and
`features/finves/FinveOverviewPage.tsx` (the latter even says
`// same logic as FinveSection.tsx`): `fmt`/`fmtNum`, `SERIE_COLORS`,
`buildPieData`/`buildLineData`, `ChartLegend`, `TitelTable` incl. 8-column
head, and the whole Collapse>Tabs>charts block. The Titel column set appears
in 2 more hand-built copies (`haushalt-import/components/ReviewTable.tsx:352`,
`TitelBreakdown.tsx:29` — the latter is deleted by QW-5).

**Solution:** Extract `features/finves/shared/`: chart builders, `ChartLegend`,
`TitelTable`, and a `FinveBudgetDetails` component consuming
`BudgetSummary[]`. Both cards keep their distinct headers. Stretch: let
`TitelTable` take a variant that covers ReviewTable.

### M-9 Import-review UI building blocks + upload/poll flow

**Problem:** Bauportal/Media/Fulda review rows triplicate: the `patch` helper
(verbatim incl. the `Parameters<…>["data"]` trick), the confirm badge +
"Wird gespeichert" loader cluster, the "Projekt fehlt?" draft-anchor wiring
(5 sites incl. ReviewTable), and the "Nur offene" filter scaffold.
`projectOptions` exists in 5 label variants — that part is Issue #66
(ProjectMultiSelect). Separately, VIB and Haushalt import pages duplicate the
~65-line upload → Celery-poll → progress → redirect state machine
(`VibImportPage.tsx:35-93`, `HaushaltsImportPage.tsx:31-68`).

**Solution:** `features/import-review/shared/` with `usePatchWithToast`,
`<ConfirmBadge>`, `<MissingProjectAnchor>`, `<UnconfirmedFilterBar>`; plus a
`useImportTask({start, onSuccessNavigate})` hook + `<TaskProgressIndicator>`.
Coordinate the options-select part with #66 instead of duplicating it. Each
extraction independently shippable.

### M-10 Missing association-table indexes

**Problem:** `finve_to_project.finve_id` is filtered alone in
`crud/finves.py` (×2), `crud/admin_assignments.py` and the Haushalt confirm
sync, but the only indexes are partial uniques leading with `project_id`;
`text_to_project.text_id` likewise (`project_texts.py:_get_project_id_for_text`).
Postgres does not auto-index FK columns. Tables are small today — this is
future-proofing at near-zero cost.

**Solution:** `Index('ix_finve_to_project_finve_id', 'finve_id')` and
`Index('ix_text_to_project_text_id', 'text_id')` on the models + one Alembic
migration via `make migrate-create`.

### M-11 Map: stop re-parsing GeoJSON on every keystroke

**Problem:** `MapPage.tsx:127-136` builds a new `filteredMapProjects` array on
each keystroke (the 200 ms debounce only applies to the URL, not the filter);
`MapView.tsx:175-188` memos are keyed on array identity, so every keystroke
re-`JSON.parse`s every project's `geojson_representation` and re-uploads both
map sources via `setData`.

**Solution:** Build features once per project (cache keyed on the
`geojson_representation` string or project id) and filter the prebuilt
features by id set; optionally debounce the map filter. Identical rendering
result.

---

## Large work packages

### L-1 Unify Haushalt upsert + change-log machinery

**Problem:** `crud/haushalt_import.py:upsert_finve` (141-209) and
`upsert_budget` (234-317) are the same ~70-line function twice (query by key →
create-with-changelog or diff-with-changelog). Four parallel change-log
implementations share identical diff-to-entries logic
(`crud/changelog.py:34/97`, `haushalt_import.py:181/289`) over four
structurally identical Entry models. A `json.dumps` serialization quirk would
need four patches today; roadmap "Change Tracking Schritt 3–6" needs one
extension point.

**Solution:** Generic `diff_to_entries(entry_cls, obj, update_data,
tracked_fields)` in `crud/changelog.py` used by all four sites; generic
`_upsert_tracked(db, model_cls, log_cls, entry_cls, proposed, key_filter,
tracked_fields, exclude, user, haushalt_year)` so the two public upserts
become thin wrappers. Keep the four tables (separate FKs are a schema
choice). Guard with snapshot tests of produced changelog entries — audit data
must be byte-identical.

### L-2 Replace hand-written frontend types with generated ones

**Problem:** ~450 lines in `queries.ts` re-type what `types.gen.ts` already
contains (`ProjectUpdatePayload` ↔ `ProjectUpdate`, VIB/Haushalt/changelog/
FinVe schemas — full table in the audit). Hand-written pairs also duplicate
each other (`TitelEntry` ≡ `TitelEntryProposed`; `VibPfaEntryProposed` ≡
`VibPfaEntrySchema` minus `id`), forcing manual mappers like the 25-field
`toProposed()` in `VibEntryEditDrawer.tsx:18-50`.

**Solution:** `export type X = components["schemas"]["XSchema"]` aliases
(pattern already in use for `Project`, `Todo`); derive narrowed payloads with
`Pick`/`Omit`. **First** run `make gen-api` against the current backend
(bauportal/media/fulda schemas are missing from the checked-in
`types.gen.ts`; mind the dev-server-port gotcha). Nullability differences the
compiler surfaces are latent mismatches to fix, not to paper over.

### L-3 Data-driven project property lists

**Problem:** The ~50-field project property list is hand-maintained in 4
places (`ProjectEdit.tsx`: FormValues type, `createInitialValues`,
`createUpdatePayload`; `queries.ts:ProjectUpdatePayload`) while
`ProjectEditFields.tsx:39-119` already holds the authoritative data-driven
`PROPERTY_SECTIONS`. The project docs codify this as a 5-site checklist — a
symptom, not a rule to keep.

**Solution:** Export `BOOL_KEYS`/`NUM_KEYS` derived from `PROPERTY_SECTIONS`;
build initial values and update payload generically; type the payload from
the generated `ProjectUpdate` (L-2). The ~8 scalar/text fields with
trim/null semantics stay explicit and get tests. New property = one
`PROPERTY_SECTIONS` entry + backend schema.

### L-4 Batch the progress aggregation for superior projects

**Problem:** `crud/projects/progress.py:_build_aggregation_node` (526-561)
runs per-node child queries + `get_or_create_progress` recursively;
`get_progress_view` on a superior project with ~10 subprojects can execute
100+ queries cold, since each stale leaf triggers the full
`sync_derived_observations` (~10+ queries each, see M-2).

**Solution:** Load the whole subtree in one query (recursive CTE or iterative
`IN`), bulk-fetch `ProjectProgress` rows, create missing rows in one flush,
resync stale leaves in one pass over shared inputs. Semantics (aggregation
rules, staleness window) unchanged — needs the existing progress test suite
green plus targeted aggregation tests.

### L-5 Haushalt parser: extract the three repeated blocks

**Problem:** `tasks/haushalt.py` (824 lines) repeats: the 7-column
`TitelEntryProposed` numeric mapping ×3 (`:249`, `:302`, `:400`); the
15-kwarg `ProposedFinve`+`ProposedBudget` construction ×2 (orphaned-SV
recovery `:564` vs main row `:649`); the SV-suggestion recompute ×2 (`:528` vs
`:623`). This is exactly where each yearly PDF format change lands.

**Solution:** Extract `_titel_numeric_fields(cells, line_idx)`,
`_build_proposed(...)`, `_refresh_sv_suggestions(...)`. Golden-output guard:
run `scripts/dump_parse_result.py` on a reference PDF before/after — output
must be byte-identical.

---

## Decision items (user call needed)

### D-1 Legacy routing endpoints + old-DB artifacts

**Findings (verified):** POST `/api/v1/route/` (`endpoints/route.py:11`, old
section-of-line routing) is referenced only by the generated client — the live
flow is `/routes/calculate` (GraphHopper). PUT
`/projects/{id}/routes/{route_id}` (`project_routes.py:100`) has no frontend
caller **and no test**; removing it would also remove
`RouteService.confirm_and_replace` + `crud/routes.update_route`. GET
`/routes/{route_id}` has tests but no frontend caller.
`scripts/import_old_db/` is a completed one-time migration; it is the only
writer of `Project.old_id`/`superior_project_old_id`, which are exposed
read-only in `ProjectSchema` but referenced nowhere in the hand-written
frontend.

**Options:** (a) remove endpoints + chain + archive scripts + drop the two
columns (keeps CSV snapshot as the only old-DB mapping); (b) remove only the
schema exposure and keep DB columns for traceability; (c) keep everything
until "RINF-Daten evaluieren" (roadmap) is decided. Public API surface —
user decision required before removal.

### D-2 Auth cost: PBKDF2 per Basic request

**Finding:** Every HTTP-Basic-authenticated request recomputes PBKDF2 with
390k iterations (`core/security.py`) — deliberately expensive, ~100-300 ms
CPU per request; the session-cookie path avoids it. `require_permission`
additionally lazy-loads role/permissions per request.

**Options:** ensure the frontend always uses the session path (audit);
eager-load `User.role.permissions` via `joinedload` (safe, do regardless);
for Basic API clients: short-TTL in-process credential cache or restricting
Basic to `/auth/session` login only. Security-sensitive — do **not** weaken
stored-password hashing; user should choose the Basic-auth policy.

---

## Explicitly kept (checked, not dead)

VIB image endpoints (`vib_import.py:390,422` — roadmap: review gallery),
POST `/tasks/debug` (Celery smoke test), `scripts/import_rinf_data/`
(documented seeding tool for live `/operational-points/`), all dump and
user-admin scripts (Makefile-wired), all schema classes (111 checked — every
"unreferenced" one is a nested field of a used schema), `crud/haushalt_import`,
`crud/projects/texts`, `crud/todos`, `services/exceptions` (all fully alive).
