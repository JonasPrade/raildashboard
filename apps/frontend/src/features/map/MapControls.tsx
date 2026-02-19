import { Box, Button, Group, Paper, Slider, Stack, Text } from "@mantine/core";

type Props = {
    onOpenFilters: () => void;
    lineWidth: number;
    onLineWidthChange: (value: number) => void;
    pointSize: number;
    onPointSizeChange: (value: number) => void;
};

export default function MapControls({ onOpenFilters, lineWidth, onLineWidthChange, pointSize, onPointSizeChange }: Props) {
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
            <Paper p="sm" radius="md" shadow="sm" withBorder>
                <Stack gap="sm">
                    <Button size="sm" color="petrol" onClick={onOpenFilters}>
                        Projektgruppen
                    </Button>
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
