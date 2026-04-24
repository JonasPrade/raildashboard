# VIB Entry Edit — Post-Import Editing via Drawer

**Date:** 2026-04-14
**Status:** Approved for implementation

## Problem

Confirmed VIB entries (written to `vib_entry` after "Import bestätigen") are read-only. Errors introduced by the PDF parser or AI extraction can only be corrected by deleting the entire report and re-importing. No PATCH endpoint and no edit UI exist.

Additionally, `VibSection.tsx` only displays a subset of fields — several text fields are missing from the read view entirely.

## Goal

1. Add a `PATCH /api/v1/import/vib/entries/{entry_id}` endpoint to update any field of a confirmed `VibEntry`, including its PFA children and project links.
2. Extract the existing edit form from `VibReviewPage` into a reusable `VibEntryEditForm` component.
3. Add a `VibEntryEditDrawer` that wraps the form in a Mantine `Drawer`.
4. Place an "Bearbeiten" button (editor/admin only) on every VIB entry card in `VibSection.tsx` and in `UnassignedPage.tsx`.
5. Update `VibSection.tsx` to display all fields in the read view.

---

## Design

### 1. Backend — `PATCH /api/v1/import/vib/entries/{entry_id}`

**Schema: `VibEntryUpdateSchema`** (all fields optional)

| Field | Type |
|---|---|
| `vib_name_raw` | `str \| None` |
| `category` | `str \| None` |
| `verkehrliche_zielsetzung` | `str \| None` |
| `durchgefuehrte_massnahmen` | `str \| None` |
| `noch_umzusetzende_massnahmen` | `str \| None` |
| `bauaktivitaeten` | `str \| None` |
| `teilinbetriebnahmen` | `str \| None` |
| `sonstiges` | `str \| None` |
| `raw_text` | `str \| None` |
| `strecklaenge_km` | `float \| None` |
| `gesamtkosten_mio_eur` | `float \| None` |
| `entwurfsgeschwindigkeit` | `str \| None` |
| `planungsstand` | `str \| None` |
| `status_planung` | `bool \| None` |
| `status_bau` | `bool \| None` |
| `status_abgeschlossen` | `bool \| None` |
| `pfa_entries` | `list[VibPfaEntryProposed] \| None` |
| `project_ids` | `list[int] \| None` |

**CRUD: `update_vib_entry(db, entry_id, data)`**

- Load `VibEntry` by id; 404 if not found.
- Apply all non-`None` fields from `data` to the ORM object.
- If `pfa_entries` is provided: delete all existing `VibPfaEntry` children and re-insert from the list.
- If `project_ids` is provided: delete all rows in `vib_entry_project` for this entry and re-insert.
- `db.flush()` + caller commits.
- Returns the updated `VibEntry` with `pfa_entries` and `project_ids` eager-loaded.

**Response schema: `VibEntrySchema`** — extends the existing read schema used in `VibSection`.

**Endpoint** registered in `vib_import.py` under `PATCH /entries/{entry_id}`, requires editor/admin role.

---

### 2. Frontend — Shared `VibEntryEditForm`

Extract the body of `VibEntryCard` (currently inline in `VibReviewPage.tsx`) into `apps/frontend/src/features/vib-import/VibEntryEditForm.tsx`.

Props:
```typescript
type Props = {
    entry: VibEntryProposed;
    projectOptions: { value: string; label: string }[];
    onChange: (patch: Partial<VibEntryProposed>) => void;
};
```

Handles internally: PFA add/remove/change, field change, number field change. Calls `onChange` with a patch for any mutation. Does not own save/cancel logic.

`VibReviewPage.tsx` is updated to use `VibEntryEditForm` instead of the inline `VibEntryCard` body.

---

### 3. Frontend — `VibEntryEditDrawer`

New file: `apps/frontend/src/features/vib-import/VibEntryEditDrawer.tsx`

Props:
```typescript
type Props = {
    entry: VibEntrySchema;         // confirmed entry from the DB
    opened: boolean;
    onClose: () => void;
    onSaved: (updated: VibEntrySchema) => void;
};
```

Behaviour:
- Initialises local `draft` state from `entry` (cast to `VibEntryProposed` shape).
- Renders `VibEntryEditForm` + footer with "Speichern" and "Abbrechen" buttons.
- On "Speichern": calls `PATCH /api/v1/import/vib/entries/{entry.id}` via `useUpdateVibEntry` mutation; on success calls `onSaved(updated)` and `onClose()`.
- On "Abbrechen": calls `onClose()` without saving (draft state is discarded because the drawer unmounts or re-initialises from `entry` on next open).
- Loading state on the save button during the PATCH call.

---

### 4. Frontend — `useUpdateVibEntry` mutation hook

Added to `queries.ts`:

```typescript
export function useUpdateVibEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, data }: { entryId: number; data: Partial<VibEntryProposed> }) =>
            api<VibEntrySchema>(`/api/v1/import/vib/entries/${entryId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }),
        onSuccess: (_, { entryId }) => {
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            queryClient.invalidateQueries({ queryKey: ["vib-entries", entryId] });
        },
    });
}
```

---

### 5. Frontend — Entry points

**`VibSection.tsx`**

- Each entry card gets an "Bearbeiten" `Button` (size `xs`, variant `subtle`, top-right of card header). Visible only when `user?.role === "editor" || user?.role === "admin"`.
- Clicking sets `editingEntryId` state. Renders `<VibEntryEditDrawer>` conditionally.
- `onSaved`: update the local `entries` state (or invalidate the project query so the section re-fetches).
- Read view updated to show all fields: add `verkehrliche_zielsetzung`, `durchgefuehrte_massnahmen`, `noch_umzusetzende_massnahmen`, `sonstiges`, `raw_text` (collapsible), full PFA table.

**`UnassignedPage.tsx`**

- Each VIB row gets a "Bearbeiten" button next to the existing "Zuweisen" button.
- Same `VibEntryEditDrawer` pattern.

---

### 6. Types

`VibEntrySchema` (frontend) needs to match the backend response. Add to `queries.ts` if not already present:

```typescript
export type VibEntrySchema = {
    id: number;
    vib_report_id: number;
    vib_section: string | null;
    vib_lfd_nr: string | null;
    vib_name_raw: string;
    category: string;
    raw_text: string | null;
    bauaktivitaeten: string | null;
    teilinbetriebnahmen: string | null;
    verkehrliche_zielsetzung: string | null;
    durchgefuehrte_massnahmen: string | null;
    noch_umzusetzende_massnahmen: string | null;
    sonstiges: string | null;
    strecklaenge_km: number | null;
    gesamtkosten_mio_eur: number | null;
    entwurfsgeschwindigkeit: string | null;
    planungsstand: string | null;
    status_planung: boolean;
    status_bau: boolean;
    status_abgeschlossen: boolean;
    ai_extracted: boolean;
    pfa_entries: VibPfaEntrySchema[];
    project_ids: number[];
    report_year: number;
};
```

---

## Files Changed

| File | Change |
|---|---|
| `models/vib/vib_entry.py` | No change (schema already sufficient) |
| `schemas/vib.py` | Add `VibEntryUpdateSchema`, add `sonstiges` field to `VibEntrySchema` |
| `crud/vib.py` | Add `update_vib_entry()` |
| `api/v1/endpoints/vib_import.py` | Add `PATCH /entries/{entry_id}` |
| `shared/api/queries.ts` | Add `VibEntrySchema` type, `useUpdateVibEntry` hook |
| `features/vib-import/VibEntryEditForm.tsx` | New — extracted from `VibReviewPage.tsx` |
| `features/vib-import/VibEntryEditDrawer.tsx` | New |
| `features/vib-import/VibReviewPage.tsx` | Use `VibEntryEditForm` |
| `features/projects/components/VibSection.tsx` | Add edit button + drawer, show all fields |
| `features/admin/UnassignedPage.tsx` | Add edit button + drawer |
