# VIB Review Features — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `planungsstand` field extraction (A), per-entry `project_status` select (B), and replace the VIB review table with card-based arrow navigation (C).

**Architecture:** Backend adds two nullable columns to `vib_entry` + one migration; the parser extracts `planungsstand` from raw text. The frontend replaces the flat table in `VibReviewPage.tsx` with a single-card view controlled by `currentIndex` state. `VibSection.tsx` gains two new display elements. All confirm logic is unchanged — the entries array is still the source of truth.

**Tech Stack:** Python/SQLAlchemy/Alembic (backend), React/TypeScript/Mantine (frontend), pdfplumber (parser)

---

## Task 1 — DB model + migration

**Files:**
- Modify: `apps/backend/dashboard_backend/models/vib/vib_entry.py`
- Create: `apps/backend/alembic/versions/20260331001_add_planungsstand_project_status_to_vib_entry.py`

- [ ] Add two columns to the model:

```python
# apps/backend/dashboard_backend/models/vib/vib_entry.py
# after: entwurfsgeschwindigkeit = Column(String(50), nullable=True)
planungsstand = Column(Text, nullable=True)
project_status = Column(String(20), nullable=True)   # "Planung" | "Bau" | None
```

- [ ] Create the migration file:

```python
# apps/backend/alembic/versions/20260331001_add_planungsstand_project_status_to_vib_entry.py
"""add planungsstand and project_status to vib_entry

Revision ID: 20260331001
Revises: 20260315001
Create Date: 2026-03-31

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260331001"
down_revision: Union[str, None] = "20260315001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vib_entry", sa.Column("planungsstand", sa.Text(), nullable=True))
    op.add_column("vib_entry", sa.Column("project_status", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("vib_entry", "project_status")
    op.drop_column("vib_entry", "planungsstand")
```

- [ ] Apply migration (backend venv must be active):

```bash
cd apps/backend && alembic upgrade head
```

Expected: `Running upgrade 20260315001 -> 20260331001, add planungsstand and project_status to vib_entry`

- [ ] Commit:

```bash
git add apps/backend/dashboard_backend/models/vib/vib_entry.py \
        apps/backend/alembic/versions/20260331001_add_planungsstand_project_status_to_vib_entry.py
git commit -m "feat(vib): add planungsstand and project_status columns to vib_entry"
```

---

## Task 2 — Backend schemas

**Files:**
- Modify: `apps/backend/dashboard_backend/schemas/vib.py`

- [ ] Add `planungsstand` and `project_status` to all three entry schemas:

In `VibEntryProposed` (after `entwurfsgeschwindigkeit`):
```python
planungsstand: Optional[str] = None
project_status: Optional[str] = None   # "Planung" | "Bau" | None
```

In `VibConfirmEntryInput` (after `entwurfsgeschwindigkeit`):
```python
planungsstand: Optional[str] = None
project_status: Optional[str] = None
```

In `VibEntryForProjectSchema` (after `entwurfsgeschwindigkeit`):
```python
planungsstand: Optional[str] = None
project_status: Optional[str] = None
```

- [ ] Commit:

```bash
git add apps/backend/dashboard_backend/schemas/vib.py
git commit -m "feat(vib): add planungsstand and project_status to VIB schemas"
```

---

## Task 3 — Parser extraction

**Files:**
- Modify: `apps/backend/dashboard_backend/tasks/vib.py`

- [ ] Add `planungsstand` to `_BLOCK_LABELS` (the dict at ~line 70):

```python
# in _BLOCK_LABELS dict, add after "teilinbetriebnahmen":
"planungsstand": re.compile(r"Planungsstand", re.IGNORECASE),
```

- [ ] Pass `planungsstand` when building `VibEntryProposed` (at ~line 477):

```python
entry = VibEntryProposed(
    vib_section=section_nr,
    vib_lfd_nr=lfd_nr,
    vib_name_raw=name_raw,
    category=category,
    verkehrliche_zielsetzung=sub_blocks.get("verkehrliche_zielsetzung"),
    durchgefuehrte_massnahmen=sub_blocks.get("durchgefuehrte_massnahmen"),
    noch_umzusetzende_massnahmen=sub_blocks.get("noch_umzusetzende_massnahmen"),
    bauaktivitaeten=sub_blocks.get("bauaktivitaeten"),
    teilinbetriebnahmen=sub_blocks.get("teilinbetriebnahmen"),
    planungsstand=sub_blocks.get("planungsstand"),
    raw_text=block_text[:_RAW_TEXT_MAX_CHARS],
    strecklaenge_km=strecklaenge,
    gesamtkosten_mio_eur=gesamtkosten,
    entwurfsgeschwindigkeit=geschwindigkeit_str,
    pfa_entries=pfa_entries,
    project_id=suggested_ids[0] if suggested_ids else None,
    suggested_project_ids=suggested_ids,
)
```

- [ ] Commit:

```bash
git add apps/backend/dashboard_backend/tasks/vib.py
git commit -m "feat(vib): extract Planungsstand field from VIB PDF"
```

---

## Task 4 — CRUD: pass new fields on create

**Files:**
- Modify: `apps/backend/dashboard_backend/crud/vib.py`

- [ ] Add `planungsstand` and `project_status` to the `VibEntry(...)` constructor in `create_vib_report_with_entries` (at ~line 128):

```python
vib_entry = VibEntry(
    vib_report_id=report.id,
    project_id=entry_data.project_id,
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
    project_status=entry_data.project_status,
)
```

- [ ] Commit:

```bash
git add apps/backend/dashboard_backend/crud/vib.py
git commit -m "feat(vib): persist planungsstand and project_status on VIB import confirm"
```

---

## Task 5 — Sync frontend API client

**Files:**
- Modify: `apps/frontend/src/shared/api/queries.ts`

The frontend types in `queries.ts` are hand-maintained (not auto-generated). Add the two fields manually to all three types:

- [ ] In `VibEntryProposed` (after `entwurfsgeschwindigkeit`):

```typescript
planungsstand: string | null;
project_status: "Planung" | "Bau" | null;
```

- [ ] `VibConfirmEntryInput` is `Omit<VibEntryProposed, "suggested_project_ids">` — it picks up the new fields automatically. No change needed.

- [ ] In `VibEntryForProject` (after `entwurfsgeschwindigkeit`):

```typescript
planungsstand: string | null;
project_status: "Planung" | "Bau" | null;
```

- [ ] Commit:

```bash
git add apps/frontend/src/shared/api/queries.ts
git commit -m "feat(vib): add planungsstand and project_status to frontend VIB types"
```

---

## Task 6 — VibReviewPage: card navigation

**Files:**
- Modify: `apps/frontend/src/features/vib-import/VibReviewPage.tsx`

Replace the entire file with the card-based implementation below.

Key changes vs current:
- Table + `VibEntryRow` → single `VibEntryCard` with all fields visible
- New `currentIndex` state controls which entry is shown
- `handleProjectChange` / `handleStatusChange` now operate on `currentIndex` (not an `index` param)
- Confirm logic is unchanged

- [ ] Replace `VibReviewPage.tsx` with:

```tsx
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Badge,
    Button,
    Card,
    Collapse,
    Container,
    Group,
    Loader,
    Paper,
    Select,
    Stack,
    Table,
    Text,
    Title,
    Tooltip,
} from "@mantine/core";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useVibParseResult,
    useConfirmVibImport,
    useProjects,
    type VibEntryProposed,
    type VibConfirmEntryInput,
} from "../../shared/api/queries";

const CATEGORY_COLORS: Record<string, string> = {
    laufend: "blue",
    neu: "green",
    potentiell: "yellow",
    abgeschlossen: "gray",
};

const PROJECT_STATUS_OPTIONS = [
    { value: "Planung", label: "Planung" },
    { value: "Bau", label: "Bau" },
];

function VibEntryCard({
    entry,
    projectOptions,
    onProjectChange,
    onStatusChange,
}: {
    entry: VibEntryProposed;
    projectOptions: { value: string; label: string }[];
    onProjectChange: (projectId: number | null) => void;
    onStatusChange: (status: string | null) => void;
}) {
    const [pfaExpanded, setPfaExpanded] = useState(false);
    const [rawExpanded, setRawExpanded] = useState(false);

    const hasSuggestion =
        entry.project_id !== null ||
        (entry.suggested_project_ids && entry.suggested_project_ids.length > 0);
    const confidence =
        entry.project_id !== null && entry.suggested_project_ids[0] === entry.project_id
            ? "high"
            : entry.project_id !== null
              ? "manual"
              : "none";

    return (
        <Card withBorder radius="md" padding="lg" shadow="xs">
            <Stack gap="md">
                {/* Section label */}
                {entry.vib_section && (
                    <Text size="xs" c="dimmed" ff="monospace">
                        {entry.vib_section}
                    </Text>
                )}

                {/* Projektkenndaten */}
                {(entry.strecklaenge_km !== null ||
                    entry.gesamtkosten_mio_eur !== null ||
                    entry.entwurfsgeschwindigkeit) && (
                    <Group gap="lg">
                        {entry.strecklaenge_km !== null && (
                            <Text size="sm">
                                <b>Länge:</b> {entry.strecklaenge_km} km
                            </Text>
                        )}
                        {entry.gesamtkosten_mio_eur !== null && (
                            <Text size="sm">
                                <b>Gesamtkosten:</b> {entry.gesamtkosten_mio_eur} Mio. €
                            </Text>
                        )}
                        {entry.entwurfsgeschwindigkeit && (
                            <Text size="sm">
                                <b>Vmax:</b> {entry.entwurfsgeschwindigkeit} km/h
                            </Text>
                        )}
                    </Group>
                )}

                {/* Planungsstand */}
                {entry.planungsstand && (
                    <div>
                        <Text size="sm" fw={600} mb={2}>
                            Planungsstand:
                        </Text>
                        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                            {entry.planungsstand}
                        </Text>
                    </div>
                )}

                {/* Project mapping */}
                <Group gap={4} align="center" wrap="nowrap">
                    <Select
                        label="Projekt zuordnen"
                        size="sm"
                        clearable
                        searchable
                        placeholder="Projekt zuordnen…"
                        data={projectOptions}
                        value={entry.project_id !== null ? String(entry.project_id) : null}
                        onChange={(v) => onProjectChange(v !== null ? Number(v) : null)}
                        style={{ flex: 1 }}
                    />
                    {hasSuggestion && (
                        <Tooltip
                            label={`KI-Vorschlag: ${entry.suggested_project_ids.join(", ")}`}
                            style={{ marginTop: 22 }}
                        >
                            <Badge
                                size="xs"
                                color={
                                    confidence === "high"
                                        ? "green"
                                        : confidence === "manual"
                                          ? "yellow"
                                          : "red"
                                }
                                variant="dot"
                                style={{ cursor: "default", marginTop: 22 }}
                            >
                                {confidence === "high" ? "✓" : confidence === "manual" ? "~" : "?"}
                            </Badge>
                        </Tooltip>
                    )}
                    <Select
                        label="Projektstatus"
                        size="sm"
                        clearable
                        placeholder="–"
                        data={PROJECT_STATUS_OPTIONS}
                        value={entry.project_status ?? null}
                        onChange={onStatusChange}
                        style={{ width: 140 }}
                    />
                </Group>

                {/* Bauaktivitäten */}
                {entry.bauaktivitaeten && (
                    <div>
                        <Text size="sm" fw={600} mb={2}>
                            Bauaktivitäten:
                        </Text>
                        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                            {entry.bauaktivitaeten}
                        </Text>
                    </div>
                )}

                {/* Teilinbetriebnahmen */}
                {entry.teilinbetriebnahmen && (
                    <div>
                        <Text size="sm" fw={600} mb={2}>
                            Teilinbetriebnahmen:
                        </Text>
                        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                            {entry.teilinbetriebnahmen}
                        </Text>
                    </div>
                )}

                {/* PFA-Tabelle */}
                {entry.pfa_entries && entry.pfa_entries.length > 0 && (
                    <div>
                        <Group
                            gap="xs"
                            mb={4}
                            style={{ cursor: "pointer" }}
                            onClick={() => setPfaExpanded((v) => !v)}
                        >
                            <Text size="sm" fw={600}>
                                PFA-Tabelle ({entry.pfa_entries.length} Einträge)
                            </Text>
                            <Text size="xs" c="dimmed">
                                {pfaExpanded ? "▲ ausblenden" : "▼ anzeigen"}
                            </Text>
                        </Group>
                        <Collapse in={pfaExpanded}>
                            <Paper withBorder p={0} style={{ overflow: "auto" }}>
                                <Table
                                    withTableBorder
                                    withColumnBorders
                                    fz="xs"
                                    style={{ fontSize: 11 }}
                                >
                                    <Table.Thead>
                                        <Table.Tr>
                                            <Table.Th>Nr.</Table.Th>
                                            <Table.Th>Örtlichkeit</Table.Th>
                                            <Table.Th>Abschluss FinVe</Table.Th>
                                            <Table.Th>PFB</Table.Th>
                                            <Table.Th>Baubeginn</Table.Th>
                                            <Table.Th>IBM</Table.Th>
                                        </Table.Tr>
                                    </Table.Thead>
                                    <Table.Tbody>
                                        {entry.pfa_entries.map((pfa, pi) => (
                                            <Table.Tr key={pi}>
                                                <Table.Td>
                                                    {pfa.abschnitt_label
                                                        ? `${pfa.abschnitt_label} / `
                                                        : ""}
                                                    {pfa.nr_pfa}
                                                </Table.Td>
                                                <Table.Td>{pfa.oertlichkeit ?? "–"}</Table.Td>
                                                <Table.Td>{pfa.abschluss_finve ?? "–"}</Table.Td>
                                                <Table.Td>{pfa.datum_pfb ?? "–"}</Table.Td>
                                                <Table.Td>{pfa.baubeginn ?? "–"}</Table.Td>
                                                <Table.Td>{pfa.inbetriebnahme ?? "–"}</Table.Td>
                                            </Table.Tr>
                                        ))}
                                    </Table.Tbody>
                                </Table>
                            </Paper>
                        </Collapse>
                    </div>
                )}

                {/* Volltext */}
                {entry.raw_text && (
                    <div>
                        <Group
                            gap="xs"
                            mb={4}
                            style={{ cursor: "pointer" }}
                            onClick={() => setRawExpanded((v) => !v)}
                        >
                            <Text size="sm" fw={600}>
                                Volltext
                            </Text>
                            <Text size="xs" c="dimmed">
                                {rawExpanded ? "▲ ausblenden" : "▼ anzeigen"}
                            </Text>
                        </Group>
                        <Collapse in={rawExpanded}>
                            <Text size="xs" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>
                                {entry.raw_text}
                            </Text>
                        </Collapse>
                    </div>
                )}
            </Stack>
        </Card>
    );
}

export default function VibReviewPage() {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const { data: parseResult, isLoading, isError } = useVibParseResult(taskId ?? null);
    const { data: projects } = useProjects();
    const confirm = useConfirmVibImport();

    const [entries, setEntries] = useState<VibEntryProposed[] | null>(null);
    const [currentIndex, setCurrentIndex] = useState(0);

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    if (isLoading) {
        return (
            <Container py="xl">
                <Group justify="center">
                    <Loader />
                </Group>
            </Container>
        );
    }

    if (isError || !parseResult) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">
                    Parse-Ergebnis konnte nicht geladen werden. Möglicherweise ist der Task noch
                    nicht abgeschlossen.
                </Alert>
            </Container>
        );
    }

    const displayEntries: VibEntryProposed[] = entries ?? parseResult.entries;
    const total = displayEntries.length;
    const currentEntry = displayEntries[currentIndex];

    const projectOptions = (projects ?? []).map((p) => ({
        value: String(p.id),
        label: `${p.project_number ?? "–"} ${p.name}`,
    }));

    const handleProjectChange = (projectId: number | null) => {
        setEntries((prev) => {
            const base = prev ?? parseResult.entries;
            return base.map((e, i) =>
                i === currentIndex ? { ...e, project_id: projectId } : e,
            );
        });
    };

    const handleStatusChange = (status: string | null) => {
        setEntries((prev) => {
            const base = prev ?? parseResult.entries;
            return base.map((e, i) =>
                i === currentIndex ? { ...e, project_status: status as "Planung" | "Bau" | null } : e,
            );
        });
    };

    const handleConfirm = async () => {
        if (!taskId) return;
        const payload = {
            task_id: taskId,
            year: parseResult.year,
            drucksache_nr: parseResult.drucksache_nr,
            report_date: parseResult.report_date,
            entries: displayEntries.map(
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                ({ suggested_project_ids, ...rest }): VibConfirmEntryInput => rest,
            ),
        };
        try {
            const res = await confirm.mutateAsync(payload);
            notifications.show({
                color: "green",
                message: `Import erfolgreich: ${res.entries_created} Vorhaben, ${res.pfa_entries_created} PFA-Einträge importiert.`,
            });
            navigate("/admin/vib-import");
        } catch (e: unknown) {
            const msg = (e as { message?: string })?.message ?? "Unbekannter Fehler";
            notifications.show({ color: "red", message: `Fehler: ${msg}` });
        }
    };

    const matchedCount = displayEntries.filter((e) => e.project_id !== null).length;

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                {/* Navigation bar */}
                <Group justify="space-between" align="center" wrap="wrap" gap="sm">
                    <Group gap="xs" align="center">
                        <ActionIcon
                            variant="subtle"
                            onClick={() => setCurrentIndex((i) => i - 1)}
                            disabled={currentIndex === 0}
                        >
                            <IconChevronLeft size={18} />
                        </ActionIcon>
                        <Text size="sm" fw={500} style={{ minWidth: 60, textAlign: "center" }}>
                            {currentIndex + 1} / {total}
                        </Text>
                        <ActionIcon
                            variant="subtle"
                            onClick={() => setCurrentIndex((i) => i + 1)}
                            disabled={currentIndex === total - 1}
                        >
                            <IconChevronRight size={18} />
                        </ActionIcon>
                        <Text fw={600} lineClamp={1} style={{ maxWidth: 400 }}>
                            {currentEntry.vib_name_raw}
                        </Text>
                        <Badge
                            size="sm"
                            color={CATEGORY_COLORS[currentEntry.category] ?? "gray"}
                            variant="light"
                        >
                            {currentEntry.category}
                        </Badge>
                    </Group>

                    <Group gap="sm">
                        <Text size="sm" c="dimmed">
                            {matchedCount} / {total} zugeordnet
                        </Text>
                        <Button variant="outline" onClick={() => navigate("/admin/vib-import")}>
                            Abbrechen
                        </Button>
                        <Button
                            onClick={handleConfirm}
                            loading={confirm.isPending}
                            color="green"
                        >
                            Import bestätigen
                        </Button>
                    </Group>
                </Group>

                {/* Header info */}
                <Stack gap={2}>
                    <Title order={2}>VIB-Review — Berichtsjahr {parseResult.year}</Title>
                    <Text size="sm" c="dimmed">
                        {parseResult.drucksache_nr
                            ? `Drucksache ${parseResult.drucksache_nr}`
                            : ""}
                        {parseResult.report_date ? ` · ${parseResult.report_date}` : ""}
                    </Text>
                </Stack>

                {/* Entry card */}
                {currentEntry && (
                    <VibEntryCard
                        entry={currentEntry}
                        projectOptions={projectOptions}
                        onProjectChange={handleProjectChange}
                        onStatusChange={handleStatusChange}
                    />
                )}
            </Stack>
        </Container>
    );
}
```

- [ ] Verify `@tabler/icons-react` is already a dependency (it is, used elsewhere in the project):

```bash
grep -r "tabler/icons-react" apps/frontend/package.json
```

Expected: line with `@tabler/icons-react`

- [ ] Commit:

```bash
git add apps/frontend/src/features/vib-import/VibReviewPage.tsx
git commit -m "feat(vib): replace table with card navigation in VibReviewPage"
```

---

## Task 7 — VibSection.tsx: display planungsstand + project_status

**Files:**
- Modify: `apps/frontend/src/features/projects/components/VibSection.tsx`

- [ ] In `VibTabContent`, add `planungsstand` display after the Kenndaten block (after the `entry.strecklaenge_km` group, before `entry.bauaktivitaeten`):

```tsx
{/* Planungsstand */}
{entry.planungsstand && (
    <div>
        <Text size="sm" fw={600} mb={4}>
            Planungsstand
        </Text>
        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
            {entry.planungsstand}
        </Text>
    </div>
)}
```

- [ ] Add `project_status` badge next to the existing category badge in `VibTabContent` (inside the `<Group gap="sm">` at the top of the component):

```tsx
{entry.project_status && (
    <Badge
        size="sm"
        color={entry.project_status === "Bau" ? "cyan" : "orange"}
        variant="light"
    >
        {entry.project_status}
    </Badge>
)}
```

- [ ] Commit:

```bash
git add apps/frontend/src/features/projects/components/VibSection.tsx
git commit -m "feat(vib): display planungsstand and project_status in VibSection"
```

---

## Task 8 — Update roadmap

**Files:**
- Modify: `docs/roadmap.md`

- [ ] Mark all Feature A/B/C checklist items as done (`- [ ]` → `- [x]`):

```bash
# In docs/roadmap.md, under "### More VIB features":
# Change all "- [ ]" to "- [x]" for Features A, B, C
```

- [ ] Commit:

```bash
git add docs/roadmap.md
git commit -m "docs: mark VIB planungsstand/project_status/card-nav features as complete"
```
