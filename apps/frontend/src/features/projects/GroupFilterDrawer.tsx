import { Alert, Drawer, Stack, Button, Group, MultiSelect, Badge, CloseButton, Loader } from "@mantine/core";
import { useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";

export type ProjectGroupOption = {
    id: number;         // URL value (?group=<id[,id2,...]>)
    name: string;       // Display label
    color: string;      // HEX/RGB for the colour dot
    count?: number;     // optional: number of projects
};

type Props = {
    opened: boolean;
    onClose: () => void;
    groups?: ProjectGroupOption[];
    loading?: boolean;
    error?: string;
};

type SelectedGroupPillProps = {
    group: ProjectGroupOption;
    onRemove: () => void;
    disabled?: boolean;
};

function SelectedGroupPill({ group, onRemove, disabled }: SelectedGroupPillProps) {
    return (
        <Group
            gap={6}
            wrap="nowrap"
            style={{
                border: "1px solid #2a3550",
                borderRadius: 8,
                padding: "2px 6px",
                background: "#f8fafc"
            }}
        >
            <span
                aria-hidden
                style={{
                    width: 8,
                    height: 8,
                    borderRadius: 999,
                    background: group.color,
                    display: "inline-block"
                }}
            />
            <span style={{ fontSize: 12, color: "black" }}>{group.name}</span>
            {!disabled && (
                <CloseButton
                    aria-label={`Remove group ${group.name}`}
                    onClick={onRemove}
                    size="xs"
                    variant="subtle"
                />
            )}
        </Group>
    );
}

export default function GroupFilterDrawer({
                                              opened,
                                              onClose,
                                              groups = [],
                                              loading = false,
                                              error
                                          }: Props) {
    const [params, setParams] = useSearchParams();

    // Local (pending) selection stored as number[] because we want to keep IDs numeric
    const [pending, setPending] = useState<number[]>([]);

    useEffect(() => {
        setPending((prev) => prev.filter((value) => groups.some((group) => group.id === value)));
    }, [groups]);

    // When the drawer opens, sync pending selection from the current URL
    useEffect(() => {
        if (!opened) return;
        const fromUrl = params.get("group")
            ? params.get("group")!.split(",").filter(Boolean).map(Number)
            : [];
        setPending(fromUrl);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [opened]);

    const data = groups.map((g) => ({
        value: String(g.id),
        label: g.name,
        color: g.color,
        count: g.count
    }));

    function removeFromPending(id: number) {
        setPending((prev) => prev.filter((value) => value !== id));
    }

    function apply() {
        setParams((p) => {
            if (pending.length === 0) p.delete("group"); // "All"
            else p.set("group", pending.join(","));
            return p;
        });
        onClose();
    }

    const selectedGroups = pending
        .map((id) => groups.find((group) => group.id === id))
        .filter((group): group is ProjectGroupOption => Boolean(group));

    return (
        <Drawer opened={opened} onClose={apply} title="Projektgruppen" position="right" size="sm">
            <Stack>
                {error && (
                    <Alert color="red" variant="light" title="Projektgruppen konnten nicht geladen werden">
                        {error}
                    </Alert>
                )}

                <MultiSelect
                    data={data}
                    value={pending.map(String)}
                    onChange={(vals) => setPending(vals.map(Number))}
                    searchable
                    clearable
                    placeholder="Gruppen wählen…"
                    nothingFoundMessage={loading ? "Lade…" : error ? "Fehler beim Laden" : "Keine Treffer"}
                    disabled={loading && groups.length === 0}
                    rightSection={loading ? <Loader size="xs" /> : undefined}
                    renderOption={({ option }) => {
                        const anyOpt = option as unknown as { label: string; color?: string; count?: number };
                        return (
                            <Group gap="xs" wrap="nowrap">
                                <span
                                    aria-hidden
                                    style={{
                                        width: 10,
                                        height: 10,
                                        borderRadius: 999,
                                        background: anyOpt.color ?? "#ccc",
                                        display: "inline-block"
                                    }}
                                />
                                <span>{anyOpt.label}</span>
                                {typeof anyOpt.count === "number" && (
                                    <Badge size="xs" variant="light">{anyOpt.count}</Badge>
                                )}
                            </Group>
                        );
                    }}
                />

                {selectedGroups.length > 0 && (
                    <Group gap={8} wrap="wrap">
                        {selectedGroups.map((group) => (
                            <SelectedGroupPill
                                key={group.id}
                                group={group}
                                onRemove={() => removeFromPending(group.id)}
                                disabled={loading}
                            />
                        ))}
                    </Group>
                )}

                <Group justify="space-between" mt="md">
                    <Button variant="default" onClick={onClose}>
                        Abbrechen
                    </Button>
                    <Button color="petrol" onClick={apply} disabled={loading}>
                        Übernehmen
                    </Button>
                </Group>
            </Stack>
        </Drawer>
    );
}
