import { ActionIcon, Box, Slider, Stack, Switch, Text, TextInput } from "@mantine/core";
import { IconSearch, IconX } from "@tabler/icons-react";
import { ChronicleButton } from "../../components/chronicle";
import "../../components/chronicle/tokens.css";

type Props = {
    onOpenFilters: () => void;
    lineWidth: number;
    onLineWidthChange: (value: number) => void;
    pointSize: number;
    onPointSizeChange: (value: number) => void;
    onlySuperior: boolean;
    onOnlySuperiorChange: (value: boolean) => void;
    searchTerm: string;
    onSearchChange: (value: string) => void;
    totalProjects: number;
    filteredCount: number;
};

export default function MapControls({
    onOpenFilters,
    lineWidth,
    onLineWidthChange,
    pointSize,
    onPointSizeChange,
    onlySuperior,
    onOnlySuperiorChange,
    searchTerm,
    onSearchChange,
    totalProjects,
    filteredCount,
}: Props) {
    return (
        <Box
            style={{
                position: "absolute",
                top: 12,
                right: 30,
                zIndex: 10,
            }}
        >
            <div
                className="chronicle-theme"
                style={{
                    background: "rgba(251, 249, 248, 0.85)",
                    backdropFilter: "blur(20px)",
                    WebkitBackdropFilter: "blur(20px)",
                    borderRadius: "var(--radius-sharp)",
                    boxShadow: "var(--shadow-float)",
                    padding: "12px",
                    border: "1px solid var(--c-outline-ghost)",
                }}
            >
                <Stack gap="sm">
                    <TextInput
                        placeholder="Projekt suchen…"
                        leftSection={<IconSearch size={14} />}
                        rightSection={
                            searchTerm ? (
                                <ActionIcon variant="subtle" size="xs" onClick={() => onSearchChange("")}>
                                    <IconX size={12} />
                                </ActionIcon>
                            ) : undefined
                        }
                        value={searchTerm}
                        onChange={(e) => onSearchChange(e.currentTarget.value)}
                        size="sm"
                        style={{ width: 180 }}
                    />
                    {searchTerm && (
                        <Text size="xs" c="dimmed">
                            {filteredCount} von {totalProjects} Projekten
                        </Text>
                    )}
                    <ChronicleButton onClick={onOpenFilters}>
                        Projektgruppen
                    </ChronicleButton>
                    <Switch
                        label="Nur Hauptprojekte"
                        checked={onlySuperior}
                        onChange={(e) => onOnlySuperiorChange(e.currentTarget.checked)}
                        size="sm"
                    />
                    <Stack gap={4}>
                        <Text size="xs" c="dimmed">
                            Linienbreite: {lineWidth} px
                        </Text>
                        <Slider
                            value={lineWidth}
                            onChange={onLineWidthChange}
                            min={1}
                            max={10}
                            step={1}
                            size="sm"
                            style={{ width: 140 }}
                        />
                    </Stack>
                    <Stack gap={4}>
                        <Text size="xs" c="dimmed">
                            Punktgröße: {pointSize} px
                        </Text>
                        <Slider
                            value={pointSize}
                            onChange={onPointSizeChange}
                            min={1}
                            max={15}
                            step={1}
                            size="sm"
                            style={{ width: 140 }}
                        />
                    </Stack>
                </Stack>
            </div>
        </Box>
    );
}
