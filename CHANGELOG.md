# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

A version tag `vX.Y.Z` names a state; it no longer deploys anything. Production is
updated by pressing *Actions → deploy → Run workflow* for a commit SHA (DEPLOY.md). Move
entries from **[Unreleased]** into a dated version section when cutting a version tag.

## [Unreleased]

### Added
- **MCP `check_geometry`: finding `overlaps` (#276).** Lists the projects on the same track (shared km, share of each, largest first, at most five) from `project_overlap`; a pair covering ≥ 90 % of both lines is marked `possible_duplicate` with a pointer to `merge_projects`. Own parent and subprojects are left out. Skill `gvfg-nacharbeit` uses it as evidence for duplicates.
- **Map overlaps: pairs and lanes (#274, `docs/features/feature-map-overlapping-geometries.md` → B1).** Projects whose lines run within 25 m of each other over at least 500 m (or half of the shorter line, at least 100 m) are stored as pairs in `project_overlap`; `project_map_geometry` holds each drawn project's bounding box, line length, geometry hash and a stable lane. Both are refreshed wherever the constituency links are (geometry save, parent cascade, merge, archive, draft/finalise) via `refresh_derived_geometry`. `GET /project_groups/{id}/geometries` gains `lanes` (stored lane and partner ids) and runs every simplified line part west to east, so parallel lanes offset to the same side. Full rebuild: `POST /api/v1/admin/overlap-recompute` (`project.edit`). Migration `20261027001` (two new tables, expand only). **No manual step after the deploy:** the backend queues the initial fill itself when `project_map_geometry` is empty (`START_BACKGROUND_JOBS`, default `true`); until it has run the map looks as before.
- **Archive: „Ersetzt durch“ (#261, `docs/features/feature-project-archive.md` → „Ersetzt durch“).** Archiving takes an optional successor (`replaced_by_project_id`; dialog with project search, MCP `archive_project`). The archived project's banner says „Ersetzt durch <Projekt>“ with a link, the successor shows „Ersetzt …“ (`GET /api/v1/projects/{id}/replacement`, also in MCP `get_project`). Previous-year suggestions of the VIB, Infraplan and GVFG imports that point to an archived project go to its successor with a hint; MCP assignment tools warn when an archived project is assigned. Restoring clears the successor; merging re-points links to the merged project. PAUSIERT/ABGEBROCHEN now carry a reason and a „seit“ date (edit drawer, banner). Expand-only migration `20261023002`.
- **Edit FinVe ↔ project assignments (feature-finve-zuordnung.md).** Projects of a FinVe can now be added and removed, also for FinVes already assigned: MCP tool `update_finve_projects`, „Zuordnung bearbeiten“ in the FinVe section of the project page (own permanent links only; inherited and Sammel-FinVe year links stay) and „Projekte bearbeiten“ on the FinVe overview (`PATCH /api/v1/finves/{id}/projects`, permission `finve.edit`). Every change — also through the open-assignments page and the new-project wizard — is logged per project as „FinVe-Zuordnung“ (revertable, revert needs `finve.edit`) and recomputes the planning state. The Haushalt confirm now applies only the reviewer's changes to permanent links, so a link removed by hand after the parse is not restored. Replaces the MCP tool `unlink_finve` (decision 2026-10-23: one logged write path, `finve.edit`, Sammel-FinVe year links stay). No migration.
- **Archive replaced or superseded projects (#264).** A project gets its own flag „Archiviert“ with a mandatory reason (`is_archived`, `archived_reason`, `archived_at`; not part of the lifecycle). An archived project keeps its history and stays reachable by URL with a banner, but counts nowhere: it is gone from the list, map, groups, pickers, subproject lists, timeline, parliament lists, MCP lists, import matching candidates and the drafts list, and it no longer feeds its parent's geometry, planning-state span or sums over subprojects (new principle in `docs/architecture.md`). Archiving is refused while FinVe or GVFG links or non-archived subprojects hang on the project or its lifecycle is ABGEBROCHEN — the message names the links; VIB, PFA, Infraplan, Fulda, Bauportal and media links stay (reported as `kept_links`). Archiving and restoring recompute the parent's geometry and planning state and are written to the changelog (`ARCHIVE`/`UNARCHIVE`). REST `POST /api/v1/projects/{id}/archive`, `/unarchive`, `GET /api/v1/projects/archived`; MCP `archive_project`, `unarchive_project`; admin page „Archiv“ (`/admin/archive`); all with permission `project.delete`. Skills `vib-import`, `gvfg-nacharbeit`, `infraplan-import` updated. Expand-only migration `20261023001`. **After deploying:** archive the eight replaced Puttgarden subprojects (checklist in #264).
- **Recompute the planning state of all projects.** The lazy resync only re-derives a project when it is read, so a new derivation rule (such as the GVFG source) reached list views, filters and `list_data_gaps` project by project. `recompute_all_progress` resyncs the derived observations, the cached phase and the cached dates of every project in batches of 100. Triggered by the button „Alle Projekte neu berechnen“ on the admin page „Planungsstand · Konflikte“ (permission `progress.edit`, `POST /api/v1/admin/progress-recompute`, Celery task with progress) or by `scripts/recompute_progress.py` (`make docker-recompute-progress`). No migration. **After deploying press the button once** (or run the script) so the GVFG-derived planning states show up in the lists.
- **VIB: PFA sections → subprojects (feature-vib-import.md → Phase 8).** The subproject suggestion per PFA row now searches the whole subtree below the Vorhaben's projects (not only direct children), uses the previous year's confirmed row first, then the section number („7.1“ ↔ „Abschnitt 7“, „PF 15-16“, „PFA 1+2“ in name or project number), then place names without the Vorhaben's own place names (threshold 0.5, clear lead required); each suggestion carries a reason and a strong/weak flag. New MCP tools (permission `vib.import`): `apply_vib_pfa_suggestions` takes over strong suggestions, `assign_vib_pfas` assigns many rows at once, `create_vib_pfa_subprojects` creates draft subprojects without geometry for missing sections on request and warns when the parent was a leaf. Skill `vib-import` step 5 and check mode updated. No migration.
- **Date qualification of planning-state dates (#243–#248).** Observations carry `date_precision` (EXACT, MONTH, YEAR, NOT_BEFORE, ASSUMED) and an optional `date_label`; the stored date is only the sort value and is never shown without its precision („2028“, „nach 2031“, „ca. 07/2028 (Annahme)“). The forecast passes the precision on; project groups get `assumed_build_months` (HLK: 6), so a missing commissioning becomes Baubeginn + that period as an assumption. A commissioning known only by its year (Infraplan, GVFG, VIB) is the Fahrplanwechsel, shown as 12/YYYY. The timeline draws year-only bars with soft edges, lower bounds as an open area with an arrow, assumptions with a dashed outline and a legend; the list shows Bau/IB and filters by year range and „Termin offen“ (a lower bound never matches a period). MCP: `add_progress_observation` takes `date_precision`, new `update_progress_observation`, `list_projects` returns and filters the dates. Expand-only migration `20261022004`; **after deploying run `make docker-refresh-progress-dates` once** to fill the cached list dates.
- **Planungsstand-Konflikte im Admin-Bereich.** New page `/admin/planungsstand-konflikte` (card „Planungsstand-Konflikte“ with a count, permission `progress.edit`, `GET /api/v1/admin/progress-conflicts`) lists every leaf project where a newer report asserts a lower phase than older information, marked „zurückgehalten“ or „übernommen“. The project page shows the same conflict as a hint to editors; a phase override resolves it.
- **Tags for tasks (#173).** Tasks carry any number of tags (`todo_tag`, `todo_tag_link`), set in the edit drawer and filterable on `/tasks`, which also gets a text search over title and description. The tag `@LLM` marks a task the LLM is to do (fully or in part) through MCP; migration `20261022003` moves the „@LLM“ marker out of existing titles into that tag (downgrade puts it back). Every task change is now logged in its own history (`todo_change_log`), shown in the drawer. MCP: `create_todo`/`update_todo` take `tags`, `list_todos` filters by `tag`, searches with `search` and pages with `offset`, new tools `list_todo_tags` and `update_todo_tag`. „Tags verwalten“ on `/tasks` renames, describes and deletes tags (`PATCH`/`DELETE /api/v1/todos/tags/{id}`), logged on every affected task. A second tag `@Jonas` marks a part Jonas does first; the migration sets it on `@LLM` tasks with a „Für Jonas:“ part.
- **GVFG-Bundesprogramm as a planning-state source.** The newest GVFG edition of a Vorhaben now yields derived observations (source `GVFG`, trust 0.75, dated on the edition's Stand): Inbetriebnahme tats. before the Stand year or Lph 9 → In Betrieb, Lph ≥ 5 or a Baubeginn up to the Stand year → Bau, Lph 3–4 → Genehmigungsplanung, Lph 1–2 → Vorplanung, plus the expected commissioning (tats., else gepl.) in the forecast and timeline. A more recent Infraplan row of the same key still wins (decision 22). Confirming an edition and assigning Vorhaben recompute the projects at once. The IBN plausibility check reads the same year. Expand-only migration `20261022001` (`progress_observation.gvfg_entry_id`).

### Fixed
- **Overview map showed the old geometry after an edit.** Saving a geometry (or switching its source, reverting it from the version history, or changing the parent project) only refreshed the project lists; the map's per-group geometries stayed cached for up to five minutes. These mutations now also refresh the group geometries and the parent project, whose geometry the backend rebuilds from its subprojects.

- **VIB-PFA prognoses no longer count as reached milestones (#262).** The per-section planning state read every parseable date as a fact, so an Inbetriebnahme „vsl. 2027“ put a section on In Betrieb (Teilprojekt 2972 Gaschwitz–Crimmitschau/Werdau, the Karlsruhe–Basel sections 2205–2207, 2862, 2863) and a PFB „vsl. 2025“ closed the PF track. Now a hedged date („vsl.“, „vsl“, „voraussichtlich“, „geplant“, „ca.“, „ab/nach/bis/frühestens …“) or a date after the report's year-end is an expected milestone (`is_expected`, timeline and sources only); „erfolgt“ counts as reached. The sections of one VIB entry assigned to the same leaf decide together: the leaf is In Betrieb only when no section is still open, otherwise it takes the highest phase reached among the open ones (finished stretches next to stretches under construction → Bau). The PF track is closed only by a PFB actually issued. The „abgeschlossen“ hint of the phase stepper now also skips „vsl“ without a full stop. No migration. **After deploying press „Alle Projekte neu berechnen“ once** (admin page „Planungsstand · Konflikte“, or `make docker-recompute-progress`) so the stored derived observations are rebuilt; until then only projects that are opened resync.

### Changed
- **Prognose as a row of the phase stepper.** The planning-state card no longer lists the forecast as a separate timeline; dated next steps appear in a „Prognose“ row under the stepper (below the Parl./PFB gates), one cell per phase with month/year and source. Steps without a date are left out, and the row disappears when none is dated. Remaining time and the GVFG commissioning doubt stay below the stepper.
- **Routing no longer draws its waypoints as points.** Saving a calculated route stores only the line; start, via and end stations become points only when the new switch „Start, Ziel und Zwischenhalte als Punkte übernehmen“ in the geometry editor is on. The MCP tool `route_project_geometry` now defaults to `add_stations: false`.
- **New section order on the project page.** Project details and map first, then the cost block, Planungsstand, sub-projects, Infraplan, GVFG, FinVe, texts, BVWP, VIB, parent project, and at the end Wahlkreise und Abgeordnete, tasks and version history; the register follows the same order. For GVFG projects the cost block shows „Bundesförderung (GVFG)“ (aid of the newest edition per key) as a third figure next to the FinVe, or in its place instead of „–“, and appears even without an Infraplan figure, then led by the GVFG total cost.
- **Cost block at the top of the project page.** The Infraplan forecast / „Vom Bund zugesichert“ band now sits directly under the project title (first entry in the register). Infraplan footnotes moved from a superscript on the figure to a „?“ tooltip next to the label. For parent projects „Vom Bund zugesichert“ sums the FinVes of all sub-projects (each FinVe once) via the new `include_subprojects` parameter of `GET /api/v1/projects/{id}/finves`; each FinVe then carries `from_subprojects` and the carrying `subprojects`. The FinVe section of a parent project lists the sub-projects' FinVes too (own ones first, each with „Aus Teilprojekt …“ and a link); the MCP tool `list_project_finves` takes the same `include_subprojects` option.
- **Design fixes.** Stronger active marker in the app bar and drawer; the „Admin“ entry is now „Einstellungen“; the Zeitstrahl uses more distinct phase colours (`TIMELINE_PHASE_COLOR`) and a thicker, haloed „heute“ line; the project table shows the short description as a tooltip on the name; the drawing buttons in the geometry editor wrap instead of being cut off.

### Added
- **IDT design system as the foundation (#217, stage 1).** The design system's `tokens.css` is vendored in `apps/frontend/src/shared/theme/` together with the self-hosted `InterVariable` (woff2); a Mantine theme with scales mixed from the DS colours, a CSS bridge (`mantine-bridge.css`) from Mantine variables to the DS aliases and `layout.css` for the layout tokens replace the old theme. The published `tokens.css` lacks its dark block, so a block generated from `tokens.json` is appended (#224). New favicon set and web manifest from the DS.
- **Dark colour scheme.** Follows the system setting by default; a toggle in the header switches it and the choice is remembered (`localStorage` key `schienendashboard.thema`). A small inline script in `index.html` sets the scheme before the first paint, so there is no flash. Maps swap the basemap when `REACT_APP_TILE_LAYER_URL_DARK` is set.
- **Register on the project page.** `ProjectRegister` replaces the table of contents: a 26px tab at the left edge on desktop that unfolds into a register lying over the page (starts folded, folds again after a pick; the page does not shift), a button „Abschnitte“ with a drawer on phones.
- **Tables as cards on phones.** `ResponsiveTable` switches every data table to a card list under 48em (one card per row, label/value pairs) instead of scrolling sideways.
- **State blocks and `Stat`.** `EmptyState`, `LoadingState`, `ErrorState` and `SaveStatus` in `src/shared/ui` give empty, loading, failed and saved states one look (no spinners); `Stat`/`StatBand` show key figures.
- **`semanticColors.ts`.** The one place that maps domain terms to colours: planning phases (teal ramp), `STATUS_TONE`, `SwatchTag`, traffic types, sources.
- **Footer with build version.** Every page (also the error page) ends in an ink footer with the IDT inverse logo, „Schienendashboard · Fassung <sha>“ and links to Impressum, Datenschutz and Dokumentation. The version comes from the build arg `VITE_APP_VERSION`, which `release.yml` sets to the short commit SHA (local builds: `dev`). The legal links go to an external URL when one is set in the app settings, else to `/impressum` and `/datenschutz`.
- **Impressum and Datenschutz pages.** `AppSettings` gains `impressum_url`, `impressum_markdown`, `datenschutz_url` and `datenschutz_markdown` (expand-only migration `20261021004`, all nullable); `GET /api/v1/settings/` returns them publicly, `PATCH` (settings.manage) is now partial and validates http(s) URLs, `""` clears. New routes `/impressum` and `/datenschutz`: a set URL redirects there, else the Markdown is rendered, both empty → empty state with a link to the admin card (settings.manage only). Maintained on `/admin` → card „Impressum und Datenschutz“. Content itself is a human task.
- **Optional dark map tiles.** `REACT_APP_TILE_LAYER_URL_DARK` (GitHub variable `TILE_LAYER_URL_DARK`, baked in by `release.yml`) is used in the dark colour scheme; the basemap source is swapped in place on scheme change. Empty → the light tiles stay.
- **Project preview on hover.** `ProjectHoverCard` shows a project's Kurzansicht (`ProjectSummaryCard`) when hovering a link to it: Wahlkreis panel and MdB list (Abgeordnete), FinVe and Infraplan cards („Verknüpfte Projekte“), GVFG overview and section, Infraplan section and review, sub-project table, timeline and task cards. The project is fetched only when the card opens (that fetch also warms the detail page); on touch devices the links stay plain links.

### Changed
- **Planning-state headline: newest report wins (2026-10-22).** The headline no longer goes to the highest trust × recency: the recency floor flattened every observation older than ~21 months, so a 15-year-old FinVe („Bau“) beat the 2023 VIB („In Betrieb“). Now FinVes are lower bounds that only raise the phase and never age; among status reports the newest wins, trust decides only within one year of it. A newer report with a lower phase sets the project back only if it is at least as trusted as the contradicting information (or manual), else the higher phase is kept; both cases are reported as conflicts. The source table shows age and trust (without recency) separately and marks lower bounds and conflicts. No migration.
- **Whole UI moved to the IDT design (#217, stages 2–4).** Colours, type (Inter), 0 px corners and 2 px frames, icons (lucide-react) and spacing follow the design system; Mantine buttons, fields, tables, dialogs, badges, alerts, notifications and tabs are styled once after the Anwendungsebene (`components.css`). Charts use a shared palette and furniture (`charts.css`), the timeline hatches uncertain stretches, maps use the DS colours and a 2 px frame. All former Chronicle/Tafel call sites (57 files) use Mantine components and the shared building blocks.
- **Header in the IDT design.** 72px (64px on phones) on paper with a 2px ink line, brand mark plus „Schienendashboard“, plain text links with a violet underline on the active entry, counters in an ink frame on violet-soft. „Aufgaben“ now counts the open tasks and turns red only when one is overdue; the Admin counter (open assignments) lost its filled violet badge. Direction-F `Signet`/`Wordmark` removed.
- **New default group colour `#6E50FA` (IDT violet).** New project groups (API schema,
  ORM default, MCP `create_project_group`, admin form) and projects without a group colour
  on the maps now use the violet of the IDT design instead of `#FF0000`/`#2563eb`; the
  admin colour picker offers six DS swatches, free input stays. ORM/schema defaults only,
  no migration: existing groups keep their stored colour.
- **New layout of `/infraplan`.** The explanation moved into a tooltip next to the title,
  the Jahrgang is picked from a dropdown in the header (once there is more than one), and a
  central switch (like Karte/Liste/Zeitstrahl on the start page) toggles between
  „Kennzahlen“ and „Maßnahmen“ (`?view=massnahmen`, `?jahr=`). The Kennzahlen get the
  project page's table of contents, one entry per kind and category. Maßnahmen are cards
  like the FinVe overview, with the linked projects as buttons (shared `LinkedProjects`).
  The Jahrgang also drives the Kennzahlen: Ist and Ziel of the chosen Infraplan, compared
  with the targets of the previous Jahrgang (dashed); later Jahrgänge are left out.
- **Elektrifizierungsgrad as two charts on `/infraplan`.** The share of the network (%)
  no longer sits inside the km chart on a right axis but gets its own card right next to
  it: the km are an annual figure, the share a cumulative stock, and one chart for both
  misled. Migration `20261021002` (data only) clears the companion link on existing
  databases, orders the share after the km KPI and adds a description to both where none
  is set; the seed matches.
- **KPI explanations as tooltips on `/infraplan`.** A KPI's description (Admin → Infraplan →
  Allgemeines, „Beschreibung“) now shows behind an info icon next to the name instead of
  as a subtitle. The Kapazitätsauslastung gets its definition from the Infraplan 2026
  (share of train-path km run on overloaded sections, > 125 % load) in the seed and in
  migration `20261021002`. The Mittelherkunft card names the shown year in its title.

### Removed
- **`make release-check` and GitHub milestones.** Milestones are no longer used; before a version tag the board must show no issue in `Needs User Test` whose change is already on `master` (AGENT.md → Release Gate).
- **`@tabler/icons-react`** (replaced by `lucide-react`) and **Google Fonts** (Archivo Narrow, IBM Plex, Inter TTF; only the self-hosted `InterVariable` remains).
- **Chronicle and Tafel components** (`components/chronicle`, `components/tafel`: `ChronicleCard`/`Button`/`Headline`/`DataChip`, `KpiCard`, `MiniBoard`, `Ticker`, `FlapText`, …) and the Direction-F tokens; `ProjectTableOfContents` (replaced by `ProjectRegister`).

### Added
- **GVFG funding questions the commissioning year.** When the newest GVFG edition still
  plans at least 1 Mio. € and 15 % of a project's aid for years after its known
  Inbetriebnahme (the edition's „Inbetriebnahme gepl.“ or the Infraplan's year, equal
  weight, the more recent statement wins), the forecast panel shows „Inbetriebnahme JJJJ fraglich“ with
  the amounts per year. The date itself is unchanged. API: `forecast.ibn_doubt`; MCP:
  `get_project_progress` and `list_project_gvfg`.
- **Infraplan import for 2027.** Matching writes out the Infraplan's abbreviations
  (Ubf, Vbk, Abzw, Ü-BW, 2gl., Bf, Mü, HH, MA, HD, Ffm, …) before comparing, finds the
  subproject of the parent the Bezeichnung names ("Großknoten München", "PB 07: ABS/NBS
  Karlsruhe – Basel") by section number or words, takes over the previous year's
  assignments also by row text (with their note) and treats a project number such as
  "InvKG Nr. 6" as a sure hit. New column `project.aliases` (migration `20261021003`,
  expand only): a Deutschlandtakt id "DT 38" counts as a sure hit, free aliases help the
  name matching and the project search. New MCP tools `assign_infraplan_rows`,
  `create_infraplan_subprojects` (also without a parent and after the confirmation),
  `get_infraplan_page_text`, `suggest_infraplan_kpi_values`, `check_project_data`;
  `get_infraplan_draft(compact=true)` and `list_projects(with_description=true)`, whose
  search now also covers description and aliases. Skill `infraplan-import` rewritten for
  batch calls and
  subagents. On the 271 rows of the Infraplan 2026, 145 rows reach ≥ 0.85 without a
  previous year (before: 93), 162 with the DT aliases.
- **One-off `scripts/set_dt_aliases_2026.py`** (run after the deploy, dry run first):
  sets 76 Deutschlandtakt aliases read from the Infraplan 2026 rows; a project is only
  changed while its number is the one the pair was read with. Idempotent.
- **Infraplan KPI settings in the admin area.** Admin → Infraplan gets the tabs „Import“
  and „Allgemeines“; the latter lists every KPI and edits name, unit, category,
  description, order and how `/infraplan` draws it (`PATCH /import/infraplan/kpis/{key}`).
  The display rules are new columns on `infraplan_kpi` (`chart_layout`, `total_series`,
  `companion_key`/`companion_label`, `zoomed_axis`; migration `20261021001`, expand only,
  sets the rules of the Infraplan 2026 on existing rows). `/infraplan` reads them instead of
  frontend constants: KMM as a sum with per-category details, ETCS on its Gesamtnetz with
  the equipment rate as a second bar on a right axis, small multiples for barrierefreie
  Bahnsteige, grouped bars for
  Planfeststellungsanträge, Herkunft/Einsatz lists for Mittelherkunft, a zoomed axis for the
  Stellwerksbesetzungsquote, stack totals in the tooltip. Units of the
  Informationskennzahlen are seeded from the Infraplan 2026.
- **MCP: create project groups.** New tool `create_project_group` (`projectgroup.create`)
  creates a group with name, unique short name, colour and visibility flags; duplicate
  short names/names and over-long values are rejected. Projects are added afterwards with
  `set_project_groups`.
- **MCP: generic project filters.** `list_projects` takes a `filters` list of
  `{field, op, value}` conditions (AND), and the new tool `list_project_filters` publishes
  the catalog (fields, types, operators, enum values) from one registry, so the MCP can ask
  what is filterable instead of the tool signature growing per request. Fields: `name`,
  `project_number`, `description` (text operators incl. `starts_with`, `contains`,
  `is_empty`), `closure` (Stilllegung), `phase`, `lifecycle_status`, `project_group`,
  `superior_project_id`, `length`, `is_known`, `has_geometry`, `has_length`,
  `parl_befassung_relevant`, `last_change`. The existing named parameters keep working and
  run through the same registry.
- **Import-created projects are drafts (#204).** The GVFG import now creates new projects
  with `is_draft = true` (the review dialog says so); the link to the Vorhaben stays and its
  funding data keeps counting in GVFG sums. MCP: `create_project` creates drafts unless
  `final=true`, new tool `set_project_draft(project_id, is_draft)` (`project.edit`, changelog),
  `list_projects` and `list_data_gaps` take `drafts` (exclude/only/include) and return
  `is_draft`, `list_gvfg_entries` marks draft projects. One-off correction for the 21 projects
  of the 2025–2029 import: `scripts/draft_gvfg_2025_projects.py` (idempotent, checks first).
- **Routing service in the system status.** `/admin/system` now shows whether GraphHopper is
  reachable (status, response time, next step on failure). New endpoint
  `GET /api/v1/system/routing` (`settings.manage`).
- **Text categories and internal texts.** Project texts get a category next to their type
  (seeded „Info“ and „Warnung“; editors add more with one of the fixed styles neutral, info,
  warning, critical). Warning and critical texts are highlighted with a left border. Texts can
  be marked internal: they and their attachments are then delivered to signed-in users only
  (the roadmap listed this as done, but it was never built). New endpoints
  `GET/POST /api/v1/text_categories`, MCP tool `list_text_categories`, `upsert_project_text`
  takes `category_id` and `is_public`. Colours come from semantic tokens `--text-cat-*`
  (new base token `--warn`). Migration `20261020002` (expand only: `category_id` nullable,
  `is_public` with server default true; existing texts become „Info“ and stay public).
- **Infraplan import, stages 2–5 (#180, #181, #184, #182).** Review of a draft: the parse
  task now suggests projects per row (project number of the previous year, GVFG key, fuzzy
  name; subprojects preferred) and preselects hits from 0.85; `PATCH …/rows/{row_key}`,
  `POST …/apply-suggestions`, `POST …/rows/{row_key}/subproject`, previous-year comparison
  in the draft, `POST /import/infraplan/confirm` (409 when the year exists or parser warnings
  are open, `force` overrides warnings only), `GET/DELETE /import/infraplan/report[/{year}]`
  (deleting reopens the draft), section "Infraplan" in `/admin/unassigned`
  (`/admin/unassigned-infraplan-entries`). Confirmed rows feed the planning state as source
  `INFRAPLAN` (trust 0.85, GVFG rows 0.75; phase, Planfeststellung, parliamentary track,
  expected commissioning in forecast and timeline; only the newest year counts) and a new
  PaBe-relevance level "laut Infraplan" (manual > Infraplan > project groups). Public reads
  `GET /infraplan/projects/{id}` (entries of all years, Gesamtkostenprognose with
  subproject sums, "nicht mehr im Infraplan"), `GET /infraplan/reports[/{year}/entries]`,
  `GET /infraplan/kpis` (checked values only). KPI values: `GET /import/infraplan/kpis`,
  `GET/PUT /import/infraplan/report/{year}/kpi-values`, `POST …/kpi-values/approve`; the 23
  KPI definitions of the Infraplan 2026 are created on first use. MCP tools
  `list_infraplan_drafts`, `get_infraplan_draft`, `start_infraplan_parse`,
  `apply_infraplan_suggestions`, `assign_infraplan_row`, `create_infraplan_subproject`,
  `confirm_infraplan_import` (refuses parser warnings), `get_infraplan_page_image` (image
  content), `list_infraplan_kpis`, `get_infraplan_kpi_values`, `set_infraplan_kpi_values`
  (stored unchecked), `get_project_infraplan`; `list_data_gaps` knows
  `infraplan_unassigned`. Skill `.claude/skills/infraplan-import`. Frontend: import and
  review pages, KPI form and approval, Infraplan section and cost block in the project
  detail, public page `/infraplan`. No migration.
- **VIB via MCP + skill (preferred way in).** An agent reads the Verkehrsinvestitionsbericht
  itself (skill `.claude/skills/vib-import/SKILL.md`, also a check mode for existing years)
  and writes it with new MCP tools (`list_vib_reports`, `create_vib_report`,
  `update_vib_report`, `list_vib_entries`, `get_vib_entry`, `add_vib_entries`,
  `update_vib_entry`, `set_vib_pfa_entries`, `assign_vib_entry`, `assign_vib_pfa`,
  `delete_vib_entry`, `confirm_vib_report`), gated by `vib.import`. Suggestions come from the
  previous year's confirmed assignment, then the VDE number, then the name (the
  "Lfd. Vorhaben Nr." prefix is ignored); at most one project is pre-assigned. Migration
  `20261020001` adds `vib_entry.confirmed` (existing rows become confirmed),
  `assignment_note` and `page`. Only confirmed VIB entries feed the planning state; MCP
  writes leave an entry unconfirmed, the upload confirm and assignments by an editor in the
  UI confirm it. The project page marks unconfirmed entries and offers "Bestätigen". The
  upload stays as a second way. See `docs/features/feature-vib-import.md` → Phase 7.
- **Drag & Drop für PDF-Uploads.** VIB-, Haushalts- und GVFG-Import sowie die Anhänge an
  Projekttexten nehmen Dateien jetzt auch per Drag & Drop an, zusätzlich zum Dateidialog
  (shared `FileDropZone` in `apps/frontend/src/shared/ui/`). Dateien mit falschem Typ werden
  mit einer Meldung abgewiesen.
- **MCP: GVFG-Bundesprogramm.** New read tools `list_gvfg_programs` (editions with year
  columns and counts), `list_gvfg_entries` (Vorhaben of an edition, search by key in any
  spelling or by name, filters Land, kind, part, Fördertatbestand, with/without project),
  `get_gvfg_entry` (all printed lines plus the key's history across editions) and
  `list_project_gvfg` (a project's GVFG funding, optionally with subprojects). The write tool
  `assign_gvfg_entry` (needs `assignment.manage`) replaces a Vorhaben's projects, optionally
  in every edition, and adds the groups "GVFG"/"GVFG BW" like the import. No migration.
- **MCP: skills come from the server.** `list_skills` and `get_skill` hand out the skills in
  `.claude/skills/` marked with `metadata: mcp: true`, so claude.ai and Claude Code always
  get the guide that matches the deployed tools — no more manual skill uploads. Only the thin
  entry skill `schienendashboard` is uploaded to claude.ai once. The backend image now needs
  the named build context `skills=.claude/skills` (`make test`, `release.yml`,
  `compose.override.yaml` pass it; a build without it fails on purpose).
- **Fulda-Runde via MCP + skill.** An agent reads the Federal Government's answer on the
  Fulda-Runde itself (skill `.claude/skills/fulda-runde/SKILL.md`) and writes it with new MCP tools (`list_fulda_categories`, `list_fulda_documents`,
  `create_fulda_document`, `update_fulda_document`, `add_fulda_entries`, `list_fulda_entries`,
  `assign_fulda_entry`, `update_fulda_entry`, `delete_fulda_entry`, `confirm_fulda_document`).
  New table `fulda_document`; entries gain category-defined statement kinds (Ist / ohne
  Folgephase / Prognose / Neuaufnahme), question, page, verbatim text, attribution and an
  assignment note. "Ist" lines set the phase as of the answer date, prognoses only add an
  expected date. New capability `fulda.import` (editors), which now also guards the Fulda REST
  routes (was `progress.edit`); `GET /import/fulda/categories` and `/documents` added.
  **Migration** `20261017001`: adds the table/columns and **deletes all existing Fulda entries
  and their derived observations** (to be re-read). See `docs/features/feature-fulda-import.md`.
- **MCP: free FinVe search.** `list_finves` searches all FinVes — including those not linked
  to any project — by FinVe number, name, Bedarfsplan number or lfd. Nr., with filters for
  budget year, Sammel-FinVe and project link; `get_finve` returns one FinVe with its budget
  history and linked projects. Previously FinVes were only reachable through a project
  (`list_project_finves`).
- **Edit saved project geometry in place.** The geometry editor (wizard step 2 and
  "Geometrie verwalten") gets a switch "Bestehende Geometrie bearbeiten": saved lines and points
  are loaded into terra-draw, vertices can be moved, intermediate points inserted and vertices
  deleted. Only changed parts are written back; feature order and properties are kept. Frontend
  only (`features/routing/editExisting.ts`).
- **Infraplan import, stage 1: parser + data model (#179).** `POST /api/v1/import/infraplan/parse`
  (PDF + `year`) stores the PDF with a new draft and starts the Celery task `parse_infraplan_pdf`,
  which reads the measure tables of chapter 2.3 (Bedarfsplan Teil A–D, GVFG Kat. A/C, InvKG)
  deterministically with pdfplumber: words with font size, column edges from the table headers,
  superscript footnotes split off, cost references resolved, commissioning normalised, running
  numbers checked per section (`warnings_json`), KPI chart pages noted (`kpi_pages_json`). Also
  `…/parse-result[/{id}]` (GET/DELETE), `…/reparse` and `…/page/{page}.png` (pymupdf). New
  capability `infraplan.import` (group Finanzierung, editors). **Migration** `20261015002`
  (additive): tables `infraplan_parse_result`, `infraplan_report`, `infraplan_entry`,
  `infraplan_entry_project`, `infraplan_kpi`, `infraplan_kpi_value`, column
  `progress_observation.infraplan_entry_id`; source type `INFRAPLAN`. **Deploy:** new setting
  `INFRAPLAN_PDF_DIR` (default `/app/uploads/infraplan`, inside the existing `uploads` volume);
  `/healthz` now also checks that it is writable. See `docs/features/feature-infraplan-import.md`.
- **GVFG display (stage 3).** The main menu item "Haushalt" becomes **"Finanzen"** with the
  sections "Bedarfsplan Schiene" (`/finanzen/bedarfsplan`, the former FinVe overview; `/finves`
  redirects) and "GVFG" (`/finanzen/gvfg`: all Vorhaben of an edition with filters, key figures,
  project links and sums per Land). The project page gets a "GVFG" section: newest edition with
  ∑/A/B/C lines, a bar chart of the yearly aid and the development across editions; a parent
  project links its subprojects' Vorhaben (`?with_subprojects=true`). GVFG Vorhaben of the newest
  edition without a project appear under *Admin → Offene Zuordnungen*
  (`GET /api/v1/admin/unassigned-gvfg-entries`, `PATCH …/{id}/assign`) and in the admin badge.
- **GVFG-Bundesprogramm import (stage 1).** Editors upload a programme PDF (main part or
  annex) under *Admin → GVFG-Import*; a Celery task reads it deterministically with pdfplumber
  (fixed column vocabulary, numbers placed by header column positions, tolerances scaled to the
  font size), checks the "Summe über <Land>" lines and every ∑ line against its A/B/C lines,
  and suggests projects (previous edition's links, normalised key, key without suffix, name).
  The review page shows the warnings, flags and suggestions; confirming writes the edition
  (`gvfg_program`, `gvfg_entry`, `gvfg_entry_amount` with the yearly aid per printed column,
  `gvfg_entry_project`) in one transaction, can create missing projects and adds the groups
  "GVFG"/"GVFG BW". Public reads: `GET /api/v1/gvfg/programs`, `…/programs/{id}/entries`,
  `…/projects/{id}/entries`. New capability `gvfg.import` (granted to editors).
  **Migration** `20261015001` (additive). See `docs/features/feature-gvfg-import.md`.
- **Merge duplicate projects (prerequisite for the GVFG import).** MCP tool `merge_projects`
  and `POST /api/v1/projects/merge` merge a duplicate into the project that stays: its empty
  fields are filled, property flags OR-ed, every link to the duplicate (groups, texts, FinVe/VIB/
  Fulda/Bauportal/media links, todos, observations, changelog, subprojects, …) is moved — found
  generically through the foreign keys, duplicates dropped — and the geometry comes from one side
  (`geometry_from`). Preview by default, `apply=true` deletes the duplicate and records a `MERGE`
  changelog entry. Its old id keeps working: `GET /api/v1/projects/{old id}` returns the project
  it went into and the detail page replaces the URL. New capability `project.merge` (seeded for
  no system role, i.e. admins only). **Migration** `20261014001` adds the table
  `project_redirect` (additive). See `docs/features/feature-project-merge.md`.
- **MCP: data maintenance across many projects (#175, stage A).** `list_data_gaps` lists
  projects with missing or outdated data in one call — no geometry, geometry without a saved
  route, no length, unknown planning state, no description, no project number, newest
  observation older than N years — with the gaps per project and counts per gap.
  `check_geometry` checks one project or a whole group: straight two-point chords instead of a
  routed line, gaps between line parts, start/end far from the operational points named in the
  project name, stored vs. computed length. `list_projects` gets the filters `is_known`,
  `has_geometry`, `has_length`, `lifecycle_status`, `parl_befassung_relevant` and
  `updated_since`, sorting (`order_by` name/id/length/last_change, `descending`) and reports
  `is_known` per project. All read-only, no migration.
- **Planning-phase filter on the map and list view (#9/#10).** The slim project-group list
  (`GET /api/v1/project_groups/`, `GET /api/v1/project_groups/{id}`) now carries `headline_phase`
  (manual override, else the cached computed phase; `null` without a progress row or when the phase
  is unknown) and `lifecycle_status` per project. Both come from the stored `project_progress` row,
  loaded with one bulk `selectinload` for all projects — list requests never run the derivation or
  the lazy resync. On `/` a multi-select "Planungsphase" filter (map panel, the phone bottom sheet
  "Karte einstellen" and the list filter row) narrows map and list to the chosen phases, including
  an "Unbekannt" option for projects without a phase; the selection is kept in `?phase=BAU,…`,
  combines with the group and search filters and survives map ↔ list switches. Paused/aborted
  projects are filtered by their headline phase. Project cards in the list view show a phase badge.
  No migration.
- **Constituency outlines via the admin page.** `/admin/abgeordnete` gets a GeoJSON upload
  („Wahlkreisgeometrien importieren"): `POST /api/v1/parliament/constituencies/import`
  (capability `parliament.import`) checks the file at once, stages it in the uploads volume
  and the worker imports the outlines and rebuilds the project–constituency links. No shell
  access to the server needed any more; `scripts/import_constituencies.py` stays as the
  alternative.
- **Skipped planning phases per project group (#164).** A project group can skip
  Vorplanung and/or Genehmigungsplanung (e.g. corridor renewals without Planfeststellung).
  The forecast and the phase bar leave such phases out when all of a project's groups
  skip them and no data places the project in them. New column
  `project_group.skipped_phases` (additive, defaults to `[]`), new field
  `hidden_phases` on the progress view.
- **Zeitstrahl view.** Next to Karte and Liste, `/?view=timeline` shows the projects of a
  group with credible dates (VIB-PFA, Fulda-Runde, expected manual entries, Planfeststellung,
  parliamentary involvement — never BVWP estimates) on a shared year axis. New public
  endpoint `GET /api/v1/project_groups/{id}/timeline`.
- **MCP: project groups and planning-state corrections.** New tools `list_project_groups`
  (groups with project counts), `set_phase_override` (pin or clear the main phase, with a
  required note) and `delete_progress_observation` (manual observations only).
  `list_projects` now matches a project group by id, short name or name (case-insensitive)
  and accepts a list of groups. `set_project_groups` adds a project to or removes it from
  groups by id, short name or name.
- **MCP: create projects and compute lengths.** `create_project` creates a (sub)project,
  recorded as a `CREATE` entry in the project change log. `compute_project_length` returns
  the length computed from the geometry (same calculation as the UI button) and can write
  it to the length field.
- **MCP: project geometry and routing.** `search_operational_points` finds Betriebsstellen,
  `get_project_geometry` summarizes a project's geometry per feature (full GeoJSON on
  request), `route_project_geometry` routes over the rail network via GraphHopper between
  operational points or coordinates (preview first, then `apply`; append or replace, stations
  as points) and `edit_project_geometry` draws lines and points from coordinates, adds
  operational points and deletes single features. Writes go through the project change log
  and are revertible; projects aggregating their subprojects' geometry stay protected.

### Changed
- **Fulda-Runde trust 0.7 → 0.55** (a working-level preview, below VIB 0.6). Forecast and
  timeline no longer let a Fulda date override a VIB-PFA date when earlier: per phase the date
  of the more credible × more recent report wins (VIB report date vs. Fulda answer date);
  manual expected dates still always win.
- **Removed** the Fulda OCR + LLM upload (`POST /import/fulda/parse`, Celery task
  `parse_fulda_pdf`, upload form) and "Fulda-Runde" as a source for manual observations.
- **Members of parliament are only shown to signed-in users.** All read routes under
  `/api/v1/parliament` and `GET /api/v1/projects/{id}/constituencies` now require a login
  (any role) and answer 401 otherwise. The frontend hides the "Abgeordnete" nav entry, the
  "Wahlkreise und Abgeordnete" block in the project detail and the map's "Wahlkreise" switch
  for anonymous visitors; `/abgeordnete` shows a hint instead.
- **Planning-state changes are written to the project change log** — from the UI and from
  MCP alike: flags, overrides, PF/parliament details, observations added or deleted and
  linked documents. They show up as "Planungsstand" entries in the project history
  (history only, no revert).
- **Project group changes are written to the project change log** (as an id list, shown
  with short names) and can be reverted like any other project field.

### Fixed
- **GVFG import reads the 2023 edition completely.** Header typos in single tables
  („1967-2020“ / „2022“ for „1967-2021“ / „vsl. 2022“) are mapped onto the edition's
  columns with a review hint instead of becoming extra year columns; a header that
  splits „Bundesfinanzhilfen insgesamt“ over two cells keeps the aid total (16 D 4520_A);
  „Kat: C“ and a key without underscore („03 D 4505 A“, previously missing) are read.
  Confirming a parse with the financial part now replaces the edition's year columns,
  so a re-import removes wrongly read ones.
  The data migration `20261022002` applies the same corrections to the already
  imported edition 2023–2027 on the next deploy (no re-upload); it does nothing without
  that edition.
- **Infraplan: full stops read as "�".** Some prints of the Infraplan 2026 map the table
  font's full stop to U+FFFD in their ToUnicode table, so every "." came out as "�"
  ("4gl�", "1�676,02", "E�1637260058") — which also broke costs from 1,000 Mio. € on, the
  "Ref. Teil …" cost references, the Lph of the state column and the matching by project
  number. The text extraction now restores the full stop. Still unreadable glyphs
  (U+FFFD, `(cid:N)`) and cost cells that are neither number nor reference become parser
  warnings (`UNREADABLE_TEXT`, `UNPARSED_COST`) instead of being lost silently.
  `scripts/repair_infraplan_full_stops.py` (dry run, `--apply` to write) repairs stored
  drafts and the years confirmed from them in place — assignments and KPI values stay.
- **Text history: partial updates no longer log untouched fields.** A text PATCH that sends
  only some fields (e.g. via MCP `upsert_project_text`) recorded every other tracked field as
  cleared; now only the sent fields are compared.
- **Timeline: separate construction stages of a superior.** A superior whose subprojects
  build in separate stages (e.g. HLK 11 München-Ost – Rosenheim, 2028 and 2031) no longer shows
  one continuous BAU bar across the gap. The timeline items carry `construction_periods`
  (union of each subtree member's own Baubeginn–Inbetriebnahme interval, overlapping/touching
  intervals merged, only reported with a real gap); the bar draws one BAU segment per stage and
  the pause as a dashed "zwischen Bauetappen" line. Milestones and the "IB" headline are
  unchanged. No migration.
- **The backend image creates `/app/uploads` owned by `appuser`.** A named volume created
  before the directory existed in the image was root-owned, so the app could write neither
  text attachments nor (since v0.0.15) import PDFs; `/healthz` reports this as
  `upload_dir`. New volumes now start with the right owner; the production volume was fixed
  by hand on 11.10.2026 (DEPLOY.md, "Backup & Restore").
- **`.env.prod.example` sets `ENVIRONMENT=production`.** Production ran without it, i.e. as
  `development`, so the session cookie lacked the `Secure` flag. Set on the server on
  11.10.2026.

### Changed
- `deploy.yml` can pin the server's SSH host key via the new environment secret
  `DEPLOY_FINGERPRINT` (empty = no check, as before).

### Changed
- **Deploys are dispatched by hand per commit SHA, no longer triggered by a tag.** Three
  workflows replace the tag pipeline: `ci.yml` runs `make test` on every pull request (job
  `Prüfung`), `release.yml` runs it again on every push to `master` and then pushes the four
  images tagged with the commit SHA (+ `latest`), `deploy.yml` (*Run workflow*, empty SHA =
  current `master`, rollback = an earlier SHA) checks that all images exist, calls
  `/srv/raildashboard/prod.sh <sha>` over SSH and then checks
  `https://dashboard.schienengruen.de/healthz` from outside. Contract: `DEPLOY.md`,
  reasoning: `docs/workflow.md`, manual setup: `docs/uebergabe-deploy.md`.
- **`make test` is the one full check**, identical locally and in CI: stub tests for
  `prod.sh`, then backend pytest and frontend `tsc`/`eslint`/Vitest inside new `test`/`check`
  stages of the Dockerfiles, then the runtime image builds. The former `make test` is now
  `make test-local`.
- **`/healthz` is the deploy gate.** New endpoint (outside `/api/v1`, proxied by the
  container nginx) that returns 200 only when the database is reachable, a full `Project`
  row loads (catches schema/code drift that `SELECT 1` misses), `SESSION_SECRET_KEY` is no
  placeholder and the upload directories are writable; otherwise 503 with a problem list.
  The backend container healthcheck now uses it. `/api/v1/health` stays.
- **Pre-migration backup moved into the stack.** A one-shot `backup` service (db image,
  `docker/db/backup.sh`) dumps the database to `backups/pre-migrate_<time>_<sha>.dump`
  before the backend starts and migrates; retention `BACKUP_KEEP` (default 10).
- **Rollback after a migration comes up.** The backend entrypoint skips
  `alembic upgrade head` when the database is on a revision the code does not know
  (`apps/backend/scripts/db_ahead.py`).

### Deploy
- `docker-compose.yml` → `compose.yaml` (with `name: raildashboard`, so volumes keep
  their names), `docker-compose.override.yml` → `compose.override.yaml`.
- **Ports:** `frontend` is published on `127.0.0.1:5000` only (the host nginx still
  reaches it); `graphhopper` is no longer published at all. Both were open on `0.0.0.0`.
- `scripts/deploy.sh` is replaced by `deploy/prod.sh`, which reads `SSH_ORIGINAL_COMMAND`
  itself, accepts only a full commit SHA (exit 2 otherwise), pulls before switching
  `IMAGE_TAG`, includes `up -d` in the rollback condition and rolls back without a new
  dump. The deploy key gets a forced command without interpolation. New environment
  secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`; the server logs in to GHCR
  itself with a classic `read:packages` token. Steps: `docs/uebergabe-deploy.md`.

## [v0.0.15] - 2026-10-07

### Added
- **MCP server for AI assistants, with personal API keys.** Claude Code and other MCP clients
  can now connect to `https://<host>/mcp` (Streamable HTTP) and search projects, read
  financing, planning state, texts and tasks, and — with a write key — update projects, add
  planning-state observations, upsert project texts and create/update tasks. Writes land in
  the existing changelogs. Authentication uses new personal **API keys**
  (`Authorization: Bearer rdb_…`), managed on the new admin page `/admin/api-keys`: the token
  is shown once, keys expire after **90 days**, can be revoked anytime, and are either
  read-only or carry the owner's rights. Keys work against the whole REST API too, narrowed to
  their scopes without the admin bypass. For now only admins get access, via the new
  capability `mcp.access`.

### Changed
- New table `api_keys` (migration `20261007001`, applied automatically on start).
- New Python dependency `mcp==2.3.0` (exactly pinned in `requirements.txt`).
- Container nginx proxies `location = /mcp` to the backend with buffering off and a 300 s
  read timeout. A host proxy in front only needs to pass `/mcp` through (the default
  `location /` already does); new optional setting `MCP_ENABLED` (default `true`).
- PDF imports (Haushalt, VIB, Fulda) no longer send the PDF through the Celery broker.
  The upload endpoint stages the file in the `uploads` volume (`IMPORT_STAGING_DIR`,
  default `/app/uploads/import-staging`) and passes only its name; the task deletes it
  afterwards, also on failure, and files never picked up are swept after 24 h (#149).
- The HTML shell declares German as the site language: German title and meta
  description plus a `Content-Language: de` header from nginx. The English title
  made browsers offer to translate the already German page (#128).
- The project detail map now zooms to the project's geometry (or its subprojects')
  instead of centring on `Project.centroid` at a fixed zoom (#136).

### Removed
- `Project.centroid` and its API field. It was written only by the old-database import
  and never maintained since, so it was empty or stale for every project created or
  edited afterwards. Migration `20260928001` drops the column (runs automatically on
  deploy; the downgrade restores it empty) (#136).

### Fixed
- **The members-of-parliament import can now be started from the UI.** The backend endpoints
  `POST /parliament/import` and `POST /parliament/recompute-links` existed, but no page called
  them — the hint on `/abgeordnete` pointed to an admin entry that did not exist. New admin page
  `/admin/abgeordnete` ("Abgeordnetenstand", capability `parliament.import`) shows the Abrufstand
  of all three runs and key figures, and launches both Celery jobs with progress and a
  stuck-worker warning. Linked from the admin overview and from the empty-state hint; the header's
  Admin entry now also appears for users holding only `parliament.import`.

### Deploy
- **The `worker` service now mounts the `uploads` volume** (`docker-compose.yml`). The
  deploy picks it up automatically; without it every PDF import fails with
  `FileNotFoundError`.

## [v0.0.14] - 2026-09-28

### Added
- **The whole application is now usable on a smartphone.** Every route is laid out for screens from
  360 px up: the page itself never scrolls sideways, data tables scroll inside their own card (new
  `ResponsiveTable`), and dialogs and drawers take the full width on a phone. The map fills the
  visible viewport with the search as a slim strip on top; project groups, layer switches and the
  line/point sliders moved into a bottom sheet ("Karte einstellen"). The constituency panel becomes
  a bottom sheet, the project detail page puts its secondary actions into a ⋮ menu and stacks
  label/value rows, and the geometry editor places its control panel above the map instead of
  beside it. Two shared breakpoints (`useIsMobile` < 48em, `useIsCompact` < 62em) and new layout
  tokens (`--page-pad`, `--card-pad`, `--map-height`) steer this centrally; the main navigation now
  collapses into the burger at 62em instead of 100em. See
  `docs/features/feature-mobile-usability.md`.

### Changed
- **Schnellere Startseite/Karte:** `GET /api/v1/project_groups/` liefert Projekte nur noch als
  schlanke Einträge ohne Geometrie (`ProjectListItem`; boolesche Merkmale als
  `active_features`) — im produktionsgroßen Testdatensatz 10,4 MB → 0,27 MB (gzip 7 KB).
  Die Karte lädt die Verläufe danach je ausgewählter Gruppe über den neuen Endpunkt
  `GET /api/v1/project_groups/{id}/geometries?only_superior=true|false` — vereinfacht
  (≈ 20 m Toleranz, Koordinaten auf ≈ 1 m gerundet), Teilprojekte nur bei Bedarf.
  Die Detailansicht nutzt weiterhin die exakte Geometrie. Siehe
  `docs/features/feature-slim-project-groups.md`.
- **Schnelleres Frontend:** Die Kartenbibliothek (maplibre, ≈ 264 kB gzip inkl. CSS) wird nur
  noch geladen, wenn tatsächlich eine Karte angezeigt wird — Listenansicht, Projektdetail-Texte,
  Dokumentation und Admin-Seiten starten ohne sie; auf der Karte lädt sie parallel zu den Daten.
  Ursache war ein Build-Artefakt (Rollups CommonJS-Helfer im maplibre-Chunk). Diagramm-CSS und
  Dokumentationsseite sind ebenfalls ausgelagert, Web-Fonts blockieren den ersten Seitenaufbau
  nicht mehr.
- Projekt-Detailseiten werden beim Überfahren einer Projektkarte bzw. beim Auswählen eines
  Projekts auf der Karte vorgeladen und öffnen dadurch meist ohne Ladeanzeige.
- Die Listenansicht zeigt große Projektgruppen in Schritten von 48 Karten („Weitere …
  anzeigen"); die Suche bleibt dabei flüssig.
- Liste, Einzelgruppe und Geometrien senden einen `ETag`; unveränderte Antworten kommen als
  `304` ohne Body.

### Fixed
- API-Antworten werden jetzt im Backend gzip-komprimiert (`GZipMiddleware`, ab 1 KB) —
  unabhängig vom Reverse Proxy. Der Container-nginx komprimiert zusätzlich auch hinter einem
  Proxy, der per HTTP/1.0 weiterleitet (`gzip_http_version 1.0`); bisher kamen API und
  JS-Assets dort unkomprimiert an. Keine Änderung am Server nötig.

## [v0.0.13] - 2026-09-24

### Added
- **Systemstatus der Hintergrund-Aufträge** unter `/admin/system` (Recht `settings.manage`, verlinkt
  von der Administrations-Übersicht mit Warn-Badge, sobald kein Worker läuft): Erreichbarkeit der
  Warteschlange, jeder laufende Celery-Worker mit seinen aktuellen Aufträgen, Länge der
  Warteschlange und die Befehle für den Fall, dass etwas fehlt. Neuer Endpunkt
  `GET /api/v1/tasks/workers` (`?refresh=true` erzwingt eine frische Prüfung); jede Sonde ist mit
  einem Timeout begrenzt, gibt Fehler als Wert statt als Ausnahme zurück und liefert die Broker-URL
  ohne Zugangsdaten. Siehe `docs/features/feature-worker-status.md`.
- Ein Import, den kein Worker abholt, benennt seinen Grund jetzt selbst: `GET /api/v1/tasks/{id}`
  liefert zusätzlich ein `hint`-Feld, und die Import-Seiten (Haushalt, VIB, Fulda) zeigen es nach
  ~12 s unter dem Fortschrittsbalken samt Link auf den Systemstatus — bis dahin sah ein hängender
  Auftrag genauso aus wie ein langsamer, weil Celery für beides `PENDING` meldet.
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
- `OcrResult` now carries the markup of each recognised table per page (`tables`) and the format it
  is in (`table_format`), which is what lets a table source read the grid instead of the prose.
- `extract_document_text` takes a `table_format` ("markdown" or "html"). The Haushalt asks for HTML:
  one of its records spans several printed lines inside a single table row, and markdown cannot
  express a line break inside a cell — the model joins the stacked lines with spaces and which value
  belongs to which sub-entry is lost. VIB and Fulda keep markdown, unchanged.
- The Haushalt row detection reads the Lfd. Nr., the FinVe number and the Bedarfsplan number through
  the column mapping, so a row is recognised whether the PDF merges those three columns into one
  cell ("B0080 275 N19", the 2026+ layout pdfplumber returns) or keeps them apart. The identity of a
  row no longer depends on one report generation's cell merging.
- **Wahlkreise und Abgeordnete auf Projekten.** Project geometries are intersected with
  the 299 Bundestag constituencies, and the members of parliament responsible for those
  constituencies are attached to the result — the answer to "what connects this member of
  parliament with this project?". Three entry points on the same data: a block on the
  project detail page (constituencies heaviest first, direct mandates visibly separated
  from "ran here, entered over the state list"), the new page `/abgeordnete` with name
  search plus transport-/budget-committee and faction filters, and a switchable
  constituency layer on the map whose selection shows projects and MPs.
- Repeatable, idempotent imports: `scripts/import_constituencies.py` for the constituency
  outlines (Die Bundeswahlleiterin, © GeoBasis-DE / BKG) and the Celery task
  `refresh_parliament_data` for the people (abgeordnetenwatch API v2, CC0). Every run is
  recorded as an Abrufstand and shown in the UI; a people import older than 60 days is
  flagged as stale.
- Public read endpoints `GET /api/v1/projects/{id}/constituencies`,
  `/api/v1/parliament/{status,politicians,politicians/{id},constituencies,
  constituencies/{id},constituencies/geojson}`; the two import endpoints
  (`POST /api/v1/parliament/import`, `POST /api/v1/parliament/recompute-links`) require
  the new capability `parliament.import`.

### Changed
- The 50 MB upload ceiling is enforced in one place per side instead of per endpoint. The Haushalt,
  VIB and Fulda parse endpoints previously read their PDF with no limit at all — only the text
  attachment upload checked one — and now share `deps.read_upload_within_limit`; the frontend shares
  `shared/api/uploads.ts` for the pre-flight check and the error text.

- The Haushalt import keeps taking its numbers from pdfplumber. The comparison against the real OCR
  API has now been run (EP 12 Part B, 2027 draft, `mistral-ocr-latest`) and came back red: 141 rows
  from pdfplumber against 107 from the OCR stage, 79 differing values. The model omits the `YYY`
  identity marker on the pages of tables 2–4 (34 rows lost, three tables entirely), reads about 29
  of 5,568 numeric tokens differently from how the report prints them, and sometimes emits the minus
  sign of a negative delta as a table cell of its own so the amount lands in the percent column.
  `HAUSHALT_EXTRACTION` stays on `pdfplumber` and `pdfplumber` stays in `requirements.txt`; the
  switch and the comparison script remain as the measuring instrument for the next model generation.
  Full evaluation in `docs/features/feature-pdf-import-unification.md`.

### Fixed
- Die Fortschrittsanzeige des Haushalts-Imports meldete während des gesamten Laufs „0 Zeilen
  gefunden“ — der Wert war im Backend fest auf 0 verdrahtet. Sie zählt jetzt die tatsächlich
  gelesenen Tabellenzeilen mit, und jede Stufe nach der Textgewinnung (Spaltenzuordnung, OCR,
  Speichern) meldet eine eigene Beschriftung, statt auf der letzten Seitenzahl stehen zu bleiben.
- Ein fehlgeschlagener Hintergrund-Auftrag meldete nur noch `Parser-Fehler: <str(exception)>`, bei
  einer leeren Ausnahme also gar nichts. Die Meldung nennt jetzt Fehlerklasse, Text und die Datei
  samt Zeile, in der die Ausnahme entstanden ist, dazu den Befehl für das vollständige Worker-Log;
  sie schließt sich nicht mehr von selbst.

- Uploading Annex VWIB Part B (3.6 MB) failed with `413 Request Entity Too Large` before the request
  ever reached the application. The TLS proxy in front of the Docker stack carried no
  `client_max_body_size`, so nginx applied its 1 MB default while the container nginx and the backend
  both allowed 50 MB. The limit is now documented as one value across all three layers
  (`docs/production_setup.md` → Deploy-Vertrag and both TLS options); the server-side configuration
  is a manual step on the host, not part of the image.
- The PDF importers reported every upload failure as a bare "Upload fehlgeschlagen.", which hid the
  cause: a proxy answers `413` with an HTML page, so the status code was the only signal and it was
  discarded. Haushalt, VIB and Fulda now name the size limit when the upload is rejected for it, and
  check the file against the limit before sending it at all.

- A measure's Mittelherkunft — which Haushaltstitel funds how much of it — no longer loses values.
  The report prints one line per Titel, but `extract_table` keeps only the non-empty lines of each
  column, so a column printed on the measure's line and on the last Titel's line arrived as a single
  value and was given to neither. The lines the report printed inside each row are now kept beside
  it (`ExtractedPage.row_lines`) and each Titel takes the values printed on its own line. Measured
  against the word coordinates of the EP 12 Part B 2027 report: 28 of 179 Titel rows carried a wrong
  or missing value before, none do now. Measure-level figures were never affected.
- The Haushalt import no longer folds the other tables of Annex VWIB Part B (Lärmsanierung, ERTMS,
  Kleine und Mittlere Maßnahmen, InvKG) into the Bedarfsplan table. Their rows carry no FinVe number
  and were appended to the last Sammel-FinVe of the first table — in the 2027 report that gave
  "SV Rest 2025" 51 instead of 3 Titel entries and 78 instead of 1 Erläuterung project. The tables
  are now detected from their page caption and each is parsed on its own.
- A measure without a printed FinVe number no longer collides with a real one on insert. FinVe
  numbers are the primary key and are written explicitly, so the sequence never advances past them
  and the first auto-assigned id hit an existing row (`duplicate key value violates unique
  constraint "finve_pkey"`). Those measures now take their id from a reserved band above any number
  the report prints.
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
- The geometry cascade in `crud/projects/projects.py` now also refreshes the constituency
  links of every project it touches, so a change to a subproject keeps the parent's
  assignment current.

### Database
- Migration `20260910001` adds `parliament_period`, `constituency` (with a GiST index on
  the outline), `politician`, `mandate`, `committee`, `committee_membership`,
  `parliament_import_run` and `project_to_constituency`.

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
