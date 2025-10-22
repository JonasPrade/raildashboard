import { Drawer, Stack, Button, Group, MultiSelect, Badge, CloseButton, type MultiSelectProps } from "@mantine/core";
import { useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";

export type ProjectGroupOption = {
    id: number;         // URL-Wert (?group=<id[,id2,...]>)
    name: string;       // Anzeigename
    color: string;      // HEX/RGB für Farbpunkt
    count?: number;     // optional: Anzahl Projekte
};

type Props = {
    opened: boolean;
    onClose: () => void;
    groups?: ProjectGroupOption[]; // später via API reinreichen
    loading?: boolean;
    error?: string;
};

// Fallback bis API angebunden ist
const FALLBACK_GROUPS: ProjectGroupOption[] = [
    { id: 1, name: "Ausbau",   color: "#22c55e" },
    { id: 2, name: "Neubau",   color: "#60a5fa" },
    { id: 3, name: "Knoten",   color: "#a78bfa" },
    { id: 4, name: "Korridor", color: "#f59e0b" },
    { id: 5, name: "Bahnhof",  color: "#f97316" },
    { id: 6, name: "Digital",  color: "#94a3b8" }
];

function SelectedValue(
  props: MultiSelectProps & { groups: ProjectGroupOption[] }
) {
  const { value, label, onRemove, disabled, groups } = props;
  const g = groups.find((gr) => String(gr.id) === value);

  return (
    <Group gap={6} wrap="nowrap" style={{
      border: "1px solid #2a3550",
      borderRadius: 8,
      padding: "2px 6px",
      background: "#142030"
    }}>
      <span
        aria-hidden
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: g?.color ?? "#ccc",
          display: "inline-block"
        }}
      />
      <span style={{ fontSize: 12 }}>{label}</span>
      {!disabled && (
        <CloseButton
          aria-label="Remove"
          onClick={onRemove}
          size="xs"
          variant="subtle"
        />)
      }
    </Group>
  );
}

export default function GroupFilterDrawer({
                                              opened,
                                              onClose,
                                              groups = FALLBACK_GROUPS,
                                              loading = false,
                                              error
                                          }: Props) {
    const [params, setParams] = useSearchParams();

    // Local (pending) selection stored as number[] because we want to store IDs as numbers
    const [pending, setPending] = useState<number[]>([]);

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

    function apply() {
        setParams((p) => {
            if (pending.length === 0) p.delete("group"); // "Alle"
            else p.set("group", pending.join(","));
            return p;
        });
        onClose();
    }

    return (
        <Drawer opened={opened} onClose={onClose} title="Projektgruppen" position="right" size="sm">
            <Stack>

                <MultiSelect
                    data={data}
                    value={pending.map(String)}
                    onChange={(vals) => setPending(vals.map(Number))}
                    searchable
                    clearable
                    placeholder="Gruppen wählen…"
                    nothingFoundMessage={loading ? "Lade…" : error ? "Fehler" : "Keine Treffer"}
                    valueComponent={(valueProps) => (
                      <SelectedValue {...valueProps} groups={groups} />
                    )}
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

                <Group justify="space-between" mt="md">
                    <Button variant="default" onClick={onClose}>
                        Abbrechen
                    </Button>
                    <Button color="petrol" onClick={apply}>
                        Übernehmen
                    </Button>
                </Group>
            </Stack>
        </Drawer>
    );
}