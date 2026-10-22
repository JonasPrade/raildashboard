import type { ReactNode } from "react";
import { Box, Button, Text } from "@mantine/core";
import { RefreshCw } from "lucide-react";

export type ErrorStateProps = {
    title?: string;
    /** One sentence explaining what failed. */
    children?: ReactNode;
    /** Retry handler, usually React Query's `refetch`. */
    onRetry?: () => void;
};

/** Error state (Anwendungsebene „Fehler“): red inner edge, heading, sentence, retry. */
export function ErrorState({ title = "Laden fehlgeschlagen", children, onRetry }: ErrorStateProps) {
    return (
        <Box
            role="alert"
            data-state="error"
            style={{
                border: "2px solid var(--border-frame)",
                background: "var(--surface)",
                boxShadow: "inset 4px 0 0 var(--idt-danger)",
                padding: "24px 24px 24px 28px",
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
            {onRetry && (
                <Button
                    mt={16}
                    variant="default"
                    leftSection={<RefreshCw size={16} aria-hidden />}
                    onClick={onRetry}
                >
                    Erneut versuchen
                </Button>
            )}
        </Box>
    );
}
