import { ActionIcon, Box, Button, Paper, Slider, Stack, Switch, Text, TextInput } from "@mantine/core";
import { IconSearch, IconX } from "@tabler/icons-react";

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
            <Paper p="sm" radius="md" shadow="sm" withBorder>
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
                    <Button size="sm" color="petrol" onClick={onOpenFilters}>
                        Projektgruppen
                    </Button>
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
            </Paper>
        </Box>
    );
}
