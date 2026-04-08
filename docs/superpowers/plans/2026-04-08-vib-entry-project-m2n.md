# VIB Entry ↔ Project m:n Relation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single `vib_entry.project_id` FK with a `vib_entry_project` association table so one VIB entry can be linked to multiple projects.

**Architecture:** New `vib_entry_project` association table (composite PK). `VibEntry` model uses a SQLAlchemy `secondary` relationship. Schemas, CRUD, parser task, and review UI are updated end-to-end. Existing data is migrated in the Alembic migration before the old column is dropped.

**Tech Stack:** SQLAlchemy (Table + secondary relationship), Alembic, Pydantic v2, FastAPI, React + Mantine (MultiSelect)

---

## File Map

| Action | File |
|--------|------|
| Create | `apps/backend/dashboard_backend/models/vib/vib_entry_project.py` |
| Modify | `apps/backend/dashboard_backend/models/vib/vib_entry.py` |
| Create | `apps/backend/alembic/versions/20260408001_vib_entry_project_m2n.py` |
| Modify | `apps/backend/dashboard_backend/schemas/vib.py` |
| Modify | `apps/backend/dashboard_backend/crud/vib.py` |
| Modify | `apps/backend/dashboard_backend/tasks/vib.py` |
| Modify | `apps/backend/tests/tasks/test_vib_ai_extraction.py` |
| Modify | `apps/frontend/src/shared/api/queries.ts` |
| Modify | `apps/frontend/src/features/vib-import/VibReviewPage.tsx` |

---

## Task 1: Association Table Model

**Files:**
- Create: `apps/backend/dashboard_backend/models/vib/vib_entry_project.py`

- [ ] **Step 1: Create the association table module**

```python
# apps/backend/dashboard_backend/models/vib/vib_entry_project.py
from sqlalchemy import Column, ForeignKey, Integer, Table

from dashboard_backend.models.base import Base

vib_entry_project = Table(
    "vib_entry_project",
    Base.metadata,
    Column(
        "vib_entry_id",
        Integer,
        ForeignKey("vib_entry.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "project_id",
        Integer,
        ForeignKey("project.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
```

- [ ] **Step 2: Commit**

```bash
git add apps/backend/dashboard_backend/models/vib/vib_entry_project.py
git commit -m "feat(vib): add vib_entry_project association table module"
```

---

## Task 2: Update VibEntry Model

**Files:**
- Modify: `apps/backend/dashboard_backend/models/vib/vib_entry.py`

- [ ] **Step 1: Rewrite vib_entry.py**

Replace the entire file with:

```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project


class VibEntry(Base):
    __tablename__ = "vib_entry"

    id = Column(Integer, primary_key=True, index=True)
    vib_report_id = Column(
        Integer, ForeignKey("vib_report.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vib_section = Column(String(20), nullable=True)   # e.g. "B.4.1.1"
    vib_lfd_nr = Column(String(20), nullable=True)
    vib_name_raw = Column(String(500), nullable=False)
    # category: laufend | neu | potentiell | abgeschlossen
    category = Column(String(20), nullable=False, server_default="laufend")

    raw_text = Column(Text, nullable=True)
    bauaktivitaeten = Column(Text, nullable=True)
    teilinbetriebnahmen = Column(Text, nullable=True)
    verkehrliche_zielsetzung = Column(Text, nullable=True)
    durchgefuehrte_massnahmen = Column(Text, nullable=True)
    noch_umzusetzende_massnahmen = Column(Text, nullable=True)

    strecklaenge_km = Column(Float, nullable=True)
    gesamtkosten_mio_eur = Column(Float, nullable=True)
    entwurfsgeschwindigkeit = Column(String(50), nullable=True)
    planungsstand = Column(Text, nullable=True)
    status_planung = Column(Boolean, nullable=False, server_default="false", default=False)
    status_bau = Column(Boolean, nullable=False, server_default="false", default=False)
    status_abgeschlossen = Column(Boolean, nullable=False, server_default="false", default=False)

    ai_extracted = Column(Boolean, nullable=False, server_default="false", default=False)
    ai_result = Column(Text, nullable=True)  # JSON blob from LLM extraction

    report = relationship("VibReport", back_populates="entries")
    projects = relationship("Project", secondary=vib_entry_project, backref="vib_entries")
    pfa_entries = relationship("VibPfaEntry", back_populates="vib_entry", cascade="all, delete-orphan")
```

- [ ] **Step 2: Commit**

```bash
git add apps/backend/dashboard_backend/models/vib/vib_entry.py
git commit -m "feat(vib): replace project_id FK with m:n projects relationship on VibEntry"
```

---

## Task 3: Alembic Migration

**Files:**
- Create: `apps/backend/alembic/versions/20260408001_vib_entry_project_m2n.py`

- [ ] **Step 1: Write the migration**

```python
# apps/backend/alembic/versions/20260408001_vib_entry_project_m2n.py
"""replace vib_entry.project_id FK with vib_entry_project m2n table

Revision ID: 20260408001
Revises: 20260407002
Create Date: 2026-04-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260408001"
down_revision: Union[str, None] = "20260407002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vib_entry_project",
        sa.Column(
            "vib_entry_id",
            sa.Integer(),
            sa.ForeignKey("vib_entry.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )

    # Migrate existing single-project links into the new association table
    op.execute(
        "INSERT INTO vib_entry_project (vib_entry_id, project_id) "
        "SELECT id, project_id FROM vib_entry WHERE project_id IS NOT NULL"
    )

    op.drop_column("vib_entry", "project_id")


def downgrade() -> None:
    op.add_column(
        "vib_entry",
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Restore one project_id per entry (take any linked project — order not guaranteed)
    op.execute(
        "UPDATE vib_entry SET project_id = ("
        "  SELECT project_id FROM vib_entry_project"
        "  WHERE vib_entry_project.vib_entry_id = vib_entry.id"
        "  LIMIT 1"
        ")"
    )

    op.drop_table("vib_entry_project")
```

- [ ] **Step 2: Run the migration**

```bash
cd apps/backend && .venv/bin/alembic upgrade head
```

Expected: `Running upgrade 20260407002 -> 20260408001, replace vib_entry.project_id FK with vib_entry_project m2n table`

- [ ] **Step 3: Commit**

```bash
git add apps/backend/alembic/versions/20260408001_vib_entry_project_m2n.py
git commit -m "feat(vib): migrate vib_entry.project_id to vib_entry_project association table"
```

---

## Task 4: Pydantic Schema Changes

**Files:**
- Modify: `apps/backend/dashboard_backend/schemas/vib.py`

- [ ] **Step 1: Write failing test**

Create `apps/backend/tests/test_vib_schemas.py`:

```python
"""Tests for VIB Pydantic schema changes (m:n project relation)."""
from dashboard_backend.schemas.vib import VibEntryProposed, VibConfirmEntryInput


class TestVibEntryProposedM2n:
    def test_has_project_ids_not_project_id(self):
        entry = VibEntryProposed(vib_name_raw="Test")
        assert hasattr(entry, "project_ids")
        assert not hasattr(entry, "project_id")

    def test_project_ids_defaults_to_empty_list(self):
        entry = VibEntryProposed(vib_name_raw="Test")
        assert entry.project_ids == []

    def test_project_ids_accepts_multiple(self):
        entry = VibEntryProposed(vib_name_raw="Test", project_ids=[1, 2, 3])
        assert entry.project_ids == [1, 2, 3]


class TestVibConfirmEntryInputM2n:
    def test_has_project_ids_not_project_id(self):
        entry = VibConfirmEntryInput(vib_name_raw="Test")
        assert hasattr(entry, "project_ids")
        assert not hasattr(entry, "project_id")

    def test_project_ids_defaults_to_empty_list(self):
        entry = VibConfirmEntryInput(vib_name_raw="Test")
        assert entry.project_ids == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/backend && .venv/bin/python -m pytest tests/test_vib_schemas.py -v
```

Expected: FAIL — `AttributeError` or assertion errors because `project_id` still exists.

- [ ] **Step 3: Update schemas/vib.py**

In `VibEntryProposed` (around line 68), replace:
```python
    # Matching result — editable by user in review UI
    project_id: Optional[int] = None
```
with:
```python
    # Matching result — editable by user in review UI (m:n: multiple projects allowed)
    project_ids: list[int] = []
```

In `VibConfirmEntryInput` (around line 130), replace:
```python
    project_id: Optional[int] = None
```
with:
```python
    project_ids: list[int] = []
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/backend && .venv/bin/python -m pytest tests/test_vib_schemas.py -v
```

Expected: PASS — all 5 tests green.

- [ ] **Step 5: Commit**

```bash
git add apps/backend/dashboard_backend/schemas/vib.py apps/backend/tests/test_vib_schemas.py
git commit -m "feat(vib): replace project_id with project_ids list in VIB Pydantic schemas"
```

---

## Task 5: CRUD Changes

**Files:**
- Modify: `apps/backend/dashboard_backend/crud/vib.py`

- [ ] **Step 1: Update `create_vib_report_with_entries`**

In `crud/vib.py`, add the import at the top of the file (after the existing imports):

```python
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project
```

In `create_vib_report_with_entries`, remove `project_id=entry_data.project_id,` from the `VibEntry(...)` constructor. The constructor call (lines ~155–175) should become:

```python
        vib_entry = VibEntry(
            vib_report_id=report.id,
            vib_section=entry_data.vib_section,
            vib_lfd_nr=entry_data.vib_lfd_nr,
            vib_name_raw=entry_data.vib_name_raw,
            category=entry_data.category,
            raw_text=entry_data.raw_text,
            bauaktivitaeten=entry_data.bauaktivitaeten,
            teilinbetriebnahmen=entry_data.teilinbetriebnahmen,
            verkehrliche_zielsetzung=entry_data.verkehrliche_zielsetzung,
            durchgefuehrte_massnahmen=entry_data.durchgefuehrte_massnahmen,
            noch_umzusetzende_massnahmen=entry_data.noch_umzusetzende_massnahmen,
            strecklaenge_km=entry_data.strecklaenge_km,
            gesamtkosten_mio_eur=entry_data.gesamtkosten_mio_eur,
            entwurfsgeschwindigkeit=entry_data.entwurfsgeschwindigkeit,
            planungsstand=entry_data.planungsstand,
            status_planung=entry_data.status_planung,
            status_bau=entry_data.status_bau,
            status_abgeschlossen=entry_data.status_abgeschlossen,
        )
        db.add(vib_entry)
        db.flush()  # get vib_entry.id

        if entry_data.project_ids:
            db.execute(
                vib_entry_project.insert(),
                [{"vib_entry_id": vib_entry.id, "project_id": pid} for pid in entry_data.project_ids],
            )

        entries_created += 1
```

- [ ] **Step 2: Update `get_vib_entries_for_project`**

Replace the function body (lines ~205–217) with:

```python
def get_vib_entries_for_project(db: Session, project_id: int) -> list[VibEntry]:
    """Return all VibEntry rows linked to a project, newest report year first."""
    return (
        db.query(VibEntry)
        .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
        .filter(vib_entry_project.c.project_id == project_id)
        .join(VibEntry.report)
        .order_by(VibReport.year.desc())
        .options(
            joinedload(VibEntry.pfa_entries),
            joinedload(VibEntry.report),
        )
        .all()
    )
```

- [ ] **Step 3: Run existing tests to confirm nothing is broken**

```bash
cd apps/backend && .venv/bin/python -m pytest tests/ -v --ignore=tests/db_related_tests -x
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add apps/backend/dashboard_backend/crud/vib.py
git commit -m "feat(vib): update CRUD to use vib_entry_project association table"
```

---

## Task 6: Update VIB Parser Task

**Files:**
- Modify: `apps/backend/dashboard_backend/tasks/vib.py`
- Modify: `apps/backend/tests/tasks/test_vib_ai_extraction.py`

The parser currently sets `project_id=suggested_ids[0] if suggested_ids else None` when building `VibEntryProposed`. This must change to `project_ids`.

- [ ] **Step 1: Write failing test**

Add to `apps/backend/tests/tasks/test_vib_parser.py`:

```python
class TestVibEntryProposedProjectIds:
    """Parser must produce project_ids (list), not project_id (scalar)."""

    def test_suggested_ids_become_project_ids(self):
        from dashboard_backend.schemas.vib import VibEntryProposed
        entry = VibEntryProposed(
            vib_name_raw="Test",
            project_ids=[42],
            suggested_project_ids=[42],
        )
        assert entry.project_ids == [42]
        assert not hasattr(entry, "project_id")

    def test_no_suggestions_gives_empty_project_ids(self):
        from dashboard_backend.schemas.vib import VibEntryProposed
        entry = VibEntryProposed(vib_name_raw="Test")
        assert entry.project_ids == []
```

- [ ] **Step 2: Run to confirm test passes (schema already updated in Task 4)**

```bash
cd apps/backend && .venv/bin/python -m pytest tests/tasks/test_vib_parser.py::TestVibEntryProposedProjectIds -v
```

Expected: PASS (schema already updated).

- [ ] **Step 3: Update vib.py parser — find and replace the VibEntryProposed construction**

In `apps/backend/dashboard_backend/tasks/vib.py` around line 803, replace:

```python
            project_id=suggested_ids[0] if suggested_ids else None,
            suggested_project_ids=suggested_ids,
```

with:

```python
            project_ids=[suggested_ids[0]] if suggested_ids else [],
            suggested_project_ids=suggested_ids,
```

- [ ] **Step 4: Update test_vib_ai_extraction.py — fix _base_entry fixture**

In `apps/backend/tests/tasks/test_vib_ai_extraction.py`, in `_base_entry()`, replace:

```python
            "project_id": None,
            "suggested_project_ids": [],
```

with:

```python
            "project_ids": [],
            "suggested_project_ids": [],
```

- [ ] **Step 5: Run all backend tests**

```bash
cd apps/backend && .venv/bin/python -m pytest tests/ -v --ignore=tests/db_related_tests -x
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/dashboard_backend/tasks/vib.py apps/backend/tests/tasks/test_vib_parser.py apps/backend/tests/tasks/test_vib_ai_extraction.py
git commit -m "feat(vib): update VIB parser to emit project_ids list instead of project_id scalar"
```

---

## Task 7: Frontend — queries.ts

**Files:**
- Modify: `apps/frontend/src/shared/api/queries.ts`

- [ ] **Step 1: Update VibEntryProposed type**

In `queries.ts`, find the `VibEntryProposed` type (around line 738). Replace:

```typescript
    project_id: number | null;
    suggested_project_ids: number[];
```

with:

```typescript
    project_ids: number[];
    suggested_project_ids: number[];
```

`VibConfirmEntryInput` is defined as `Omit<VibEntryProposed, "suggested_project_ids">` so it picks up `project_ids` automatically — no further change needed there.

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/shared/api/queries.ts
git commit -m "feat(vib): update VibEntryProposed TS type: project_id -> project_ids"
```

---

## Task 8: Frontend — VibReviewPage.tsx

**Files:**
- Modify: `apps/frontend/src/features/vib-import/VibReviewPage.tsx`

There are six places to update in this file. Apply them in order.

- [ ] **Step 1: Add MultiSelect to Mantine imports**

At the top of the file, in the Mantine import block, add `MultiSelect` and remove `Select`:

```typescript
import {
    ActionIcon,
    Alert,
    Badge,
    Box,
    Button,
    Card,
    Checkbox,
    Container,
    Group,
    Loader,
    MultiSelect,
    Paper,
    Stack,
    Table,
    Text,
    Textarea,
    Title,
    Tooltip,
} from "@mantine/core";
```

- [ ] **Step 2: Update VibEntryCard prop signature**

In the `VibEntryCard` function props (around line 62), replace:

```typescript
    onProjectChange: (projectId: number | null) => void;
```

with:

```typescript
    onProjectChange: (projectIds: number[]) => void;
```

- [ ] **Step 3: Update confidence / hasSuggestion logic in VibEntryCard**

Replace (around lines 74–82):

```typescript
    const hasSuggestion =
        entry.project_id !== null ||
        (entry.suggested_project_ids && entry.suggested_project_ids.length > 0);
    const confidence =
        entry.project_id !== null && entry.suggested_project_ids[0] === entry.project_id
            ? "high"
            : entry.project_id !== null
              ? "manual"
              : "none";
```

with:

```typescript
    const hasSuggestion =
        entry.project_ids.length > 0 ||
        (entry.suggested_project_ids && entry.suggested_project_ids.length > 0);
    const confidence =
        entry.project_ids.length > 0 &&
        entry.suggested_project_ids.some((id) => entry.project_ids.includes(id))
            ? "high"
            : entry.project_ids.length > 0
              ? "manual"
              : "none";
```

- [ ] **Step 4: Replace Select with MultiSelect in the render**

Replace the project mapping `<Select>` block (around lines 141–152):

```typescript
                    <Select
                        label="Projekt zuordnen"
                        size="sm"
                        clearable
                        searchable
                        placeholder="Projekt zuordnen…"
                        data={projectOptions}
                        value={entry.project_id !== null ? String(entry.project_id) : null}
                        onChange={(v) => onProjectChange(v !== null ? Number(v) : null)}
                        style={{ flex: 1, minWidth: 200 }}
                    />
```

with:

```typescript
                    <MultiSelect
                        label="Projekte zuordnen"
                        size="sm"
                        clearable
                        searchable
                        placeholder="Projekte zuordnen…"
                        data={projectOptions}
                        value={entry.project_ids.map(String)}
                        onChange={(vs) => onProjectChange(vs.map(Number))}
                        style={{ flex: 1, minWidth: 200 }}
                    />
```

- [ ] **Step 5: Update matchedCount and onProjectChange call site**

Replace (around line 549):

```typescript
    const matchedCount = displayEntries.filter((e) => e.project_id !== null).length;
```

with:

```typescript
    const matchedCount = displayEntries.filter((e) => e.project_ids.length > 0).length;
```

Replace (around line 639):

```typescript
                        onProjectChange={(projectId) => updateCurrentEntry({ project_id: projectId })}
```

with:

```typescript
                        onProjectChange={(projectIds) => updateCurrentEntry({ project_ids: projectIds })}
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd apps/frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors. If there are type errors, read them carefully — they'll point to any remaining `project_id` references.

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/features/vib-import/VibReviewPage.tsx
git commit -m "feat(vib): update VibReviewPage to MultiSelect for m:n project assignment"
```

---

## Final Verification

- [ ] **Run all backend tests**

```bash
cd apps/backend && .venv/bin/python -m pytest tests/ -v --ignore=tests/db_related_tests
```

Expected: all tests pass.

- [ ] **Check for any remaining project_id references in VIB code**

```bash
grep -rn "project_id" apps/backend/dashboard_backend/models/vib/ apps/backend/dashboard_backend/schemas/vib.py apps/backend/dashboard_backend/tasks/vib.py apps/frontend/src/features/vib-import/
```

Expected: no matches (only `project_ids` plural or association table column references should remain).
