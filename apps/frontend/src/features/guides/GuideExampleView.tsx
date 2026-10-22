import type { ReactNode } from "react";
import { Badge, Box, Group, Text } from "@mantine/core";

/**
 * Frame for an illustrative UI mock inside a guide step. The content is a
 * static, non-interactive replica of the real screen (pointer events off), so
 * readers see what to expect without accidentally "using" the example.
 */
export default function GuideExampleView({
    children,
    caption,
}: {
    children: ReactNode;
    caption?: string;
}) {
    return (
        <Box mt="sm">
            <Group gap={6} mb={6} align="center">
                <Badge variant="outline">Beispielansicht</Badge>
                <Text size="xs" c="dimmed">
                    {caption ?? "vereinfachte, nicht interaktive Darstellung"}
                </Text>
            </Group>
            <Box
                p="md"
                aria-hidden
                style={{
                    border: "1px dashed var(--border-strong)",
                    pointerEvents: "none",
                    userSelect: "none",
                    overflowX: "auto",
                }}
            >
                {children}
            </Box>
        </Box>
    );
}
