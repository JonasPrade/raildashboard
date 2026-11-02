# Feature: Admin — Offene Zuordnungen (Unassigned FinVes & VIB Entries)

## Goal

Provide editors and admins with a single page (`/admin/unassigned`) that surfaces all imported records that have not yet been linked to a project, and lets them assign projects inline without leaving the page.

## Scope

- **FinVes without a project**: rows in `finve` with no corresponding entry in `finve_to_project`
- **VIB entries without a project**: rows in `vib_entry` with no corresponding entry in `vib_entry_project` — confirmed or not (entries read in over MCP stay open until they have a project). Assigning here is an editor's decision and confirms the entry (`vib_entry.confirmed = true`, see `feature-vib-import.md` → Phase 7).
- Inline project assignment (searchable MultiSelect) per row
- Header badge showing total unassigned count (editor/admin only)
- „Dauerhaft ignorieren“: hide a record that will never get a project (see below)

Out of scope: creating new projects from this page (future roadmap item). Changing or removing links of FinVes that are already assigned: see `feature-finve-zuordnung.md` — the assign endpoint here uses the same function (logged per project, planning state recomputed).

## Acceptance Criteria

1. `/admin/unassigned` is accessible to editor and admin roles only.
2. Two table sections are shown: FinVes and VIB entries, each with a count badge.
3. Each row has a searchable MultiSelect for project(s) and a "Zuweisen" button.
4. After successful assignment the row disappears from the table; counts update immediately.
5. The header shows a "Offene Zuordnungen" link with a counter badge when there are unassigned items (ink frame on violet-soft; red only when something is overdue — IDT design, W7 in `feature-idt-design.md`, 2026-10-21).
6. All four new API endpoints require editor/admin auth.

## Dauerhaft ignorieren

Some imported records never get a project — a bus or tram Vorhaben in the GVFG
programme, a pure equipment or Sammel line, a VIB entry outside the scope. Until
now they stayed in the list and in the header count for good. Requested long ago,
built 2026-11-02.

- Every row (FinVe, VIB, GVFG, Infraplan) has the anchor „Dauerhaft ignorieren“
  next to „Projekt fehlt?“. It opens a confirm modal with an optional reason.
- An ignored record leaves its open list and the header/admin-overview count
  (the four `unassigned-*` lists filter it out, so the MCP gap report
  `list_data_gaps` → `infraplan_unassigned` skips it too).
- Ignoring never changes the record: links, confirmation and planning state stay.
  If the record gets a project later (e.g. over MCP), the dismissal is moot.
- The collapsed section „Ignorierte Einträge“ at the end of the page lists them
  (source, label, reason, who, when) with „Wieder aufnehmen“, which deletes the
  dismissal.
- Scope is the single record. GVFG and Infraplan rows are per edition, so the
  same Vorhaben in a new edition shows up again — deliberate: a new edition can
  change what a Vorhaben is. Carrying dismissals over by key is a possible
  follow-up.
- Permission `assignment.manage`, as for assigning.

Storage: table `assignment_dismissal` (`kind` ∈ finve, vib, gvfg, infraplan;
`entry_id`; `note`; `dismissed_at`; `dismissed_by_user_id`), unique on
(`kind`, `entry_id`), no foreign key to the four source tables. Expand-only
migration `20261102001`. CRUD in `crud/assignment_dismissals.py`.

## Backend

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/unassigned-finves` | editor/admin | FinVes with zero project links |
| GET | `/api/v1/admin/unassigned-vib-entries` | editor/admin | VibEntries with zero project links |
| PATCH | `/api/v1/admin/unassigned-finves/{finve_id}/assign` | editor/admin | Assign project(s) to a FinVe |
| PATCH | `/api/v1/admin/unassigned-vib-entries/{entry_id}/assign` | editor/admin | Assign project(s) to a VIB entry |
| GET | `/api/v1/admin/dismissed-assignments` | editor/admin | Ignored records with label, reason, user, date |
| PUT | `/api/v1/admin/dismissed-assignments/{kind}/{entry_id}` | editor/admin | Ignore a record for good (`{note?}`, idempotent; 404 if the record does not exist) |
| DELETE | `/api/v1/admin/dismissed-assignments/{kind}/{entry_id}` | editor/admin | Undo, the record is open again |

### Schemas

```
UnassignedFinveSchema { id, name, is_sammel_finve, starting_year }
UnassignedVibEntrySchema { id, vib_name_raw, vib_section, category, report_year }
AssignProjectsInput { project_ids: list[int] }
```

### CRUD

- `list_unassigned_finves(db)` — LEFT OUTER JOIN `finve_to_project`, filter `finve_to_project.id IS NULL`
- `list_unassigned_vib_entries(db)` — LEFT OUTER JOIN `vib_entry_project`, filter `vib_entry_project.vib_entry_id IS NULL`
- `assign_finve_to_projects(db, finve_id, project_ids, user)` — adds permanent rows to `finve_to_project` (haushalt_year=NULL) via `crud/finve_links.py`; skips duplicates, logs `finve_ids` per project and recomputes the planning state
- `assign_vib_entry_to_projects(db, entry_id, project_ids)` — inserts rows into `vib_entry_project`; skips duplicates

### Router

New file `api/v1/endpoints/admin_assignments.py`, registered under prefix `/api/v1/admin` in `api/v1/router.py`.

## Frontend

### Files

- `features/admin/UnassignedPage.tsx` — new page
- `router.tsx` — add route `admin/unassigned`
- `components/Header.tsx` — add nav link with badge
- `shared/api/queries.ts` — add 4 new hooks

### Query Hooks

```ts
useUnassignedFinves()          // GET /admin/unassigned-finves
useUnassignedVibEntries()      // GET /admin/unassigned-vib-entries
useAssignFinve()               // PATCH /admin/unassigned-finves/{id}/assign
useAssignVibEntry()            // PATCH /admin/unassigned-vib-entries/{id}/assign
```

Project search reuses the existing project search endpoint already available in `queries.ts`.

### Page Layout

```
/admin/unassigned
├── Title: "Offene Zuordnungen"
├── Section: "FinVes ohne Projektzuordnung" [badge: N]
│   └── Table: id | name | Typ | Jahr | Projekte zuweisen [MultiSelect + Button]
└── Section: "VIB-Einträge ohne Projektzuordnung" [badge: N]
    └── Table: id | Name | Abschnitt | Kategorie | Jahr | Projekte zuweisen [MultiSelect + Button]
(… GVFG and Infraplan sections …; each row: „Projekt fehlt?“ · „Dauerhaft ignorieren“)
└── Section (collapsed): "Ignorierte Einträge" [badge: N]
    └── Table: Quelle | Eintrag | Grund | Ignoriert (Datum, Person) | [Wieder aufnehmen]
```

Header link "Offene Zuordnungen" visible for editor/admin; counter badge = sum of both counts (hidden when 0; neutral badge, red only for overdue items since the IDT design).

## Technical Notes

- `assign_finve_to_projects` uses `haushalt_year=None` (permanent link, same as non-SV FinVes).
- Duplicate inserts are silently skipped via `ON CONFLICT DO NOTHING` or a pre-check.
- After `gen-api`, the frontend client is regenerated from the updated OpenAPI schema.
