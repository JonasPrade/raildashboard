import { Box, Button, Group, Paper } from "@mantine/core";

export default function MapControls({ onOpenFilters }: { onOpenFilters: () => void }) {
    // Absolute overlay, sits on top of the map
    return (
        <Box
            style={{
                position: "absolute",
                top: 12,
                right: 30,
                zIndex: 10, // above map
            }}
        >
            <Paper p="xs" radius="md" shadow="sm" withBorder>
                <Group gap="xs">
                    <Button size="sm" color="petrol" onClick={onOpenFilters}>
                        Projektgruppen
                    </Button>
                    {/* space for more controls later: locate, layers, etc. */}
                </Group>
            </Paper>
        </Box>
    );
}
