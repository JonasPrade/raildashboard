# VIB Entry ↔ Project: m:n Relation

**Date:** 2026-04-08
**Branch:** feature/vib-import
**Status:** Approved for implementation

## Problem

A single VIB Vorhaben (entry) can span multiple rail projects (e.g. a shared corridor section touching two separate DB Netz projects). The current `vib_entry.project_id` FK allows only one project per entry, so shared entries can only appear in one project's detail view.

## Goal

Allow a `VibEntry` to be linked to zero or more projects, and appear in each linked project's detail view.

---

## Design

### 1. Database & Model Layer

**New association table** `vib_entry_project`:

| Column         | Type    | Constraints                                  |
|---------------|---------|----------------------------------------------|
| `vib_entry_id` | INTEGER | PK, FK → `vib_entry.id` ON DELETE CASCADE    |
| `project_id`   | INTEGER | PK, FK → `project.id` ON DELETE CASCADE      |

Composite PK `(vib_entry_id, project_id)`.

**`VibEntry` model changes:**
- Remove `project_id = Column(Integer, ForeignKey("project.id"), ...)`
- Remove `project = relationship("Project", foreign_keys=[project_id])`
- Add `projects = relationship("Project", secondary="vib_entry_project", backref="vib_entries")`

**Alembic migration** (`20260408001_vib_entry_project_m2n.py`):
1. Create `vib_entry_project` table
2. Migrate existing data: `INSERT INTO vib_entry_project (vib_entry_id, project_id) SELECT id, project_id FROM vib_entry WHERE project_id IS NOT NULL`
3. Drop `vib_entry.project_id` column

### 2. Pydantic Schemas (`schemas/vib.py`)

**`VibEntryProposed`:**
- Remove `project_id: Optional[int] = None`
- Add `project_ids: list[int] = []`
- Keep `suggested_project_ids: list[int] = []` unchanged (already a list, used as hints)

**`VibConfirmEntryInput`:**
- Remove `project_id: Optional[int] = None`
- Add `project_ids: list[int] = []`

No changes to `VibEntryForProjectSchema` — it's queried by project and doesn't need to carry the project list.

### 3. CRUD Layer (`crud/vib.py`)

**`create_vib_report_with_entries`:**
- Remove `project_id=entry_data.project_id` from `VibEntry(...)` constructor
- After `db.flush()` for each entry, bulk-insert rows into `vib_entry_project` for each id in `entry_data.project_ids`

**`get_vib_entries_for_project`:**
- Replace `.filter(VibEntry.project_id == project_id)` with a join through the association table:
  ```python
  .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
  .filter(vib_entry_project.c.project_id == project_id)
  ```

### 4. API Endpoints

No new endpoints. Changes propagate automatically from schema updates:

- `POST /vib/confirm` — `VibConfirmRequest` → `VibConfirmEntryInput` now carries `project_ids: list[int]`
- `GET /projects/{id}/vib` — `get_vib_entries_for_project` query updated internally, response schema unchanged

### 5. Frontend

**`queries.ts`:**
- `VibEntryProposed`: change `project_id: number | null` → `project_ids: number[]`
- `VibConfirmEntryInput`: already derived as `Omit<VibEntryProposed, "suggested_project_ids">` — picks up `project_ids` automatically

**`VibReviewPage.tsx`:**
- `onProjectChange` prop: `(projectId: number | null) => void` → `(projectIds: number[]) => void`
- Replace `<Select>` with `<MultiSelect>` for project assignment per entry
- Update `updateCurrentEntry({ project_id: ... })` → `updateCurrentEntry({ project_ids: [...] })`
- Confidence/suggestion logic:
  - `hasSuggestion`: `entry.project_ids.length > 0 || entry.suggested_project_ids.length > 0`
  - `confidence "high"`: `entry.suggested_project_ids.some(id => entry.project_ids.includes(id))`
  - `confidence "manual"`: `entry.project_ids.length > 0` and no overlap with suggestions
  - `confidence "none"`: `entry.project_ids.length === 0`
- `matchedCount`: `displayEntries.filter(e => e.project_ids.length > 0).length`
- Confirm payload: strip `suggested_project_ids` via existing `Omit` — no change needed

**`VibSection.tsx`:** No changes — queries by project, unaffected by schema.

---

## Migration Safety

- Existing data is preserved: the migration copies `project_id` into the association table before dropping the column.
- Entries with `project_id = NULL` get no rows in `vib_entry_project` (equivalent to unlinked — correct).
- No data loss possible.

---

## Out of Scope

- Showing sibling projects on a VIB entry in the project detail view (future nice-to-have)
- Per-link metadata (notes, primary flag) — YAGNI
