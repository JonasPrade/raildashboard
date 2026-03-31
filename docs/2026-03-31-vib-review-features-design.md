# VIB Review Features — Design Spec
_Date: 2026-03-31_

## Scope

Three additions to the VIB import pipeline:

1. **Planungsstand extraction** — parse a new text field from the VIB PDF and store/display it
2. **Project status (Planung / Bau)** — user-settable status per VIB entry in the review UI
3. **Card navigation in VIB-Review** — replace table with single-card view, navigable with arrows

---

## Feature 1 — Planungsstand Extraction

### Backend

**Model** (`models/vib/vib_entry.py`):
- Add `planungsstand = Column(Text, nullable=True)` to `VibEntry`

**Migration** (`alembic/versions/`):
- Single migration adds both `planungsstand` and `project_status` (see Feature 2)

**Parser** (`tasks/vib.py`):
- Extract label `Planungsstand:` from accumulated raw text, same pattern used for `Bauaktivitäten:` and `Teilinbetriebnahmen:`
- Store result in `planungsstand` field of the parsed entry

**Schemas** (`schemas/vib.py`):
- `VibEntryProposed`: add `planungsstand: Optional[str] = None`
- `VibConfirmEntryInput`: add `planungsstand: Optional[str] = None`
- `VibEntryForProjectSchema`: add `planungsstand: Optional[str] = None`

**CRUD** (`crud/vib.py`):
- Pass `planungsstand` when creating `VibEntry` from confirmed data

### Frontend

**VibReviewPage** — expanded row section:
- Add `Planungsstand` text block (same pattern as Bauaktivitäten)

**VibSection.tsx** — tab content:
- Add `Planungsstand` block below Kenndaten, above Bauaktivitäten

---

## Feature 2 — Project Status (Planung / Bau)

### Backend

**Model** (`models/vib/vib_entry.py`):
- Add `project_status = Column(String(20), nullable=True)` — values: `"Planung"` | `"Bau"` | `null`

**Migration**: combined with Feature 1 migration

**Schemas**:
- `VibEntryProposed`: add `project_status: Optional[str] = None`
- `VibConfirmEntryInput`: add `project_status: Optional[str] = None`
- `VibEntryForProjectSchema`: add `project_status: Optional[str] = None`

**CRUD**: pass `project_status` when creating `VibEntry`

### Frontend

**VibReviewPage** (card view, see Feature 3):
- `Select` with options `[{value: "Planung", label: "Planung"}, {value: "Bau", label: "Bau"}]`, clearable
- State managed identically to `project_id` — per-entry in local entries array

**VibSection.tsx**:
- Show as `Badge` next to category badge (`color="orange"` for Planung, `color="cyan"` for Bau)

---

## Feature 3 — Card Navigation in VIB-Review

### Layout

Replace the `<Table>` in `VibReviewPage` with a single-card view:

**Top navigation bar** (sticky or at top of content area):
```
[←]  3 / 42  [→]   |  ABS Lübeck–Rostock… [laufend]   |  [Import bestätigen]
```
- Arrow buttons: `ActionIcon` with chevron icons, disabled at boundaries
- Entry count: `Text` showing `{currentIndex + 1} / {total}`
- Entry name + category badge: compact header
- Match count `{matched}/{total} zugeordnet` + Confirm button stay in top-right (same as now)

**Card body** — full width `Paper`/`Card` with `Stack`:
1. `vib_section` monospace label
2. Kenndaten row: Länge, Gesamtkosten, Vmax (if present)
3. **Planungsstand** block (Feature 1)
4. Project mapping `Select` + confidence badge (moved from table column)
5. **Project status** `Select` — Planung / Bau (Feature 2)
6. Bauaktivitäten block
7. Teilinbetriebnahmen block
8. PFA-Tabelle (collapsible, same as current expanded row)
9. Volltext (collapsible)

### State

- `currentIndex: number` (useState, default 0)
- `entries: VibEntryProposed[]` — same array as today, mutations at index still work
- No functional change to confirm logic

### Keyboard (optional, nice-to-have — skip if time-constrained)
- Left/Right arrow keys to navigate (document-level keydown listener)

---

## Data Flow Summary

```
PDF upload
  → parse_vib_pdf (Celery)
      → extracts planungsstand per entry
  → VibReviewPage loads VibParseTaskResult
      → user navigates cards, sets project_id, project_status per entry
  → POST /confirm
      → VibEntry created with planungsstand + project_status
  → VibSection.tsx displays planungsstand + project_status badge
```

---

## Migration

Single Alembic migration file (`20260331001_add_planungsstand_project_status_to_vib_entry.py`):
```sql
ALTER TABLE vib_entry ADD COLUMN planungsstand TEXT;
ALTER TABLE vib_entry ADD COLUMN project_status VARCHAR(20);
```

---

## Files Changed

| File | Change |
|------|--------|
| `models/vib/vib_entry.py` | +2 columns |
| `alembic/versions/20260331001_...py` | new migration |
| `tasks/vib.py` | extract planungsstand |
| `schemas/vib.py` | +2 fields on 3 schemas |
| `crud/vib.py` | pass new fields on create |
| `VibReviewPage.tsx` | replace table → card navigation |
| `VibSection.tsx` | display planungsstand + project_status |

`make gen-api` must be run after backend changes.
