# New Project Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A 5-step admin wizard at `/admin/projects/new` to create a new project (Stammdaten) and optionally attach geometry, properties, FinVe links, and VIB-entry links — all skippable after step 1.

**Architecture:**
- Backend: three new endpoints (`POST /api/v1/projects`, `POST /api/v1/projects/{id}/finves`, `GET /api/v1/import/vib/entries`) plus one new CRUD helper. No data-model changes.
- Frontend: new `NewProjectPage` using Mantine `Stepper`, per-step submits (project is persisted after Step 1 so later steps use `PATCH` or link endpoints). Extract `ProjectEditFields` from `ProjectEdit.tsx` to share form body with Step 3.

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic (backend); React + TypeScript + Mantine + React Query (frontend); pytest + vitest for tests.

**Spec:** `docs/features/feature-new-project-wizard.md`.

---

## File Structure

**Backend — create:**
- `apps/backend/dashboard_backend/schemas/projects/project_create_schema.py` — `ProjectCreate` (name required, other fields optional; same field set as `ProjectUpdate`).
- `apps/backend/dashboard_backend/schemas/projects/link_finves_schema.py` — `LinkFinvesInput { finve_ids: list[int] }`.

**Backend — modify:**
- `apps/backend/dashboard_backend/crud/projects/projects.py` — add `create_project(db, data: dict) -> Project`.
- `apps/backend/dashboard_backend/api/v1/endpoints/projects.py` — add `POST /` and `POST /{id}/finves`.
- `apps/backend/dashboard_backend/api/v1/endpoints/vib_import.py` — add `GET /entries` (list confirmed VIB entries).
- `apps/backend/dashboard_backend/schemas/vib.py` — add `VibEntryListItemSchema` (lean list item).
- `apps/backend/tests/api/test_projects.py` — add tests for POST and POST finves.
- `apps/backend/tests/api/test_vib_import.py` — add one test for GET entries.

**Frontend — create:**
- `apps/frontend/src/features/projects/ProjectEditFields.tsx` — extracted form body.
- `apps/frontend/src/features/projects/ProjectSearchSelect.tsx` — superior-project combobox.
- `apps/frontend/src/features/admin/new-project/NewProjectPage.tsx` — Stepper shell.
- `apps/frontend/src/features/admin/new-project/Step1Stammdaten.tsx`
- `apps/frontend/src/features/admin/new-project/Step2Geometrie.tsx`
- `apps/frontend/src/features/admin/new-project/Step3Properties.tsx`
- `apps/frontend/src/features/admin/new-project/Step4Finves.tsx`
- `apps/frontend/src/features/admin/new-project/Step5Vib.tsx`

**Frontend — modify:**
- `apps/frontend/src/features/projects/ProjectEdit.tsx` — replace inline form body with `<ProjectEditFields>`.
- `apps/frontend/src/shared/api/queries.ts` — add `useCreateProject`, `useLinkFinvesToProject`, `useConfirmedVibEntries`, and a light helper to PATCH VIB entry project_ids.
- `apps/frontend/src/router.tsx` — register `/admin/projects/new`.
- `apps/frontend/src/features/admin/UnassignedPage.tsx` — add "Neues Projekt anlegen" button at the top.
- `apps/frontend/src/shared/api/types.gen.ts` — regenerated via `make gen-api` (do not edit by hand).
- `docs/roadmap.md` — tick the wizard box.

---

## Task 1: Backend — `POST /api/v1/projects` + `ProjectCreate` schema + `create_project` CRUD

**Files:**
- Create: `apps/backend/dashboard_backend/schemas/projects/project_create_schema.py`
- Modify: `apps/backend/dashboard_backend/crud/projects/projects.py`
- Modify: `apps/backend/dashboard_backend/api/v1/endpoints/projects.py`
- Test: `apps/backend/tests/api/test_projects.py`

- [ ] **Step 1: Create `ProjectCreate` schema**

`apps/backend/dashboard_backend/schemas/projects/project_create_schema.py`:

```python
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Create schema for Project. `name` is the only required field."""

    name: str = Field(min_length=1)
    project_number: Optional[str] = None
    description: Optional[str] = None
    justification: Optional[str] = None
    superior_project_id: Optional[int] = None

    length: Optional[float] = None

    # Project-property booleans / ints (mirrors ProjectUpdate — all optional, default None).
    effects_passenger_long_rail: Optional[bool] = None
    effects_passenger_local_rail: Optional[bool] = None
    effects_cargo_rail: Optional[bool] = None
    nbs: Optional[bool] = None
    abs: Optional[bool] = None
    elektrification: Optional[bool] = None
    charging_station: Optional[bool] = None
    small_charging_station: Optional[bool] = None
    second_track: Optional[bool] = None
    third_track: Optional[bool] = None
    fourth_track: Optional[bool] = None
    curve: Optional[bool] = None
    platform: Optional[bool] = None
    junction_station: Optional[bool] = None
    number_junction_station: Optional[int] = None
    overtaking_station: Optional[bool] = None
    number_overtaking_station: Optional[int] = None
    double_occupancy: Optional[bool] = None
    block_increase: Optional[bool] = None
    flying_junction: Optional[bool] = None
    tunnel_structural_gauge: Optional[bool] = None
    increase_speed: Optional[bool] = None
    new_vmax: Optional[int] = None
    level_free_platform_entrance: Optional[bool] = None
    etcs: Optional[bool] = None
    etcs_level: Optional[int] = None
    station_railroad_switches: Optional[bool] = None
    new_station: Optional[bool] = None
    depot: Optional[bool] = None
    battery: Optional[bool] = None
    h2: Optional[bool] = None
    efuel: Optional[bool] = None
    closure: Optional[bool] = None
    optimised_electrification: Optional[bool] = None
    filling_stations_efuel: Optional[bool] = None
    filling_stations_h2: Optional[bool] = None
    filling_stations_diesel: Optional[bool] = None
    filling_stations_count: Optional[int] = None
    sanierung: Optional[bool] = None
    sgv740m: Optional[bool] = None
    railroad_crossing: Optional[bool] = None
    new_estw: Optional[bool] = None
    new_dstw: Optional[bool] = None
    noise_barrier: Optional[bool] = None
    overpass: Optional[bool] = None
    buffer_track: Optional[bool] = None
    gwb: Optional[bool] = None
    simultaneous_train_entries: Optional[bool] = None
    tilting: Optional[bool] = None

    project_group_ids: Optional[List[int]] = None
```

- [ ] **Step 2: Add `create_project` to CRUD**

Open `apps/backend/dashboard_backend/crud/projects/projects.py` and append:

```python
def create_project(db: Session, data: dict) -> Project:
    """Create a new project. `project_group_ids` is handled separately."""
    data = dict(data)
    group_ids = data.pop("project_group_ids", None)

    # Drop keys whose value is None to let the DB use its defaults.
    filtered = {k: v for k, v in data.items() if v is not None}

    project = Project(**filtered)
    if group_ids:
        project.project_groups = (
            db.query(ProjectGroup).filter(ProjectGroup.id.in_(group_ids)).all()
        )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
```

Verify `ProjectGroup` is already imported at top of the file; add it if not.

- [ ] **Step 3: Write failing tests**

Add to `apps/backend/tests/api/test_projects.py`:

```python
def test_create_project_success(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    created = _make_project(42, "Wizard Project")
    captured = {}

    def fake_create(db, data):
        captured.update(data)
        return created

    monkeypatch.setattr(projects_route, "create_project", fake_create)

    resp = client.post(
        "/api/v1/projects",
        json={"name": "Wizard Project", "project_number": "1-042"},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 42
    assert body["name"] == "Wizard Project"
    assert captured["name"] == "Wizard Project"
    assert captured["project_number"] == "1-042"


def test_create_project_requires_editor(client, create_user):
    create_user("viewer", "pass123", UserRole.viewer)
    resp = client.post(
        "/api/v1/projects",
        json={"name": "X"},
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 403


def test_create_project_rejects_empty_name(client, create_user):
    create_user("editor", "pass123", UserRole.editor)
    resp = client.post(
        "/api/v1/projects",
        json={"name": ""},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 422
```

- [ ] **Step 4: Run tests to verify they fail**

```
cd apps/backend && .venv/bin/python -m pytest tests/api/test_projects.py -k create_project -v
```
Expected: three failures (route not registered → 405/404).

- [ ] **Step 5: Implement endpoint**

Open `apps/backend/dashboard_backend/api/v1/endpoints/projects.py`. Add import:

```python
from dashboard_backend.schemas.projects.project_create_schema import ProjectCreate
from dashboard_backend.crud.projects.projects import create_project
```

Append a route (near the top, before the `{project_id}` routes to keep ordering clean):

```python
@router.post("/", response_model=ProjectSchema, status_code=201)
def create_project_endpoint(
    body: ProjectCreate,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    project = create_project(db, body.model_dump(exclude_unset=True))
    return project
```

- [ ] **Step 6: Run tests again**

```
cd apps/backend && .venv/bin/python -m pytest tests/api/test_projects.py -k create_project -v
```
Expected: PASS.

- [ ] **Step 7: Commit**

```
git add apps/backend/dashboard_backend/schemas/projects/project_create_schema.py \
        apps/backend/dashboard_backend/crud/projects/projects.py \
        apps/backend/dashboard_backend/api/v1/endpoints/projects.py \
        apps/backend/tests/api/test_projects.py
git commit -m "feat(projects): add POST /api/v1/projects endpoint"
```

---

## Task 2: Backend — `POST /api/v1/projects/{id}/finves`

**Files:**
- Create: `apps/backend/dashboard_backend/schemas/projects/link_finves_schema.py`
- Modify: `apps/backend/dashboard_backend/api/v1/endpoints/projects.py`
- Test: `apps/backend/tests/api/test_projects.py`

- [ ] **Step 1: Create input schema**

`apps/backend/dashboard_backend/schemas/projects/link_finves_schema.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class LinkFinvesInput(BaseModel):
    finve_ids: list[int] = Field(default_factory=list)
```

- [ ] **Step 2: Write failing tests**

Add to `test_projects.py`:

```python
def test_link_finves_to_project_success(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    calls = []

    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))
    monkeypatch.setattr(
        projects_route,
        "assign_finve_to_projects",
        lambda db, finve_id, project_ids: calls.append((finve_id, tuple(project_ids))),
    )

    resp = client.post(
        "/api/v1/projects/7/finves",
        json={"finve_ids": [11, 12]},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 204
    assert calls == [(11, (7,)), (12, (7,))]


def test_link_finves_to_project_404(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: None)
    resp = client.post(
        "/api/v1/projects/999/finves",
        json={"finve_ids": [1]},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 404
```

- [ ] **Step 3: Run tests to confirm they fail**

```
cd apps/backend && .venv/bin/python -m pytest tests/api/test_projects.py -k link_finves -v
```

- [ ] **Step 4: Implement endpoint**

In `projects.py` add imports:

```python
from dashboard_backend.crud.admin_assignments import assign_finve_to_projects
from dashboard_backend.schemas.projects.link_finves_schema import LinkFinvesInput
```

Add the route:

```python
@router.post("/{project_id}/finves", status_code=204)
def link_finves_to_project(
    project_id: int,
    body: LinkFinvesInput,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for finve_id in body.finve_ids:
        assign_finve_to_projects(db, finve_id, [project_id])
    db.commit()
    return None
```

- [ ] **Step 5: Run tests to verify green**

```
cd apps/backend && .venv/bin/python -m pytest tests/api/test_projects.py -k link_finves -v
```

- [ ] **Step 6: Commit**

```
git add apps/backend/dashboard_backend/schemas/projects/link_finves_schema.py \
        apps/backend/dashboard_backend/api/v1/endpoints/projects.py \
        apps/backend/tests/api/test_projects.py
git commit -m "feat(projects): add POST /projects/{id}/finves to link FinVes"
```

---

## Task 3: Backend — `GET /api/v1/import/vib/entries`

**Files:**
- Modify: `apps/backend/dashboard_backend/schemas/vib.py`
- Modify: `apps/backend/dashboard_backend/api/v1/endpoints/vib_import.py`
- Test: `apps/backend/tests/api/test_vib_import.py`

- [ ] **Step 1: Add list-item schema**

Add to `schemas/vib.py`:

```python
class VibEntryListItemSchema(BaseModel):
    id: int
    vib_name_raw: Optional[str]
    report_year: int
    project_ids: list[int]
    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Write failing test**

Add to `tests/api/test_vib_import.py` (create the file if it does not exist — use `test_projects.py`'s imports as template):

```python
def test_list_confirmed_vib_entries(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)

    fake_entries = [
        SimpleNamespace(id=1, vib_name_raw="Projekt A", report=SimpleNamespace(year=2024),
                        projects=[SimpleNamespace(id=10)]),
        SimpleNamespace(id=2, vib_name_raw="Projekt B", report=SimpleNamespace(year=2024),
                        projects=[]),
    ]
    monkeypatch.setattr(vib_import_route, "list_confirmed_vib_entries",
                        lambda db: fake_entries)

    resp = client.get(
        "/api/v1/import/vib/entries",
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["id"] == 1
    assert body[0]["project_ids"] == [10]
    assert body[1]["project_ids"] == []
```

Include at top of file:

```python
from types import SimpleNamespace
from dashboard_backend.api.v1.endpoints import vib_import as vib_import_route
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header  # or import the helper path used in test_projects.py
```

- [ ] **Step 3: Run test (expect fail)**

```
cd apps/backend && .venv/bin/python -m pytest tests/api/test_vib_import.py -k list_confirmed -v
```

- [ ] **Step 4: Implement endpoint**

In `vib_import.py` add a thin CRUD helper (inline is fine):

```python
def list_confirmed_vib_entries(db: Session):
    from dashboard_backend.models.vib.vib_entry import VibEntry
    return (
        db.query(VibEntry)
        .options(joinedload(VibEntry.report), joinedload(VibEntry.projects))
        .order_by(VibEntry.id.desc())
        .all()
    )
```

(Place the function near the other helpers in this file; reuse existing imports if `joinedload` is already imported.)

Then add the route, right before the `GET /entries/{entry_id}` route:

```python
@router.get("/entries", response_model=list[VibEntryListItemSchema])
def list_vib_entries(db: Session = Depends(get_db)):
    entries = list_confirmed_vib_entries(db)
    return [
        VibEntryListItemSchema(
            id=e.id,
            vib_name_raw=e.vib_name_raw,
            report_year=e.report.year,
            project_ids=[p.id for p in e.projects],
        )
        for e in entries
    ]
```

Add the schema import at the top:
```python
from dashboard_backend.schemas.vib import VibEntryListItemSchema
```
(Likely already pulled in — check.)

- [ ] **Step 5: Run test (expect pass)**

```
cd apps/backend && .venv/bin/python -m pytest tests/api/test_vib_import.py -k list_confirmed -v
```

- [ ] **Step 6: Commit**

```
git add apps/backend/dashboard_backend/schemas/vib.py \
        apps/backend/dashboard_backend/api/v1/endpoints/vib_import.py \
        apps/backend/tests/api/test_vib_import.py
git commit -m "feat(vib): add GET /import/vib/entries to list confirmed entries"
```

---

## Task 4: Run `make gen-api`

- [ ] **Step 1: Regenerate types**

```
make gen-api
```

- [ ] **Step 2: Verify the diff**

```
git diff apps/frontend/src/shared/api/types.gen.ts
```

Expected new entries: `ProjectCreate` schema, `LinkFinvesInput`, `VibEntryListItemSchema`, and the new paths under `paths["/api/v1/projects/"]`, `paths["/api/v1/projects/{project_id}/finves"]`, and `paths["/api/v1/import/vib/entries"]`.

- [ ] **Step 3: Commit the regenerated client**

```
git add apps/frontend/src/shared/api/types.gen.ts
git commit -m "chore(api): regenerate frontend types for new project endpoints"
```

---

## Task 5: Frontend — Extract `ProjectEditFields`

**Files:**
- Create: `apps/frontend/src/features/projects/ProjectEditFields.tsx`
- Modify: `apps/frontend/src/features/projects/ProjectEdit.tsx`

- [ ] **Step 1: Create the component**

`apps/frontend/src/features/projects/ProjectEditFields.tsx`:

```tsx
import { Stack, Divider, TextInput, Textarea, NumberInput, Switch, MultiSelect, Group } from "@mantine/core";
import type { ProjectEditFormValues } from "./ProjectEdit";

type Props = {
    values: ProjectEditFormValues;
    setValues: (updater: (prev: ProjectEditFormValues) => ProjectEditFormValues) => void;
    projectGroupOptions: { value: string; label: string }[];
};

function SwitchField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
    return <Switch label={label} checked={checked} onChange={(e) => onChange(e.currentTarget.checked)} />;
}

export function ProjectEditFields({ values, setValues, projectGroupOptions }: Props) {
    const set = <K extends keyof ProjectEditFormValues>(key: K, value: ProjectEditFormValues[K]) =>
        setValues((prev) => ({ ...prev, [key]: value }));

    return (
        <Stack gap="md">
            {/* Move the body of ProjectEdit.tsx (from <Divider label="Stammdaten" /> through the end of the form) here,
                replacing every `form.getInputProps(...)` and direct state setter with set("field", value). */}
        </Stack>
    );
}
```

Then copy the JSX sections from `ProjectEdit.tsx` verbatim into this body, converting state writes to `set(key, value)`. Keep the `SwitchField` helper local to this file. Keep section order identical (Stammdaten, Verkehrsarten, Streckenausbau, Bahnhöfe, Signaltechnik, Elektrifizierung, Sonstiges).

Exports needed: `ProjectEditFields`, and re-export `ProjectEditFormValues` from `ProjectEdit.tsx` (or move the type here if cleaner — decide while editing).

- [ ] **Step 2: Update `ProjectEdit.tsx` to use it**

Replace the extracted JSX in `ProjectEdit.tsx` with `<ProjectEditFields values={values} setValues={setValues} projectGroupOptions={projectGroupOptions} />`. Keep `createInitialValues`, `createUpdatePayload`, and the Drawer shell unchanged.

- [ ] **Step 3: Verify build**

```
cd apps/frontend && pnpm run type-check
```
Expected: no type errors.

- [ ] **Step 4: Smoke-test the drawer in the dev server**

Start the frontend (`pnpm dev`), open an existing project, click "Bearbeiten" → confirm every section renders correctly and edits save. Fix any regression before proceeding.

- [ ] **Step 5: Commit**

```
git add apps/frontend/src/features/projects/ProjectEditFields.tsx \
        apps/frontend/src/features/projects/ProjectEdit.tsx
git commit -m "refactor(projects): extract ProjectEditFields for wizard reuse"
```

---

## Task 6: Frontend — Wizard hooks in `queries.ts`

**Files:**
- Modify: `apps/frontend/src/shared/api/queries.ts`

- [ ] **Step 1: Add `useCreateProject`**

Near the other project hooks:

```ts
export type ProjectCreatePayload = {
    name: string;
    project_number?: string | null;
    description?: string | null;
    justification?: string | null;
    superior_project_id?: number | null;
    project_group_ids?: number[];
};

export function useCreateProject() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: ProjectCreatePayload) =>
            api<Project>("/api/v1/projects", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: (newProject) => {
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            if (newProject.id != null) {
                queryClient.setQueryData(["project", newProject.id], newProject);
            }
        },
    });
}
```

- [ ] **Step 2: Add `useLinkFinvesToProject`**

```ts
export function useLinkFinvesToProject(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (finveIds: number[]) =>
            api<void>(`/api/v1/projects/${projectId}/finves`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ finve_ids: finveIds }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["project", projectId, "finves"] });
            queryClient.invalidateQueries({ queryKey: ["finves"] });
            queryClient.invalidateQueries({ queryKey: ["admin-unassigned-finves"] });
        },
    });
}
```

- [ ] **Step 3: Add `useConfirmedVibEntries`**

```ts
export type ConfirmedVibEntry = {
    id: number;
    vib_name_raw: string | null;
    report_year: number;
    project_ids: number[];
};

export function useConfirmedVibEntries(enabled = true) {
    return useQuery({
        queryKey: ["vib-entries-confirmed"],
        queryFn: () => api<ConfirmedVibEntry[]>("/api/v1/import/vib/entries"),
        enabled,
    });
}
```

- [ ] **Step 4: Type-check**

```
cd apps/frontend && pnpm run type-check
```

- [ ] **Step 5: Commit**

```
git add apps/frontend/src/shared/api/queries.ts
git commit -m "feat(frontend): add wizard hooks (create project, link finves, list VIB entries)"
```

---

## Task 7: Frontend — `ProjectSearchSelect` (superior-project combobox)

**Files:**
- Create: `apps/frontend/src/features/projects/ProjectSearchSelect.tsx`

- [ ] **Step 1: Build the component**

```tsx
import { Combobox, InputBase, Loader, Text, useCombobox } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useMemo, useState } from "react";
import { useProjects } from "../../shared/api/queries";

type Props = {
    label: string;
    value: number | null;
    onChange: (id: number | null) => void;
    excludeId?: number;
};

export default function ProjectSearchSelect({ label, value, onChange, excludeId }: Props) {
    const [query, setQuery] = useState("");
    const [debounced] = useDebouncedValue(query, 200);
    const combobox = useCombobox({ onDropdownClose: () => combobox.resetSelectedOption() });
    const { data: projects = [], isFetching } = useProjects();

    const selectedProject = useMemo(
        () => (value == null ? null : projects.find((p) => p.id === value) ?? null),
        [projects, value],
    );

    const filtered = useMemo(() => {
        const q = debounced.trim().toLowerCase();
        return projects
            .filter((p) => p.id !== excludeId)
            .filter((p) => {
                if (!q) return true;
                return (
                    (p.name ?? "").toLowerCase().includes(q) ||
                    (p.project_number ?? "").toLowerCase().includes(q)
                );
            })
            .slice(0, 20);
    }, [projects, debounced, excludeId]);

    return (
        <Combobox
            store={combobox}
            onOptionSubmit={(val) => {
                const id = Number(val);
                onChange(Number.isNaN(id) ? null : id);
                setQuery("");
                combobox.closeDropdown();
            }}
        >
            <Combobox.Target>
                <InputBase
                    label={label}
                    placeholder="Projekt suchen…"
                    value={query || selectedProject?.name || ""}
                    onFocus={() => combobox.openDropdown()}
                    onBlur={() => combobox.closeDropdown()}
                    onChange={(e) => {
                        setQuery(e.currentTarget.value);
                        if (!e.currentTarget.value) onChange(null);
                        combobox.openDropdown();
                    }}
                    rightSection={isFetching ? <Loader size="xs" /> : <Combobox.Chevron />}
                    rightSectionPointerEvents="none"
                />
            </Combobox.Target>
            <Combobox.Dropdown>
                <Combobox.Options>
                    {filtered.length === 0 ? (
                        <Combobox.Empty>Keine Treffer</Combobox.Empty>
                    ) : (
                        filtered.map((p) => (
                            <Combobox.Option key={p.id} value={String(p.id)}>
                                <Text size="sm" fw={500}>{p.name}</Text>
                                {p.project_number && (
                                    <Text size="xs" c="dimmed">{p.project_number}</Text>
                                )}
                            </Combobox.Option>
                        ))
                    )}
                </Combobox.Options>
            </Combobox.Dropdown>
        </Combobox>
    );
}
```

- [ ] **Step 2: Type-check**

```
cd apps/frontend && pnpm run type-check
```

- [ ] **Step 3: Commit**

```
git add apps/frontend/src/features/projects/ProjectSearchSelect.tsx
git commit -m "feat(projects): add ProjectSearchSelect combobox for wizard"
```

---

## Task 8: Frontend — `NewProjectPage` + Step 1 (Stammdaten) + route

**Files:**
- Create: `apps/frontend/src/features/admin/new-project/NewProjectPage.tsx`
- Create: `apps/frontend/src/features/admin/new-project/Step1Stammdaten.tsx`
- Modify: `apps/frontend/src/router.tsx`

- [ ] **Step 1: Step 1 form component**

`Step1Stammdaten.tsx`:

```tsx
import { Button, Group, MultiSelect, Stack, TextInput, Textarea } from "@mantine/core";
import { useMemo, useState } from "react";
import { useCreateProject, useProjectGroups, type ProjectCreatePayload, type Project } from "../../../shared/api/queries";
import ProjectSearchSelect from "../../projects/ProjectSearchSelect";

type Props = {
    onCreated: (project: Project) => void;
};

export default function Step1Stammdaten({ onCreated }: Props) {
    const createProject = useCreateProject();
    const { data: groups = [] } = useProjectGroups();
    const [name, setName] = useState("");
    const [projectNumber, setProjectNumber] = useState("");
    const [description, setDescription] = useState("");
    const [justification, setJustification] = useState("");
    const [superiorId, setSuperiorId] = useState<number | null>(null);
    const [groupIds, setGroupIds] = useState<string[]>([]);

    const groupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
    );

    const disabled = name.trim().length === 0 || createProject.isPending;

    const handleSubmit = async () => {
        const payload: ProjectCreatePayload = {
            name: name.trim(),
            project_number: projectNumber || null,
            description: description || null,
            justification: justification || null,
            superior_project_id: superiorId,
            project_group_ids: groupIds.map(Number),
        };
        const created = await createProject.mutateAsync(payload);
        onCreated(created);
    };

    return (
        <Stack gap="md">
            <TextInput label="Name" required value={name} onChange={(e) => setName(e.currentTarget.value)} />
            <TextInput label="Projektnummer" value={projectNumber} onChange={(e) => setProjectNumber(e.currentTarget.value)} />
            <Textarea label="Beschreibung" autosize minRows={3} value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
            <Textarea label="Begründung" autosize minRows={3} value={justification} onChange={(e) => setJustification(e.currentTarget.value)} />
            <ProjectSearchSelect label="Übergeordnetes Projekt" value={superiorId} onChange={setSuperiorId} />
            <MultiSelect label="Projektgruppen" data={groupOptions} value={groupIds} onChange={setGroupIds} searchable clearable />
            <Group justify="flex-end">
                <Button onClick={handleSubmit} disabled={disabled} loading={createProject.isPending}>
                    Projekt anlegen
                </Button>
            </Group>
        </Stack>
    );
}
```

Check that `useProjectGroups` exists in `queries.ts`; if it's named differently (e.g. `useListProjectGroups`), use that name.

- [ ] **Step 2: Stepper shell**

`NewProjectPage.tsx`:

```tsx
import { Alert, Button, Container, Group, Stack, Stepper, Title } from "@mantine/core";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../lib/auth";
import type { Project } from "../../../shared/api/queries";
import Step1Stammdaten from "./Step1Stammdaten";

export default function NewProjectPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [active, setActive] = useState(0);
    const [project, setProject] = useState<Project | null>(null);

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    const handleFinish = () => {
        if (project?.id != null) navigate(`/projects/${project.id}`);
        else navigate("/admin/unassigned");
    };

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Title order={2}>Neues Projekt anlegen</Title>
                <Stepper active={active} allowNextStepsSelect={false}>
                    <Stepper.Step label="Stammdaten" description="Pflicht">
                        <Step1Stammdaten
                            onCreated={(p) => {
                                setProject(p);
                                setActive(1);
                            }}
                        />
                    </Stepper.Step>
                    <Stepper.Step label="Geometrie" description="Optional">
                        <Stack><div>Schritt 2 folgt in Task 9.</div></Stack>
                    </Stepper.Step>
                    <Stepper.Step label="Eigenschaften" description="Optional">
                        <Stack><div>Schritt 3 folgt in Task 10.</div></Stack>
                    </Stepper.Step>
                    <Stepper.Step label="FinVes" description="Optional">
                        <Stack><div>Schritt 4 folgt in Task 11.</div></Stack>
                    </Stepper.Step>
                    <Stepper.Step label="VIB" description="Optional">
                        <Stack><div>Schritt 5 folgt in Task 12.</div></Stack>
                    </Stepper.Step>
                    <Stepper.Completed>
                        <div>Projekt angelegt. Du wirst weitergeleitet.</div>
                    </Stepper.Completed>
                </Stepper>
                {project && (
                    <Group justify="space-between">
                        <Button variant="subtle" onClick={() => setActive((s) => Math.max(0, s - 1))} disabled={active === 0}>
                            Zurück
                        </Button>
                        <Group>
                            <Button variant="subtle" onClick={() => setActive((s) => s + 1)} disabled={active >= 4}>
                                Überspringen
                            </Button>
                            <Button onClick={handleFinish}>Fertig</Button>
                        </Group>
                    </Group>
                )}
            </Stack>
        </Container>
    );
}
```

- [ ] **Step 3: Register route**

In `apps/frontend/src/router.tsx`, inside the `children` array of the root `"/"` route:

```tsx
{
    path: "admin/projects/new",
    element: (
        <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
            <NewProjectPage />
        </Suspense>
    ),
},
```

Add the lazy import alongside the others at the top of the file:

```tsx
const NewProjectPage = lazy(() => import("./features/admin/new-project/NewProjectPage"));
```

- [ ] **Step 4: Smoke test**

Start `pnpm dev`, log in as an editor, navigate to `/admin/projects/new`, fill the name and click "Projekt anlegen". Verify:
- A POST /api/v1/projects hits the backend (check network tab and server logs).
- After success, Step 2 becomes active.
- Reloading the page resets the wizard (OK for now).

- [ ] **Step 5: Commit**

```
git add apps/frontend/src/features/admin/new-project/NewProjectPage.tsx \
        apps/frontend/src/features/admin/new-project/Step1Stammdaten.tsx \
        apps/frontend/src/router.tsx
git commit -m "feat(admin): add NewProjectPage stepper with Step 1 (Stammdaten)"
```

---

## Task 9: Frontend — Step 2 (Geometrie)

**Files:**
- Create: `apps/frontend/src/features/admin/new-project/Step2Geometrie.tsx`
- Modify: `apps/frontend/src/features/admin/new-project/NewProjectPage.tsx`

- [ ] **Step 1: Build Step 2**

Embed the existing `RouteCalculatorForm` inline (no modal wrapper), plus a `FileInput` for GeoJSON upload. Reuse `useConfirmRoute(projectId)` and `useUpdateProjectGeometry(projectId)`. Use the same state handling pattern as `GeometryManagementModal` — but omit the "deleteExisting" toggle (new projects have no geometry).

Provide two buttons:
- "Speichern & Weiter" — calls `confirmRoute` (if a route preview exists) or `updateProjectGeometry` (if a GeoJSON was uploaded), then calls `onDone()`.
- "Überspringen" — calls `onDone()` immediately.

Props:
```ts
type Props = {
    projectId: number;
    onDone: () => void;
};
```

Do NOT duplicate the modal wrapper, scroll area, or delete toggle. Keep the component under ~150 lines by leaning on `RouteCalculatorForm`.

- [ ] **Step 2: Wire into stepper**

In `NewProjectPage.tsx`, replace the placeholder in `Stepper.Step label="Geometrie"`:

```tsx
<Stepper.Step label="Geometrie" description="Optional">
    {project?.id != null && (
        <Step2Geometrie projectId={project.id} onDone={() => setActive(2)} />
    )}
</Stepper.Step>
```

- [ ] **Step 3: Smoke-test**

Run dev server, create a test project via Step 1, then on Step 2:
- Calculate a route between two stations and save — verify the project gets geometry.
- Alternatively upload a GeoJSON file.
- Click "Überspringen" — confirms Step 3 opens.

- [ ] **Step 4: Commit**

```
git add apps/frontend/src/features/admin/new-project/Step2Geometrie.tsx \
        apps/frontend/src/features/admin/new-project/NewProjectPage.tsx
git commit -m "feat(admin): wizard step 2 — inline geometry calculator"
```

---

## Task 10: Frontend — Step 3 (Projekteigenschaften)

**Files:**
- Create: `apps/frontend/src/features/admin/new-project/Step3Properties.tsx`
- Modify: `apps/frontend/src/features/admin/new-project/NewProjectPage.tsx`

- [ ] **Step 1: Build Step 3**

```tsx
import { Button, Group, Stack } from "@mantine/core";
import { useMemo, useState } from "react";
import { ProjectEditFields } from "../../projects/ProjectEditFields";
import type { ProjectEditFormValues } from "../../projects/ProjectEdit";
import { updateProject, useProjectGroups, type Project, type ProjectUpdatePayload } from "../../../shared/api/queries";

type Props = {
    project: Project;
    onDone: (updated: Project) => void;
};

export default function Step3Properties({ project, onDone }: Props) {
    const { data: groups = [] } = useProjectGroups();
    const groupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
    );
    const [values, setValues] = useState<ProjectEditFormValues>(() => createInitialValuesFromProject(project));
    const [saving, setSaving] = useState(false);

    const handleSave = async () => {
        setSaving(true);
        try {
            const payload: ProjectUpdatePayload = buildUpdatePayload(values, project);
            const updated = await updateProject(project.id!, payload);
            onDone(updated);
        } finally {
            setSaving(false);
        }
    };

    return (
        <Stack gap="md">
            <ProjectEditFields values={values} setValues={setValues} projectGroupOptions={groupOptions} />
            <Group justify="flex-end">
                <Button variant="subtle" onClick={() => onDone(project)}>Überspringen</Button>
                <Button onClick={handleSave} loading={saving}>Speichern & Weiter</Button>
            </Group>
        </Stack>
    );
}

// If ProjectEdit.tsx already exports createInitialValues/createUpdatePayload, import them here and drop these helpers.
function createInitialValuesFromProject(project: Project): ProjectEditFormValues { /* reuse ProjectEdit's helper */ }
function buildUpdatePayload(values: ProjectEditFormValues, project: Project): ProjectUpdatePayload { /* reuse ProjectEdit's helper */ }
```

**Preferred approach:** Before writing Step 3, export `createInitialValues` and `createUpdatePayload` from `ProjectEdit.tsx` and import them here, to avoid duplication. If they depend on closure state inside the drawer, refactor them into pure functions first (they likely already are pure — they were named in the Explore report).

- [ ] **Step 2: Wire into stepper**

In `NewProjectPage.tsx`:

```tsx
<Stepper.Step label="Eigenschaften" description="Optional">
    {project && (
        <Step3Properties
            project={project}
            onDone={(updated) => { setProject(updated); setActive(3); }}
        />
    )}
</Stepper.Step>
```

- [ ] **Step 3: Smoke-test**

Verify toggling several booleans (e.g. `elektrification`, `abs`) persists via PATCH and Step 4 opens.

- [ ] **Step 4: Commit**

```
git add apps/frontend/src/features/admin/new-project/Step3Properties.tsx \
        apps/frontend/src/features/admin/new-project/NewProjectPage.tsx \
        apps/frontend/src/features/projects/ProjectEdit.tsx
git commit -m "feat(admin): wizard step 3 — project properties via ProjectEditFields"
```

---

## Task 11: Frontend — Step 4 (FinVes)

**Files:**
- Create: `apps/frontend/src/features/admin/new-project/Step4Finves.tsx`
- Modify: `apps/frontend/src/features/admin/new-project/NewProjectPage.tsx`

- [ ] **Step 1: Build Step 4**

```tsx
import { Button, Group, MultiSelect, Stack, Text } from "@mantine/core";
import { useMemo, useState } from "react";
import { useFinves, useLinkFinvesToProject } from "../../../shared/api/queries";

type Props = {
    projectId: number;
    onDone: () => void;
};

export default function Step4Finves({ projectId, onDone }: Props) {
    const { data: finves = [] } = useFinves();
    const linkFinves = useLinkFinvesToProject(projectId);
    const [selected, setSelected] = useState<string[]>([]);

    const options = useMemo(
        () =>
            finves.map((f) => ({
                value: String(f.id),
                label: `${f.finve_nr ?? "—"} · ${f.name ?? ""}`.trim(),
            })),
        [finves],
    );

    const handleSave = async () => {
        if (selected.length === 0) return onDone();
        await linkFinves.mutateAsync(selected.map(Number));
        onDone();
    };

    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">Wähle bestehende FinVes aus, die diesem Projekt zugeordnet werden sollen.</Text>
            <MultiSelect
                label="FinVes"
                data={options}
                value={selected}
                onChange={setSelected}
                searchable
                clearable
                hidePickedOptions
                placeholder="FinVes suchen…"
            />
            <Group justify="flex-end">
                <Button variant="subtle" onClick={onDone}>Überspringen</Button>
                <Button onClick={handleSave} loading={linkFinves.isPending} disabled={selected.length === 0}>
                    Verknüpfen & Weiter
                </Button>
            </Group>
        </Stack>
    );
}
```

Verify `useFinves`'s returned type has `finve_nr` and `name` fields. If property names differ in `FinveListItem`, adjust.

- [ ] **Step 2: Wire into stepper**

```tsx
<Stepper.Step label="FinVes" description="Optional">
    {project?.id != null && <Step4Finves projectId={project.id} onDone={() => setActive(4)} />}
</Stepper.Step>
```

- [ ] **Step 3: Smoke-test**

Select 1-2 FinVes, click Verknüpfen — verify the `finve_to_project` rows were created (check `/projects/{id}` — the FinVe appears).

- [ ] **Step 4: Commit**

```
git add apps/frontend/src/features/admin/new-project/Step4Finves.tsx \
        apps/frontend/src/features/admin/new-project/NewProjectPage.tsx
git commit -m "feat(admin): wizard step 4 — link FinVes"
```

---

## Task 12: Frontend — Step 5 (VIB) + completion

**Files:**
- Create: `apps/frontend/src/features/admin/new-project/Step5Vib.tsx`
- Modify: `apps/frontend/src/features/admin/new-project/NewProjectPage.tsx`

- [ ] **Step 1: Build Step 5**

```tsx
import { Button, Group, MultiSelect, Stack, Text } from "@mantine/core";
import { useMemo, useState } from "react";
import { useConfirmedVibEntries, useUpdateVibEntry } from "../../../shared/api/queries";

type Props = {
    projectId: number;
    onDone: () => void;
};

export default function Step5Vib({ projectId, onDone }: Props) {
    const { data: entries = [] } = useConfirmedVibEntries();
    const updateVib = useUpdateVibEntry();
    const [selected, setSelected] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);

    const options = useMemo(
        () => entries.map((e) => ({
            value: String(e.id),
            label: `[${e.report_year}] ${e.vib_name_raw ?? "(ohne Name)"}`,
        })),
        [entries],
    );

    const handleSave = async () => {
        if (selected.length === 0) return onDone();
        setSaving(true);
        try {
            for (const idStr of selected) {
                const id = Number(idStr);
                const entry = entries.find((e) => e.id === id);
                if (!entry) continue;
                const nextProjectIds = Array.from(new Set([...entry.project_ids, projectId]));
                await updateVib.mutateAsync({ id, payload: { project_ids: nextProjectIds } });
            }
            onDone();
        } finally {
            setSaving(false);
        }
    };

    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">Ordne diesem neuen Projekt bestehende VIB-Einträge zu.</Text>
            <MultiSelect
                label="VIB-Einträge"
                data={options}
                value={selected}
                onChange={setSelected}
                searchable
                clearable
                hidePickedOptions
                placeholder="VIB-Einträge suchen…"
            />
            <Group justify="flex-end">
                <Button variant="subtle" onClick={onDone}>Überspringen</Button>
                <Button onClick={handleSave} loading={saving} disabled={selected.length === 0}>
                    Verknüpfen & Fertig
                </Button>
            </Group>
        </Stack>
    );
}
```

Check the existing `useUpdateVibEntry` signature (line 970 of queries.ts) — adapt the call shape (`mutateAsync({ id, payload })` vs. `mutateAsync({ entryId, body })`).

- [ ] **Step 2: Wire into stepper + completion redirect**

```tsx
<Stepper.Step label="VIB" description="Optional">
    {project?.id != null && <Step5Vib projectId={project.id} onDone={() => setActive(5)} />}
</Stepper.Step>
```

And once `active === 5`, auto-navigate: add `useEffect(() => { if (active === 5) handleFinish(); }, [active])`.

- [ ] **Step 3: Smoke test end-to-end**

Create a new project; go through all 5 steps; confirm redirect to `/projects/{id}` shows the project with the linked VIB entries.

- [ ] **Step 4: Commit**

```
git add apps/frontend/src/features/admin/new-project/Step5Vib.tsx \
        apps/frontend/src/features/admin/new-project/NewProjectPage.tsx
git commit -m "feat(admin): wizard step 5 — link VIB entries and complete"
```

---

## Task 13: Nav entry-points + roadmap

**Files:**
- Modify: `apps/frontend/src/features/admin/UnassignedPage.tsx`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add button to UnassignedPage**

Above the two tables, for editor/admin only:

```tsx
<Group>
    <Button component={Link} to="/admin/projects/new" variant="filled">
        Neues Projekt anlegen
    </Button>
</Group>
```

Import `Link` from `react-router-dom` if not already imported.

- [ ] **Step 2: Tick the roadmap**

In `docs/roadmap.md`, replace the wizard entry under "Neues Projekt anlegen":

```
- [x] 5-step wizard at `/admin/projects/new`: Stammdaten → Geometrie → Projekteigenschaften → FinVes → VIB. …
```

Also tick the companion item if the UnassignedPage button was what it described:

```
- [x] **Neues Projekt aus Zuordnungsseite anlegen** — Auf `/admin/unassigned` einen "Neues Projekt anlegen"-Button …
```

- [ ] **Step 3: Commit**

```
git add apps/frontend/src/features/admin/UnassignedPage.tsx docs/roadmap.md
git commit -m "feat(admin): entry button from UnassignedPage; tick wizard in roadmap"
```

---

## Self-Review

**Spec coverage:**
- ✅ Step 1 Stammdaten (required) — Task 8.
- ✅ superior_project combobox — Task 7.
- ✅ Step 2 Geometrie — Task 9 (inline; no deleteExisting toggle, per spec).
- ✅ Step 3 Projekteigenschaften with `ProjectEditFields` extraction — Tasks 5 + 10.
- ✅ Step 4 FinVes — Task 11 (new endpoint in Task 2).
- ✅ Step 5 VIB — Task 12 (new GET endpoint in Task 3, reuses existing PATCH).
- ✅ Role gating — Task 8 component-level check.
- ✅ Backend endpoints `POST /api/v1/projects` and `POST /api/v1/projects/{id}/finves` — Tasks 1 and 2.
- ✅ No new data model / migration — confirmed.

**Open assumptions to watch during execution:**
- `useProjectGroups`: name used in Tasks 8 and 10 — verify against `queries.ts`. If it's `useListProjectGroups` or similar, adjust.
- `useFinves` return shape — if it uses `finve_nr` vs. `finve_number`, fix in Task 11 Step 1.
- `useUpdateVibEntry` mutation signature — adjust the call in Task 12 Step 1 accordingly.
- `createInitialValues` / `createUpdatePayload` in `ProjectEdit.tsx` — Task 10 assumes they can be exported unchanged. Prefer exporting over re-implementing.
