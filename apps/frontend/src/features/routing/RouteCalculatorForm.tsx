import { useState } from "react";
import {
    ActionIcon,
    Button,
    Combobox,
    Group,
    InputBase,
    Loader,
    Stack,
    Text,
    useCombobox,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import type { OperationalPointRef, RoutePreviewFeature } from "../../shared/api/queries";
import { useCalculateRoute, useOperationalPointSearch } from "../../shared/api/queries";

type StationSelectProps = {
    label: string;
    value: OperationalPointRef | null;
    onChange: (op: OperationalPointRef | null) => void;
};

function StationSelect({ label, value, onChange }: StationSelectProps) {
    const [query, setQuery] = useState("");
    const [debouncedQuery] = useDebouncedValue(query, 300);
    const combobox = useCombobox({ onDropdownClose: () => combobox.resetSelectedOption() });
    const { data: results = [], isFetching } = useOperationalPointSearch(debouncedQuery);

    const displayValue = value ? (value.name ?? value.op_id ?? "") : "";

    return (
        <Combobox
            store={combobox}
            onOptionSubmit={(val) => {
                const op = results.find((r) => String(r.id) === val) ?? null;
                onChange(op);
                setQuery(op?.name ?? "");
                combobox.closeDropdown();
            }}
        >
            <Combobox.Target>
                <InputBase
                    label={label}
                    placeholder="Station suchen…"
                    value={query || displayValue}
                    onChange={(e) => {
                        setQuery(e.currentTarget.value);
                        if (!e.currentTarget.value) onChange(null);
                        combobox.openDropdown();
                    }}
                    onFocus={() => combobox.openDropdown()}
                    onBlur={() => {
                        combobox.closeDropdown();
                        if (!value) setQuery("");
                    }}
                    rightSection={isFetching ? <Loader size="xs" /> : <Combobox.Chevron />}
                    rightSectionPointerEvents="none"
                />
            </Combobox.Target>
            <Combobox.Dropdown>
                <Combobox.Options>
                    {results.length === 0 && !isFetching && debouncedQuery.length >= 2 && (
                        <Combobox.Empty>Keine Ergebnisse</Combobox.Empty>
                    )}
                    {results.map((op) => (
                        <Combobox.Option key={op.id} value={String(op.id)}>
                            <Text size="sm" fw={500}>{op.name ?? op.op_id}</Text>
                            {op.op_id && op.name && (
                                <Text size="xs" c="dimmed">{op.op_id}</Text>
                            )}
                        </Combobox.Option>
                    ))}
                </Combobox.Options>
            </Combobox.Dropdown>
        </Combobox>
    );
}

type Props = {
    onResult: (feature: RoutePreviewFeature) => void;
    onError: (message: string) => void;
};

export default function RouteCalculatorForm({ onResult, onError }: Props) {
    const [start, setStart] = useState<OperationalPointRef | null>(null);
    const [end, setEnd] = useState<OperationalPointRef | null>(null);
    const [viaList, setViaList] = useState<Array<OperationalPointRef | null>>([]);

    const { mutate: calculate, isPending } = useCalculateRoute();

    function addVia() {
        setViaList((prev) => [...prev, null]);
    }

    function removeVia(index: number) {
        setViaList((prev) => prev.filter((_, i) => i !== index));
    }

    function updateVia(index: number, op: OperationalPointRef | null) {
        setViaList((prev) => prev.map((v, i) => (i === index ? op : v)));
    }

    function buildWaypoints() {
        const stations = [start, ...viaList, end];
        return stations
            .filter((op): op is OperationalPointRef =>
                op !== null && op.latitude !== null && op.longitude !== null,
            )
            .map((op) => ({ lat: op.latitude!, lon: op.longitude! }));
    }

    function handleCalculate() {
        const waypoints = buildWaypoints();
        if (waypoints.length < 2) {
            onError("Start- und Zielbahnhof müssen angegeben werden.");
            return;
        }
        calculate(
            { waypoints },
            {
                onSuccess: (feature) => onResult(feature),
                onError: (err) => {
                    const status = (err as { status?: number }).status;
                    if (status === 502) {
                        onError("Routing-Dienst nicht erreichbar.");
                    } else if (status === 422) {
                        onError("Kein Pfad gefunden.");
                    } else {
                        onError("Fehler bei der Routenberechnung.");
                    }
                },
            },
        );
    }

    const canCalculate = start !== null && end !== null && !isPending;

    return (
        <Stack gap="sm">
            <StationSelect label="Startbahnhof" value={start} onChange={setStart} />

            {viaList.map((via, i) => (
                <Group key={i} align="flex-end" gap="xs">
                    <div style={{ flex: 1 }}>
                        <StationSelect
                            label={`Via ${i + 1}`}
                            value={via}
                            onChange={(op) => updateVia(i, op)}
                        />
                    </div>
                    <ActionIcon
                        variant="subtle"
                        color="red"
                        onClick={() => removeVia(i)}
                        mb={1}
                        aria-label="Via entfernen"
                    >
                        ×
                    </ActionIcon>
                </Group>
            ))}

            <Button variant="subtle" size="xs" onClick={addVia} style={{ alignSelf: "flex-start" }}>
                + Via-Bahnhof hinzufügen
            </Button>

            <StationSelect label="Zielbahnhof" value={end} onChange={setEnd} />

            <Button
                onClick={handleCalculate}
                loading={isPending}
                disabled={!canCalculate}
                mt="xs"
            >
                Route berechnen
            </Button>
        </Stack>
    );
}
