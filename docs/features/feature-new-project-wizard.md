# Feature: Neues Projekt anlegen (Multi-Step Wizard)

## Ziel

Multi-step wizard at `/admin/projects/new` (editor/admin only). Entry point: button in the admin section (exact position TBD). Uses a Mantine `Stepper`.

Steps 2–5 are optional/skippable — the project is already persisted after step 1 completes.

---

## Wizard Steps

### Step 1 — Stammdaten *(required)*

Fields:
- `name` (required)
- `project_number`
- `description`
- `justification`
- `superior_project` — searchable combobox (same pattern as `StationSelect`); debounced `GET /api/v1/projects?q=` → `ProjectSearchSelect` component
- `project_groups` — MultiSelect (same as in `ProjectEdit.tsx`)

On "Weiter": `POST /api/v1/projects` → creates the project and returns the new `ProjectSchema` with its `id`. All subsequent steps use this `id`.

### Step 2 — Geometrie *(optional)*

Inline version of the `GeometryManagementModal` left-panel controls (route calculator + operational points + GeoJSON upload). No modal wrapper needed — embed the controls directly in the stepper page.

Uses the existing PATCH endpoint (`useUpdateProjectGeometry`) and route confirm flow. The `deleteExisting` toggle can be omitted since no geometry exists yet.

### Step 3 — Projekteigenschaften *(optional)*

All boolean/numeric fields from `ProjectEdit.tsx` (Verkehrsarten, Streckenausbau, Bahnhöfe & Infrastruktur, Signaltechnik, Elektrifizierung, Sonstiges).

**Refactor required:** Extract the inner form section of `ProjectEdit.tsx` into a shared `ProjectEditFields` component (props: `values`, `setValues`) so both the wizard and the existing edit Drawer reuse it without duplication.

Submits via `PATCH /api/v1/projects/{id}`.

### Step 4 — FinVes verknüpfen *(optional)*

Searchable MultiSelect of all existing FinVes (id + name + finve_nr). Links the selected FinVes to the new project.

Backend: reuse `assign_finve_to_projects` from `crud/admin_assignments.py`. Expose via a new endpoint `POST /api/v1/projects/{id}/finves` that accepts `{ finve_ids: number[] }`.

### Step 5 — VIB-Einträge verknüpfen *(optional)*

Searchable list of confirmed VIB entries (name + year). Assigns the new project to the selected entries by adding its id to `project_ids`.

Backend: check whether `PATCH /api/v1/import/vib/entries/{id}` already supports `project_ids` update; if not, add it.

---

## Backend Changes

| Task | Status |
|---|---|
| `POST /api/v1/projects` — create project (name required, all other fields optional); returns `ProjectSchema` | **missing — must build** |
| `POST /api/v1/projects/{id}/finves` — link FinVes; reuses `assign_finve_to_projects` | **missing — must build** |
| VIB entry `project_ids` update endpoint | check existing |

No new data model or migration needed.

## Frontend Changes

| File | Change |
|---|---|
| `features/projects/ProjectEditFields.tsx` | NEW — extracted inner form body from `ProjectEdit.tsx` |
| `features/projects/ProjectEdit.tsx` | Refactored to use `ProjectEditFields` |
| `features/admin/NewProjectPage.tsx` | NEW — Stepper wizard |
| `shared/api/queries.ts` | Add `useCreateProject`, `useLinkFinvesToProject`; add `useProjectSearch` hook for superior project combobox |
| `router.tsx` | Register `/admin/projects/new` |

## Akzeptanzkriterien

- [ ] Step 1 creates the project; subsequent steps are skippable
- [ ] Superior project field searches existing projects by name
- [ ] Step 3 reuses `ProjectEditFields` (no duplicated form code)
- [ ] Step 4 links selected FinVes without overwriting existing links
- [ ] Step 5 adds the new project to selected VIB entries
- [ ] Wizard is only accessible to editor/admin roles
