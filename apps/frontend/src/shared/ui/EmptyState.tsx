import type { ReactNode } from "react";
import { Box, Text } from "@mantine/core";

export type EmptyStateProps = {
    /** Short heading, e.g. "Keine Projekte". */
    title: string;
    /** One sentence explaining the state. */
    children?: ReactNode;
    /** The one action that helps (usually a `<Button variant="default">`). */
    action?: ReactNode;
};

/** Empty state (Anwendungsebene „Leer“): heading, one sentence, one action. */
export function EmptyState({ title, children, action }: EmptyStateProps) {
    return (
        <Box
            data-state="empty"
            style={{
                border: "2px solid var(--border-frame)",
                background: "var(--surface)",
                padding: 24,
            }}
        >
            <Text component="h3" m={0} fw={700} style={{ fontSize: 17, color: "var(--text-strong)" }}>
                {title}
            </Text>
            {children && (
                <Text mt={6} style={{ fontSize: 14.5, color: "var(--text-muted)" }}>
                    {children}
                </Text>
            )}
            {action && <Box mt={16}>{action}</Box>}
        </Box>
    );
}
