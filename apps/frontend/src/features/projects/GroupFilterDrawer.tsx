import { Alert, Drawer, Stack, Button, Group, Text, Loader, UnstyledButton } from "@mantine/core";
import { ChronicleDataChip } from "../../components/chronicle";
import { useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";

export type ProjectGroupOption = {
    id: number;
    name: string;
    color: string;
    count?: number;
};

type Props = {
    opened: boolean;
    onClose: () => void;
    groups?: ProjectGroupOption[];
    loading?: boolean;
    error?: string;
};

export default function GroupFilterDrawer({ opened, onClose, groups = [], loading = false, error }: Props) {
    const [params, setParams] = useSearchParams();
    const [pending, setPending] = useState<number[]>([]);

    useEffect(() => {
        setPending((prev) => prev.filter((id) => groups.some((g) => g.id === id)));
    }, [groups]);

    useEffect(() => {
        if (!opened) return;
        const fromUrl = params.get("group")
            ? params.get("group")!.split(",").filter(Boolean).map(Number)
            : [];
        setPending(fromUrl);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [opened]);

    function toggle(id: number) {
        setPending((prev) =>
            prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id],
        );
    }

    function apply() {
        setParams((p) => {
            if (pending.length === 0) p.delete("group");
            else p.set("group", pending.join(","));
            return p;
        });
        onClose();
    }

    return (
        <Drawer opened={opened} onClose={apply} title="Projektgruppen" position="right" size="sm">
            <Stack gap="xs">
                {error && (
                    <Alert color="red" variant="light" title="Projektgruppen konnten nicht geladen werden">
                        {error}
                    </Alert>
                )}

                {loading && groups.length === 0 ? (
                    <Group justify="center" py="xl">
                        <Loader size="sm" />
                    </Group>
                ) : (
                    groups.map((group) => {
                        const selected = pending.includes(group.id);
                        return (
                            <UnstyledButton
                                key={group.id}
                                onClick={() => toggle(group.id)}
                                disabled={loading}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 10,
                                    padding: "10px 12px",
                                    borderRadius: 8,
                                    border: selected ? `2px solid ${group.color}` : "2px solid transparent",
                                    background: selected ? `${group.color}18` : "var(--mantine-color-default)",
                                    outline: "1px solid var(--mantine-color-default-border)",
                                    cursor: "pointer",
                                    transition: "background 120ms, border-color 120ms",
                                }}
                            >
                                <span
                                    aria-hidden
                                    style={{
                                        width: 12,
                                        height: 12,
                                        borderRadius: "50%",
                                        background: group.color,
                                        flexShrink: 0,
                                    }}
                                />
                                <Text size="sm" style={{ flex: 1 }}>{group.name}</Text>
                                {typeof group.count === "number" && (
                                    <ChronicleDataChip>{group.count}</ChronicleDataChip>
                                )}
                            </UnstyledButton>
                        );
                    })
                )}

                <Group justify="space-between" mt="md">
                    <Button variant="default" onClick={onClose}>Abbrechen</Button>
                    <Button color="preussen" onClick={apply} disabled={loading}>Übernehmen</Button>
                </Group>
            </Stack>
        </Drawer>
    );
}
