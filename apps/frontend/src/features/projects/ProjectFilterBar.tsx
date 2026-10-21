import { ActionIcon, Button, Popover, Select, Stack, Switch, TextInput } from "@mantine/core";
import { Filter, Search, X } from "lucide-react";

import PhaseFilterSelect from "./PhaseFilterSelect";
import { phaseFilterOptions, type PhaseFilterValue } from "./phaseFilter";

const PHASE_LABEL = new Map(phaseFilterOptions().map((o) => [o.value, o.label]));

type Props = {
    groups: { value: string; label: string }[];
    groupId: number | null;
    onGroupChange: (value: string | null) => void;
    groupsLoading: boolean;
    search: string;
    onSearchChange: (value: string) => void;
    phases: PhaseFilterValue[];
    onPhasesChange: (values: PhaseFilterValue[]) => void;
    onlySuperior: boolean;
    onOnlySuperiorChange: (checked: boolean) => void;
    /** Hits after all filters, and the size of the group they come from. */
    shown: number;
    total: number | null;
};

function FilterMark({ label, onRemove }: { label: string; onRemove: () => void }) {
    return (
        <span className="idt-filtermark">
            {label}
            <ActionIcon variant="transparent" size="sm" style={{ color: "inherit" }} aria-label={`Filter „${label}“ entfernen`} onClick={onRemove}>
                <X size={14} />
            </ActionIcon>
        </span>
    );
}

/**
 * Filter bar of the project list and timeline (Anwendungsebene „Tabelle“):
 * group, search field, the active filters as removable marks, the filter
 * button with the remaining filters, and the hit count on the right.
 */
export function ProjectFilterBar({
    groups,
    groupId,
    onGroupChange,
    groupsLoading,
    search,
    onSearchChange,
    phases,
    onPhasesChange,
    onlySuperior,
    onOnlySuperiorChange,
    shown,
    total,
}: Props) {
    return (
        <div className="idt-filterbar">
            <Select
                aria-label="Projektgruppe"
                placeholder="Projektgruppe wählen"
                data={groups}
                value={groupId !== null ? String(groupId) : null}
                onChange={onGroupChange}
                disabled={groupsLoading && groups.length === 0}
                nothingFoundMessage={groupsLoading ? "Lade…" : "Keine Projektgruppen gefunden"}
                searchable
                clearable
                style={{ flex: "1 1 220px", minWidth: 0, maxWidth: 360 }}
            />
            <TextInput
                aria-label="Suche"
                placeholder="Name, Nr., Beschreibung…"
                leftSection={<Search size={16} />}
                rightSection={
                    search ? (
                        <ActionIcon variant="subtle" size="sm" aria-label="Suche leeren" onClick={() => onSearchChange("")}>
                            <X size={14} />
                        </ActionIcon>
                    ) : undefined
                }
                value={search}
                onChange={(e) => onSearchChange(e.currentTarget.value)}
                style={{ flex: "1 1 220px", minWidth: 0, maxWidth: 360 }}
            />
            {phases.map((phase) => (
                <FilterMark
                    key={phase}
                    label={`Phase: ${PHASE_LABEL.get(phase) ?? phase}`}
                    onRemove={() => onPhasesChange(phases.filter((p) => p !== phase))}
                />
            ))}
            {onlySuperior && <FilterMark label="Nur Hauptprojekte" onRemove={() => onOnlySuperiorChange(false)} />}
            <Popover width={300} position="bottom-start">
                <Popover.Target>
                    <Button variant="default" leftSection={<Filter size={16} />}>
                        Filter
                    </Button>
                </Popover.Target>
                <Popover.Dropdown>
                    <Stack gap="md">
                        <PhaseFilterSelect label="Planungsphase" value={phases} onChange={onPhasesChange} />
                        <Switch
                            label="Nur Hauptprojekte"
                            checked={onlySuperior}
                            onChange={(e) => onOnlySuperiorChange(e.currentTarget.checked)}
                        />
                    </Stack>
                </Popover.Dropdown>
            </Popover>
            {total !== null && (
                <span
                    className="idt-filterbar__count"
                    aria-live="polite"
                    style={{
                        marginLeft: "auto",
                        color: "var(--text-muted)",
                        fontSize: 14.5,
                        fontVariantNumeric: "tabular-nums",
                        whiteSpace: "nowrap",
                    }}
                >
                    {shown} von {total}
                </span>
            )}
        </div>
    );
}

export default ProjectFilterBar;
