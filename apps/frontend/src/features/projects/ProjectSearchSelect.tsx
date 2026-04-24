import { Combobox, InputBase, Loader, Text, useCombobox } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useMemo, useState } from "react";

import { useProjects } from "../../shared/api/queries";

type Props = {
    label: string;
    value: number | null;
    onChange: (id: number | null) => void;
};

export default function ProjectSearchSelect({ label, value, onChange }: Props) {
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
        if (!q) return projects.slice(0, 20);
        return projects
            .filter((p) =>
                (p.name ?? "").toLowerCase().includes(q) ||
                (p.project_number ?? "").toLowerCase().includes(q),
            )
            .slice(0, 20);
    }, [projects, debounced]);

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
