import { useState } from "react";
import { Badge, Combobox, Group, InputBase, Text, useCombobox } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import type { OperationalPointNetwork, OperationalPointRef } from "../../shared/api/queries";
import { useOperationalPointSearch } from "../../shared/api/queries";

/** Short network tag per search hit, so equal names of different networks are told apart. */
const NETWORK_TAG: Record<OperationalPointNetwork, string | null> = {
    rail: null,
    light_rail: "S",
    subway: "U",
    tram: "Tram",
};

const NETWORK_TITLE: Record<OperationalPointNetwork, string> = {
    rail: "Betriebsstelle (RINF)",
    light_rail: "S-Bahn/Stadtbahn (OSM)",
    subway: "U-Bahn (OSM)",
    tram: "Straßenbahn (OSM)",
};

function networkOf(op: OperationalPointRef): OperationalPointNetwork {
    return (op.network in NETWORK_TITLE ? op.network : "rail") as OperationalPointNetwork;
}

type Props = {
    label: string;
    value: OperationalPointRef | null;
    onChange: (op: OperationalPointRef | null) => void;
};

export default function StationSelect({ label, value, onChange }: Props) {
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
                    rightSection={<Combobox.Chevron />}
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
                            <Group gap={6} wrap="nowrap">
                                {NETWORK_TAG[networkOf(op)] && (
                                    <Badge size="xs" variant="light" title={NETWORK_TITLE[networkOf(op)]}>
                                        {NETWORK_TAG[networkOf(op)]}
                                    </Badge>
                                )}
                                <Text size="sm" fw={500}>{op.name ?? op.op_id}</Text>
                            </Group>
                            {op.op_id && op.name && (
                                <Text size="xs" c="dimmed">
                                    {networkOf(op) === "rail" ? op.op_id : NETWORK_TITLE[networkOf(op)]}
                                </Text>
                            )}
                        </Combobox.Option>
                    ))}
                </Combobox.Options>
            </Combobox.Dropdown>
        </Combobox>
    );
}
