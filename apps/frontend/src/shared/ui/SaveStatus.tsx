import { Box, Group, Text, UnstyledButton } from "@mantine/core";
import { Check } from "lucide-react";

export type SaveStatusProps = {
    state: "saved" | "saving" | "error";
    savedAt?: Date;
    onRetry?: () => void;
};

function formatTime(date: Date): string {
    return date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

/** Save feedback in the view header (Anwendungsebene „Bearbeiten und Speichern“). */
export function SaveStatus({ state, savedAt, onRetry }: SaveStatusProps) {
    const isError = state === "error";
    return (
        <Box
            role="status"
            aria-live="polite"
            data-state={state}
            style={{
                display: "inline-block",
                border: "2px solid var(--border-frame)",
                background: "var(--surface)",
                boxShadow: isError ? "inset 4px 0 0 var(--idt-danger)" : undefined,
                padding: isError ? "4px 10px 4px 14px" : "4px 10px",
                fontSize: 15,
            }}
        >
            {state === "saved" && (
                <Group gap={6} wrap="nowrap" style={{ color: "var(--text-muted)" }}>
                    <Check size={16} aria-hidden />
                    <Text span inherit>
                        gespeichert{savedAt ? ` ${formatTime(savedAt)}` : ""}
                    </Text>
                </Group>
            )}
            {state === "saving" && (
                <Text span inherit style={{ color: "var(--text-muted)" }}>
                    schreibt …
                </Text>
            )}
            {isError && (
                <Group gap={12} wrap="nowrap">
                    <Text span inherit fw={700} style={{ color: "var(--text-strong)" }}>
                        nicht gespeichert
                    </Text>
                    {onRetry && (
                        <UnstyledButton
                            onClick={onRetry}
                            style={{ fontSize: 15, color: "var(--accent-primary)", textDecoration: "underline" }}
                        >
                            erneut
                        </UnstyledButton>
                    )}
                </Group>
            )}
        </Box>
    );
}
