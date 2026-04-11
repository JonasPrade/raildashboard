# Feature: Admin — Offene Zuordnungen (Unassigned FinVes & VIB Entries)

## Goal

Provide editors and admins with a single page (`/admin/unassigned`) that surfaces all imported records that have not yet been linked to a project, and lets them assign projects inline without leaving the page.

## Scope

- **FinVes without a project**: rows in `finve` with no corresponding entry in `finve_to_project`
- **VIB entries without a project**: rows in `vib_entry` with no corresponding entry in `vib_entry_project`
- Inline project assignment (searchable MultiSelect) per row
- Header badge showing total unassigned count (editor/admin only)

Out of scope: creating new projects from this page (future roadmap item).

## Acceptance Criteria

1. `/admin/unassigned` is accessible to editor and admin roles only.
2. Two table sections are shown: FinVes and VIB entries, each with a count badge.
3. Each row has a searchable MultiSelect for project(s) and a "Zuweisen" button.
4. After successful assignment the row disappears from the table; counts update immediately.
5. The header shows a "Offene Zuordnungen" link with a red badge when there are unassigned items.
6. All four new API endpoints require editor/admin auth.

## Backend

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/unassigned-finves` | editor/admin | FinVes with zero project links |
| GET | `/api/v1/admin/unassigned-vib-entries` | editor/admin | VibEntries with zero project links |
| PATCH | `/api/v1/admin/unassigned-finves/{finve_id}/assign` | editor/admin | Assign project(s) to a FinVe |
| PATCH | `/api/v1/admin/unassigned-vib-entries/{entry_id}/assign` | editor/admin | Assign project(s) to a VIB entry |

### Schemas

```
UnassignedFinveSchema { id, name, is_sammel_finve, starting_year }
UnassignedVibEntrySchema { id, vib_name_raw, vib_section, category, report_year }
AssignProjectsInput { project_ids: list[int] }
```

### CRUD

- `list_unassigned_finves(db)` — LEFT OUTER JOIN `finve_to_project`, filter `finve_to_project.id IS NULL`
- `list_unassigned_vib_entries(db)` — LEFT OUTER JOIN `vib_entry_project`, filter `vib_entry_project.vib_entry_id IS NULL`
- `assign_finve_to_projects(db, finve_id, project_ids)` — inserts rows into `finve_to_project` (haushalt_year=NULL); skips duplicates
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
```

Header link "Offene Zuordnungen" visible for editor/admin; red badge = sum of both counts (hidden when 0).

## Technical Notes

- `assign_finve_to_projects` uses `haushalt_year=None` (permanent link, same as non-SV FinVes).
- Duplicate inserts are silently skipped via `ON CONFLICT DO NOTHING` or a pre-check.
- After `gen-api`, the frontend client is regenerated from the updated OpenAPI schema.
