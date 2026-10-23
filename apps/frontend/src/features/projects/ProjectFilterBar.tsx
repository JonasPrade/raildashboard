import { ActionIcon, Button, Group, NumberInput, Popover, Select, Stack, Switch, Text, TextInput } from "@mantine/core";
import { Filter, Search, X } from "lucide-react";

import PhaseFilterSelect from "./PhaseFilterSelect";
import { phaseFilterOptions, type PhaseFilterValue } from "./phaseFilter";
import { dateFilterMarks, type DateFilter } from "./dateFilter";

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
    /** Replaced and aborted projects shown (`?beendet=1`). */
    showEnded: boolean;
    onShowEndedChange: (checked: boolean) => void;
    dateFilter: DateFilter;
    onDateFilterChange: (filter: DateFilter) => void;
    /** Hits after all filters, and the size of the group they come from. */
    shown: number;
    total: number | null;
};

function YearRange({
    label,
    from,
    to,
    onChange,
}: {
    label: string;
    from: number | null;
    to: number | null;
    onChange: (from: number | null, to: number | null) => void;
}) {
    const year = (v: string | number) => (typeof v === "number" && v >= 1900 && v <= 2100 ? v : null);
    return (
        <Stack gap={4}>
            <Text size="sm" fw={500}>
                {label}
            </Text>
            <Group gap="xs" wrap="nowrap">
                <NumberInput
                    aria-label={`${label} von`}
                    placeholder="von"
                    value={from ?? ""}
                    onChange={(v) => onChange(year(v), to)}
                    min={1900}
                    max={2100}
                    allowDecimal={false}
                    thousandSeparator={false}
                    hideControls
                    style={{ flex: 1 }}
                />
                <NumberInput
                    aria-label={`${label} bis`}
                    placeholder="bis"
                    value={to ?? ""}
                    onChange={(v) => onChange(from, year(v))}
                    min={1900}
                    max={2100}
                    allowDecimal={false}
                    thousandSeparator={false}
                    hideControls
                    style={{ flex: 1 }}
                />
            </Group>
        </Stack>
    );
}

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
    showEnded,
    onShowEndedChange,
    dateFilter,
    onDateFilterChange,
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
            {dateFilterMarks(dateFilter).map((mark) => (
                <FilterMark key={mark.label} label={mark.label} onRemove={() => onDateFilterChange(mark.without)} />
            ))}
            {onlySuperior && <FilterMark label="Nur Hauptprojekte" onRemove={() => onOnlySuperiorChange(false)} />}
            {showEnded && <FilterMark label="Mit beendeten Projekten" onRemove={() => onShowEndedChange(false)} />}
            <Popover width={300} position="bottom-start">
                <Popover.Target>
                    <Button variant="default" leftSection={<Filter size={16} />}>
                        Filter
                    </Button>
                </Popover.Target>
                <Popover.Dropdown>
                    <Stack gap="md">
                        <PhaseFilterSelect label="Planungsphase" value={phases} onChange={onPhasesChange} />
                        <YearRange
                            label="Baubeginn (Jahr)"
                            from={dateFilter.bauFrom}
                            to={dateFilter.bauTo}
                            onChange={(bauFrom, bauTo) => onDateFilterChange({ ...dateFilter, bauFrom, bauTo })}
                        />
                        <YearRange
                            label="Inbetriebnahme (Jahr)"
                            from={dateFilter.ibFrom}
                            to={dateFilter.ibTo}
                            onChange={(ibFrom, ibTo) => onDateFilterChange({ ...dateFilter, ibFrom, ibTo })}
                        />
                        <Switch
                            label="Termin offen"
                            description="Baubeginn oder Inbetriebnahme nur als Untergrenze bekannt („nach 2031“) — zählt in keinem Zeitraum"
                            checked={dateFilter.open}
                            onChange={(e) => onDateFilterChange({ ...dateFilter, open: e.currentTarget.checked })}
                        />
                        <Switch
                            label="Nur Hauptprojekte"
                            checked={onlySuperior}
                            onChange={(e) => onOnlySuperiorChange(e.currentTarget.checked)}
                        />
                        <Switch
                            label="Beendete Projekte einblenden"
                            description="Abgebrochene und durch ein anderes Projekt ersetzte Projekte"
                            checked={showEnded}
                            onChange={(e) => onShowEndedChange(e.currentTarget.checked)}
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
