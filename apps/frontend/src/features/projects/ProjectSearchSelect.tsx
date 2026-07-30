import {
    CloseButton,
    Combobox,
    Group,
    InputBase,
    Loader,
    ScrollArea,
    Text,
    useCombobox,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useMemo, useState } from "react";

import { useProject, useProjects } from "../../shared/api/queries";
import { collectSubtreeIds, searchProjects } from "./projectSearch";

/** Options rendered at once — the full match count is shown in the footer. */
const MAX_OPTIONS = 30;

type Props = {
    label: string;
    value: number | null;
    onChange: (id: number | null) => void;
    /** Help text rendered below the label. */
    description?: string;
    /**
     * Hide this project and everything below it from the results. Used when picking a
     * superior project: a project can neither be its own parent nor be parented by one
     * of its descendants.
     */
    excludeSubtreeOfId?: number | null;
};

export default function ProjectSearchSelect({
    label,
    value,
    onChange,
    description,
    excludeSubtreeOfId = null,
}: Props) {
    const [search, setSearch] = useState("");
    const [debounced] = useDebouncedValue(search, 150);
    const combobox = useCombobox({
        onDropdownClose: () => {
            combobox.resetSelectedOption();
            setSearch("");
        },
        onDropdownOpen: () => combobox.updateSelectedOptionIndex("active"),
    });

    const { data: projects = [], isFetching } = useProjects();
    // The current value may not be part of the list (drafts are excluded from
    // GET /projects/) — fetch it directly so the input still shows its name.
    const { data: fetchedValue } = useProject(value ?? Number.NaN);

    const selectedProject = useMemo(() => {
        if (value == null) return null;
        return (
            projects.find((p) => p.id === value) ??
            (fetchedValue?.id === value ? fetchedValue : null)
        );
    }, [projects, fetchedValue, value]);

    const nameById = useMemo(() => {
        const map = new Map<number, string>();
        for (const project of projects) {
            if (typeof project.id === "number") map.set(project.id, project.name ?? "");
        }
        return map;
    }, [projects]);

    const excludedIds = useMemo(
        () => collectSubtreeIds(projects, excludeSubtreeOfId),
        [projects, excludeSubtreeOfId],
    );

    const matches = useMemo(
        () => searchProjects(projects, debounced, { excludeIds: excludedIds }),
        [projects, debounced, excludedIds],
    );
    const visibleMatches = matches.slice(0, MAX_OPTIONS);

    const selectedLabel =
        value == null ? "" : selectedProject?.name ?? `Projekt #${value}`;

    const rightSection = isFetching ? (
        <Loader size="xs" />
    ) : value != null ? (
        <CloseButton
            size="sm"
            aria-label="Auswahl entfernen"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
                onChange(null);
                setSearch("");
            }}
        />
    ) : (
        <Combobox.Chevron />
    );

    return (
        <Combobox
            store={combobox}
            withinPortal={false}
            onOptionSubmit={(val) => {
                const id = Number(val);
                onChange(Number.isNaN(id) ? null : id);
                combobox.closeDropdown();
            }}
        >
            <Combobox.Target>
                <InputBase
                    label={label}
                    description={description}
                    placeholder="Projektname oder Projektnummer suchen…"
                    value={combobox.dropdownOpened ? search : selectedLabel}
                    onFocus={() => combobox.openDropdown()}
                    onBlur={() => combobox.closeDropdown()}
                    onClick={() => combobox.openDropdown()}
                    onChange={(event) => {
                        setSearch(event.currentTarget.value);
                        combobox.openDropdown();
                    }}
                    rightSection={rightSection}
                    rightSectionPointerEvents={value != null && !isFetching ? "all" : "none"}
                />
            </Combobox.Target>

            <Combobox.Dropdown>
                <Combobox.Options>
                    <ScrollArea.Autosize mah={280} type="scroll">
                        {visibleMatches.length === 0 ? (
                            <Combobox.Empty>
                                {projects.length > 0 && excludedIds.size > 0 && search.trim() === ""
                                    ? "Keine auswählbaren Projekte"
                                    : "Keine Treffer"}
                            </Combobox.Empty>
                        ) : (
                            visibleMatches.map((project) => {
                                const parentName =
                                    typeof project.superior_project_id === "number"
                                        ? nameById.get(project.superior_project_id)
                                        : undefined;
                                return (
                                    <Combobox.Option
                                        key={project.id}
                                        value={String(project.id)}
                                        active={project.id === value}
                                    >
                                        <Group gap={6} wrap="nowrap" justify="space-between">
                                            <Text size="sm" fw={500} truncate>
                                                {project.name}
                                            </Text>
                                            {project.project_number && (
                                                <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>
                                                    {project.project_number}
                                                </Text>
                                            )}
                                        </Group>
                                        {parentName && (
                                            <Text size="xs" c="dimmed" truncate>
                                                Unterprojekt von {parentName}
                                            </Text>
                                        )}
                                    </Combobox.Option>
                                );
                            })
                        )}
                    </ScrollArea.Autosize>
                </Combobox.Options>
                {matches.length > visibleMatches.length && (
                    <Combobox.Footer>
                        <Text size="xs" c="dimmed">
                            {matches.length} Treffer — Suche verfeinern, um weitere zu sehen.
                        </Text>
                    </Combobox.Footer>
                )}
            </Combobox.Dropdown>
        </Combobox>
    );
}
