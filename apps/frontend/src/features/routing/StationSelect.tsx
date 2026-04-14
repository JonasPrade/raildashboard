import { useState } from "react";
import { Combobox, InputBase, Loader, Text, useCombobox } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import type { OperationalPointRef } from "../../shared/api/queries";
import { useOperationalPointSearch } from "../../shared/api/queries";

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
