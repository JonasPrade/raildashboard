# Admin Unassigned Assignments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `/admin/unassigned` page that shows FinVes and VIB entries without project links, with inline project assignment.

**Architecture:** Four new backend endpoints under `/api/v1/admin/` (two GET for listing, two PATCH for assigning). New `UnassignedPage.tsx` frontend page with two table sections and inline MultiSelect assignment. Header badge shows total count.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, React, Mantine UI, React Query, openapi-typescript (gen-api)

---

## File Map

**Create:**
- `apps/backend/dashboard_backend/schemas/admin_assignments.py` — Pydantic schemas
- `apps/backend/dashboard_backend/crud/admin_assignments.py` — DB queries + assignment logic
- `apps/backend/dashboard_backend/api/v1/endpoints/admin_assignments.py` — FastAPI router
- `apps/backend/tests/api/test_admin_assignments.py` — API tests
- `apps/frontend/src/features/admin/UnassignedPage.tsx` — React page

**Modify:**
- `apps/backend/dashboard_backend/api/v1/api.py` — register new router
- `apps/frontend/src/shared/api/queries.ts` — add 4 query hooks + 2 types
- `apps/frontend/src/router.tsx` — add `/admin/unassigned` route
- `apps/frontend/src/components/Header.tsx` — add nav link with badge

---

### Task 1: Backend schemas

**Files:**
- Create: `apps/backend/dashboard_backend/schemas/admin_assignments.py`

- [ ] **Step 1: Create the schema file**

```python
# apps/backend/dashboard_backend/schemas/admin_assignments.py
from __future__ import annotations

from pydantic import BaseModel


class UnassignedFinveSchema(BaseModel):
    id: int
    name: str | None
    is_sammel_finve: bool
    starting_year: int | None

    model_config = {"from_attributes": True}


class UnassignedVibEntrySchema(BaseModel):
    id: int
    vib_name_raw: str
    vib_section: str | None
    category: str
    report_year: int

    model_config = {"from_attributes": True}


class AssignProjectsInput(BaseModel):
    project_ids: list[int]
```

- [ ] **Step 2: Commit**

```bash
cd apps/backend && git add dashboard_backend/schemas/admin_assignments.py
git commit -m "feat(admin): add schemas for unassigned FinVe/VIB assignment endpoints"
```

---

### Task 2: Backend CRUD

**Files:**
- Create: `apps/backend/dashboard_backend/crud/admin_assignments.py`

- [ ] **Step 1: Write the CRUD file**

```python
# apps/backend/dashboard_backend/crud/admin_assignments.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.schemas.admin_assignments import (
    UnassignedFinveSchema,
    UnassignedVibEntrySchema,
)


def list_unassigned_finves(db: Session) -> list[UnassignedFinveSchema]:
    """Return FinVes that have no entry in finve_to_project."""
    rows = (
        db.query(Finve)
        .outerjoin(FinveToProject, FinveToProject.finve_id == Finve.id)
        .filter(FinveToProject.id.is_(None))
        .order_by(Finve.id)
        .all()
    )
    return [
        UnassignedFinveSchema(
            id=f.id,
            name=f.name,
            is_sammel_finve=f.is_sammel_finve,
            starting_year=f.starting_year,
        )
        for f in rows
    ]


def list_unassigned_vib_entries(db: Session) -> list[UnassignedVibEntrySchema]:
    """Return VibEntries that have no row in vib_entry_project."""
    rows = (
        db.query(VibEntry, VibReport.year)
        .join(VibReport, VibReport.id == VibEntry.vib_report_id)
        .outerjoin(
            vib_entry_project,
            vib_entry_project.c.vib_entry_id == VibEntry.id,
        )
        .filter(vib_entry_project.c.project_id.is_(None))
        .order_by(VibReport.year.desc(), VibEntry.id)
        .all()
    )
    return [
        UnassignedVibEntrySchema(
            id=entry.id,
            vib_name_raw=entry.vib_name_raw,
            vib_section=entry.vib_section,
            category=entry.category,
            report_year=year,
        )
        for entry, year in rows
    ]


def assign_finve_to_projects(db: Session, finve_id: int, project_ids: list[int]) -> None:
    """Insert finve_to_project rows (haushalt_year=NULL). Skips existing links."""
    for pid in project_ids:
        exists = (
            db.query(FinveToProject)
            .filter(
                FinveToProject.finve_id == finve_id,
                FinveToProject.project_id == pid,
                FinveToProject.haushalt_year.is_(None),
            )
            .first()
        )
        if not exists:
            db.add(FinveToProject(finve_id=finve_id, project_id=pid, haushalt_year=None))
    db.flush()


def assign_vib_entry_to_projects(db: Session, entry_id: int, project_ids: list[int]) -> None:
    """Insert vib_entry_project rows. Skips existing links."""
    existing = set(
        db.execute(
            vib_entry_project.select().where(
                vib_entry_project.c.vib_entry_id == entry_id
            )
        ).scalars()
    )
    new_rows = [
        {"vib_entry_id": entry_id, "project_id": pid}
        for pid in project_ids
        if pid not in existing
    ]
    if new_rows:
        db.execute(vib_entry_project.insert(), new_rows)
    db.flush()
```

- [ ] **Step 2: Commit**

```bash
git add apps/backend/dashboard_backend/crud/admin_assignments.py
git commit -m "feat(admin): add CRUD for listing/assigning unassigned FinVes and VIB entries"
```

---

### Task 3: Backend endpoint

**Files:**
- Create: `apps/backend/dashboard_backend/api/v1/endpoints/admin_assignments.py`
- Modify: `apps/backend/dashboard_backend/api/v1/api.py`

- [ ] **Step 1: Create endpoint file**

```python
# apps/backend/dashboard_backend/api/v1/endpoints/admin_assignments.py
from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_roles
from dashboard_backend.crud.admin_assignments import (
    assign_finve_to_projects,
    assign_vib_entry_to_projects,
    list_unassigned_finves,
    list_unassigned_vib_entries,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.users import User
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.admin_assignments import (
    AssignProjectsInput,
    UnassignedFinveSchema,
    UnassignedVibEntrySchema,
)
from dashboard_backend.schemas.users import UserRole

router = AuthRouter()

_require_editor = Depends(require_roles(UserRole.editor, UserRole.admin))


@router.get("/unassigned-finves", response_model=list[UnassignedFinveSchema])
def get_unassigned_finves(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[UnassignedFinveSchema]:
    return list_unassigned_finves(db)


@router.get("/unassigned-vib-entries", response_model=list[UnassignedVibEntrySchema])
def get_unassigned_vib_entries(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[UnassignedVibEntrySchema]:
    return list_unassigned_vib_entries(db)


@router.patch("/unassigned-finves/{finve_id}/assign", response_model=None, status_code=204)
def assign_finve(
    finve_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> None:
    finve = db.get(Finve, finve_id)
    if not finve:
        raise HTTPException(status_code=404, detail="FinVe not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    assign_finve_to_projects(db, finve_id, body.project_ids)
    db.commit()


@router.patch("/unassigned-vib-entries/{entry_id}/assign", response_model=None, status_code=204)
def assign_vib_entry(
    entry_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> None:
    entry = db.get(VibEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="VIB entry not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    assign_vib_entry_to_projects(db, entry_id, body.project_ids)
    db.commit()
```

- [ ] **Step 2: Register router in `api/v1/api.py`**

Open `apps/backend/dashboard_backend/api/v1/api.py`. Add `admin_assignments` to the import and add `include_router` call:

```python
# dashboard_backend/api/v1/api.py
from fastapi import APIRouter
from .endpoints import auth, project_routes, project_texts, route, projects, project_groups, users, tasks, haushalt_import, finves, settings, vib_import, admin_assignments

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(route.router, prefix="/route", tags=["route"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(project_groups.router, prefix="/project_groups", tags=["project_groups"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(project_routes.router, tags=["routes"])
api_router.include_router(project_texts.router, tags=["texts"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(haushalt_import.router, prefix="/import/haushalt", tags=["haushalt-import"])
api_router.include_router(finves.router, prefix="/finves", tags=["finves"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(vib_import.router, prefix="/import/vib", tags=["vib-import"])
api_router.include_router(admin_assignments.router, prefix="/admin", tags=["admin-assignments"])
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/dashboard_backend/api/v1/endpoints/admin_assignments.py \
        apps/backend/dashboard_backend/api/v1/api.py
git commit -m "feat(admin): add admin assignment endpoints for unassigned FinVes and VIB entries"
```

---

### Task 4: Backend tests

**Files:**
- Create: `apps/backend/tests/api/test_admin_assignments.py`

- [ ] **Step 1: Write the test file**

```python
# apps/backend/tests/api/test_admin_assignments.py
"""Tests for /api/v1/admin/unassigned-* endpoints."""
from __future__ import annotations

import dashboard_backend.api.v1.endpoints.admin_assignments as admin_route
from dashboard_backend.schemas.admin_assignments import (
    UnassignedFinveSchema,
    UnassignedVibEntrySchema,
)
from dashboard_backend.schemas.users import UserRole

MOCK_FINVES = [
    UnassignedFinveSchema(id=1, name="ABS Test", is_sammel_finve=False, starting_year=2020),
    UnassignedFinveSchema(id=2, name="SV Sammel", is_sammel_finve=True, starting_year=2022),
]

MOCK_VIB_ENTRIES = [
    UnassignedVibEntrySchema(
        id=10,
        vib_name_raw="Ausbau Strecke X",
        vib_section="B.4.1",
        category="laufend",
        report_year=2024,
    ),
]


def test_get_unassigned_finves_requires_auth(client):
    resp = client.get("/api/v1/admin/unassigned-finves")
    assert resp.status_code == 401


def test_get_unassigned_finves_returns_list(client, monkeypatch, create_user):
    create_user("editor1", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "list_unassigned_finves", lambda db: MOCK_FINVES)

    resp = client.get(
        "/api/v1/admin/unassigned-finves",
        headers={"Authorization": "Basic ZWRpdG9yMTpwYXNz"},  # editor1:pass base64
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["id"] == 1
    assert body[1]["is_sammel_finve"] is True


def test_get_unassigned_finves_empty(client, monkeypatch, create_user):
    create_user("editor2", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "list_unassigned_finves", lambda db: [])

    resp = client.get(
        "/api/v1/admin/unassigned-finves",
        headers={"Authorization": "Basic ZWRpdG9yMjpwYXNz"},  # editor2:pass
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_unassigned_vib_entries_requires_auth(client):
    resp = client.get("/api/v1/admin/unassigned-vib-entries")
    assert resp.status_code == 401


def test_get_unassigned_vib_entries_returns_list(client, monkeypatch, create_user):
    create_user("editor3", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "list_unassigned_vib_entries", lambda db: MOCK_VIB_ENTRIES)

    resp = client.get(
        "/api/v1/admin/unassigned-vib-entries",
        headers={"Authorization": "Basic ZWRpdG9yMzpwYXNz"},  # editor3:pass
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["report_year"] == 2024


def test_assign_finve_requires_auth(client):
    resp = client.patch(
        "/api/v1/admin/unassigned-finves/1/assign",
        json={"project_ids": [5]},
    )
    assert resp.status_code == 401


def test_assign_finve_not_found(client, monkeypatch, create_user):
    create_user("editor4", "pass", UserRole.editor)

    resp = client.patch(
        "/api/v1/admin/unassigned-finves/9999/assign",
        json={"project_ids": [5]},
        headers={"Authorization": "Basic ZWRpdG9yNDpwYXNz"},  # editor4:pass
    )
    assert resp.status_code == 404


def test_assign_vib_entry_not_found(client, monkeypatch, create_user):
    create_user("editor5", "pass", UserRole.editor)

    resp = client.patch(
        "/api/v1/admin/unassigned-vib-entries/9999/assign",
        json={"project_ids": [5]},
        headers={"Authorization": "Basic ZWRpdG9yNTpwYXNz"},  # editor5:pass
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd apps/backend && .venv/bin/python -m pytest tests/api/test_admin_assignments.py -v
```

Expected: all tests pass (404 tests rely on DB returning None for non-existent IDs, which SQLite in-memory does correctly).

- [ ] **Step 3: Commit**

```bash
git add apps/backend/tests/api/test_admin_assignments.py
git commit -m "test(admin): add API tests for unassigned FinVe/VIB assignment endpoints"
```

---

### Task 5: Regenerate frontend API client

**Files:**
- Auto-generated: `apps/frontend/src/shared/api/types.gen.ts`

- [ ] **Step 1: Run gen-api (requires backend running at http://localhost:8000)**

```bash
make gen-api
```

Expected: `types.gen.ts` updated with `UnassignedFinveSchema`, `UnassignedVibEntrySchema`, `AssignProjectsInput` types.

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/shared/api/types.gen.ts apps/frontend/src/shared/api/schemas.gen.ts 2>/dev/null || true
git commit -m "chore: regenerate frontend API client with admin assignment endpoints"
```

---

### Task 6: Frontend query hooks

**Files:**
- Modify: `apps/frontend/src/shared/api/queries.ts`

Append these types and hooks at the end of the admin-assignments section (after the VIB section, before end of file or in a new `// Admin: unassigned assignments` section).

- [ ] **Step 1: Add types and hooks to `queries.ts`**

Find the end of the file (or after the last VIB hook) and append:

```typescript
// ---------------------------------------------------------------------------
// Admin: Offene Zuordnungen (unassigned FinVe / VIB entries)
// ---------------------------------------------------------------------------

export type UnassignedFinve = {
    id: number;
    name: string | null;
    is_sammel_finve: boolean;
    starting_year: number | null;
};

export type UnassignedVibEntry = {
    id: number;
    vib_name_raw: string;
    vib_section: string | null;
    category: string;
    report_year: number;
};

export function useUnassignedFinves() {
    return useQuery({
        queryKey: ["admin-unassigned-finves"],
        queryFn: () => api<UnassignedFinve[]>("/api/v1/admin/unassigned-finves"),
    });
}

export function useUnassignedVibEntries() {
    return useQuery({
        queryKey: ["admin-unassigned-vib-entries"],
        queryFn: () => api<UnassignedVibEntry[]>("/api/v1/admin/unassigned-vib-entries"),
    });
}

export function useAssignFinve() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ finveId, projectIds }: { finveId: number; projectIds: number[] }) =>
            api<void>(`/api/v1/admin/unassigned-finves/${finveId}/assign`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_ids: projectIds }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin-unassigned-finves"] });
        },
    });
}

export function useAssignVibEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, projectIds }: { entryId: number; projectIds: number[] }) =>
            api<void>(`/api/v1/admin/unassigned-vib-entries/${entryId}/assign`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_ids: projectIds }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin-unassigned-vib-entries"] });
        },
    });
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/shared/api/queries.ts
git commit -m "feat(admin): add query hooks for unassigned FinVe/VIB assignment"
```

---

### Task 7: Frontend page

**Files:**
- Create: `apps/frontend/src/features/admin/UnassignedPage.tsx`

- [ ] **Step 1: Create the page**

```tsx
// apps/frontend/src/features/admin/UnassignedPage.tsx
import { useState } from "react";
import {
    Alert,
    Badge,
    Button,
    Container,
    Group,
    Loader,
    MultiSelect,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import { useProjects } from "../../shared/api/queries";
import {
    useUnassignedFinves,
    useUnassignedVibEntries,
    useAssignFinve,
    useAssignVibEntry,
} from "../../shared/api/queries";

export default function UnassignedPage() {
    const { user } = useAuth();
    const [finveSelections, setFinveSelections] = useState<Record<number, string[]>>({});
    const [vibSelections, setVibSelections] = useState<Record<number, string[]>>({});

    const { data: finves, isLoading: finvesLoading } = useUnassignedFinves();
    const { data: vibEntries, isLoading: vibLoading } = useUnassignedVibEntries();
    const { data: projects } = useProjects();
    const assignFinve = useAssignFinve();
    const assignVib = useAssignVibEntry();

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    const projectOptions = (projects ?? []).map((p) => ({
        value: String(p.id),
        label: p.name ?? `Projekt ${p.id}`,
    }));

    const handleAssignFinve = async (finveId: number) => {
        const ids = (finveSelections[finveId] ?? []).map(Number);
        if (!ids.length) return;
        try {
            await assignFinve.mutateAsync({ finveId, projectIds: ids });
            notifications.show({ color: "green", message: "FinVe zugewiesen." });
            setFinveSelections((prev) => { const n = { ...prev }; delete n[finveId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    const handleAssignVib = async (entryId: number) => {
        const ids = (vibSelections[entryId] ?? []).map(Number);
        if (!ids.length) return;
        try {
            await assignVib.mutateAsync({ entryId, projectIds: ids });
            notifications.show({ color: "green", message: "VIB-Eintrag zugewiesen." });
            setVibSelections((prev) => { const n = { ...prev }; delete n[entryId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="xl">
                <Title order={2}>Offene Zuordnungen</Title>

                {/* FinVe section */}
                <Stack gap="sm">
                    <Group gap="xs">
                        <Title order={4}>FinVes ohne Projektzuordnung</Title>
                        <Badge color="red" variant="filled">{finves?.length ?? "…"}</Badge>
                    </Group>
                    {finvesLoading && <Loader size="sm" />}
                    {!finvesLoading && (
                        <Table withTableBorder withColumnBorders>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>ID</Table.Th>
                                    <Table.Th>Name</Table.Th>
                                    <Table.Th>Typ</Table.Th>
                                    <Table.Th>Ab Jahr</Table.Th>
                                    <Table.Th>Projekte zuweisen</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {(finves ?? []).length === 0 && (
                                    <Table.Tr>
                                        <Table.Td colSpan={5}>
                                            <Text c="dimmed" size="sm" ta="center">Keine offenen FinVes.</Text>
                                        </Table.Td>
                                    </Table.Tr>
                                )}
                                {(finves ?? []).map((f) => (
                                    <Table.Tr key={f.id}>
                                        <Table.Td>{f.id}</Table.Td>
                                        <Table.Td>{f.name ?? "–"}</Table.Td>
                                        <Table.Td>
                                            {f.is_sammel_finve
                                                ? <Badge color="violet" variant="light" size="sm">SV-FinVe</Badge>
                                                : <Badge color="blue" variant="light" size="sm">FinVe</Badge>
                                            }
                                        </Table.Td>
                                        <Table.Td>{f.starting_year ?? "–"}</Table.Td>
                                        <Table.Td>
                                            <Group gap="xs" wrap="nowrap">
                                                <MultiSelect
                                                    data={projectOptions}
                                                    value={finveSelections[f.id] ?? []}
                                                    onChange={(v) =>
                                                        setFinveSelections((prev) => ({ ...prev, [f.id]: v }))
                                                    }
                                                    placeholder="Projekt suchen…"
                                                    searchable
                                                    size="xs"
                                                    w={300}
                                                />
                                                <Button
                                                    size="xs"
                                                    disabled={!(finveSelections[f.id]?.length)}
                                                    loading={assignFinve.isPending}
                                                    onClick={() => handleAssignFinve(f.id)}
                                                >
                                                    Zuweisen
                                                </Button>
                                            </Group>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </Table>
                    )}
                </Stack>

                {/* VIB section */}
                <Stack gap="sm">
                    <Group gap="xs">
                        <Title order={4}>VIB-Einträge ohne Projektzuordnung</Title>
                        <Badge color="red" variant="filled">{vibEntries?.length ?? "…"}</Badge>
                    </Group>
                    {vibLoading && <Loader size="sm" />}
                    {!vibLoading && (
                        <Table withTableBorder withColumnBorders>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>ID</Table.Th>
                                    <Table.Th>Name</Table.Th>
                                    <Table.Th>Abschnitt</Table.Th>
                                    <Table.Th>Kategorie</Table.Th>
                                    <Table.Th>VIB-Jahr</Table.Th>
                                    <Table.Th>Projekte zuweisen</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {(vibEntries ?? []).length === 0 && (
                                    <Table.Tr>
                                        <Table.Td colSpan={6}>
                                            <Text c="dimmed" size="sm" ta="center">Keine offenen VIB-Einträge.</Text>
                                        </Table.Td>
                                    </Table.Tr>
                                )}
                                {(vibEntries ?? []).map((e) => (
                                    <Table.Tr key={e.id}>
                                        <Table.Td>{e.id}</Table.Td>
                                        <Table.Td style={{ maxWidth: 300 }}>{e.vib_name_raw}</Table.Td>
                                        <Table.Td>{e.vib_section ?? "–"}</Table.Td>
                                        <Table.Td>
                                            <Badge variant="light" size="sm">{e.category}</Badge>
                                        </Table.Td>
                                        <Table.Td>{e.report_year}</Table.Td>
                                        <Table.Td>
                                            <Group gap="xs" wrap="nowrap">
                                                <MultiSelect
                                                    data={projectOptions}
                                                    value={vibSelections[e.id] ?? []}
                                                    onChange={(v) =>
                                                        setVibSelections((prev) => ({ ...prev, [e.id]: v }))
                                                    }
                                                    placeholder="Projekt suchen…"
                                                    searchable
                                                    size="xs"
                                                    w={300}
                                                />
                                                <Button
                                                    size="xs"
                                                    disabled={!(vibSelections[e.id]?.length)}
                                                    loading={assignVib.isPending}
                                                    onClick={() => handleAssignVib(e.id)}
                                                >
                                                    Zuweisen
                                                </Button>
                                            </Group>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </Table>
                    )}
                </Stack>
            </Stack>
        </Container>
    );
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/features/admin/UnassignedPage.tsx
git commit -m "feat(admin): add UnassignedPage for inline FinVe/VIB project assignment"
```

---

### Task 8: Wire up routing and header

**Files:**
- Modify: `apps/frontend/src/router.tsx`
- Modify: `apps/frontend/src/components/Header.tsx`

- [ ] **Step 1: Add lazy import and route to `router.tsx`**

Add after the `VibStructurePreviewPage` lazy import line:

```typescript
const UnassignedPage = lazy(() => import("./features/admin/UnassignedPage"));
```

Add after the `admin/vib-import/preview/:taskId` route block (before the closing `]`):

```typescript
{
    path: "admin/unassigned",
    element: (
        <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
            <UnassignedPage />
        </Suspense>
    ),
},
```

- [ ] **Step 2: Add nav link with badge to `Header.tsx`**

Add this import at the top of `Header.tsx` (with the other Mantine imports):

```typescript
import { Badge } from "@mantine/core";
```

(Note: `Badge` may already be imported — check first and skip if so.)

Add the hook imports at the top of the component or import section:

```typescript
import { useUnassignedFinves, useUnassignedVibEntries } from "../shared/api/queries";
```

Inside the `Header` function body, add after the existing hooks:

```typescript
const { data: unassignedFinves } = useUnassignedFinves();
const { data: unassignedVibEntries } = useUnassignedVibEntries();
const totalUnassigned = (unassignedFinves?.length ?? 0) + (unassignedVibEntries?.length ?? 0);
```

Add this nav link inside `navLinks`, after the VIB-Import link and before the Administration link:

```tsx
{(user?.role === "editor" || user?.role === "admin") && (
    <NavLink
        to="/admin/unassigned"
        style={({ isActive }) => ({
            ...baseStyle,
            backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
        })}
        onClick={closeDrawer}
    >
        <Group gap={6} align="center">
            Offene Zuordnungen
            {totalUnassigned > 0 && (
                <Badge color="red" size="xs" variant="filled" circle>
                    {totalUnassigned}
                </Badge>
            )}
        </Group>
    </NavLink>
)}
```

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/router.tsx apps/frontend/src/components/Header.tsx
git commit -m "feat(admin): add /admin/unassigned route and header nav link with badge"
```

---

### Task 9: Update roadmap

**Files:**
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Mark the feature as done in roadmap**

In `docs/roadmap.md`, under `### Admin: Offene Zuordnungen (BudgetFinVe & VIB)`, change the first `- [ ]` to `- [x]`.

- [ ] **Step 2: Commit**

```bash
git add docs/roadmap.md
git commit -m "docs: mark admin unassigned assignments feature as complete"
```

---

## Self-Review Notes

- All GET endpoints that need auth use explicit `_current_user: User = _require_editor` parameter — `AuthRouter` only auto-adds auth for non-GET methods.
- `assign_vib_entry_to_projects` uses `scalars()` on a non-scalar select — this needs correction: use `db.execute(vib_entry_project.select()...).mappings()` then extract `project_id`. See Task 2 correction below.

**Correction to Task 2 — `assign_vib_entry_to_projects`:**

The `vib_entry_project` table has two columns (`vib_entry_id`, `project_id`). `scalars()` returns only the first column. Replace with:

```python
def assign_vib_entry_to_projects(db: Session, entry_id: int, project_ids: list[int]) -> None:
    """Insert vib_entry_project rows. Skips existing links."""
    rows = db.execute(
        vib_entry_project.select().where(
            vib_entry_project.c.vib_entry_id == entry_id
        )
    ).all()
    existing_pids = {row.project_id for row in rows}
    new_rows = [
        {"vib_entry_id": entry_id, "project_id": pid}
        for pid in project_ids
        if pid not in existing_pids
    ]
    if new_rows:
        db.execute(vib_entry_project.insert(), new_rows)
    db.flush()
```

Use this corrected version in Task 2, not the version shown in the original task body.
