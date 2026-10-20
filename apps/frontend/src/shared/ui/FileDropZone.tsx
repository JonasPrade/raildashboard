import { Box, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useRef, useState, type DragEvent, type ReactNode } from "react";

import { matchesAccept } from "./fileAccept";

type FileDropZoneProps = {
    /** Same format as the `accept` attribute of a file input. */
    accept?: string;
    /** Allow more than one file per drop; otherwise only the first file is passed on. */
    multiple?: boolean;
    /** Receives the accepted files of a drop (never empty). */
    onFiles: (files: File[]) => void;
    /** Text shown while a file is dragged over the zone. */
    label?: string;
    disabled?: boolean;
    children: ReactNode;
};

/**
 * Makes its children a drop target for files, as an addition to the file
 * picker inside it. While a file is dragged over, a dashed overlay marks the
 * zone; files that do not match `accept` are rejected with a notification.
 */
export function FileDropZone({ accept, multiple = false, onFiles, label = "Datei hier ablegen", disabled, children }: FileDropZoneProps) {
    const [active, setActive] = useState(false);
    // dragenter/dragleave also fire when moving across child elements — count them
    // so the overlay only disappears once the pointer has really left the zone.
    const depth = useRef(0);

    function carriesFiles(event: DragEvent) {
        return Array.from(event.dataTransfer.types).includes("Files");
    }

    function handleDragEnter(event: DragEvent<HTMLDivElement>) {
        if (disabled || !carriesFiles(event)) return;
        event.preventDefault();
        depth.current += 1;
        setActive(true);
    }

    function handleDragOver(event: DragEvent<HTMLDivElement>) {
        if (disabled || !carriesFiles(event)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
    }

    function handleDragLeave(event: DragEvent<HTMLDivElement>) {
        if (disabled || !carriesFiles(event)) return;
        depth.current = Math.max(0, depth.current - 1);
        if (depth.current === 0) setActive(false);
    }

    function handleDrop(event: DragEvent<HTMLDivElement>) {
        if (disabled || !carriesFiles(event)) return;
        event.preventDefault();
        depth.current = 0;
        setActive(false);

        const dropped = Array.from(event.dataTransfer.files);
        const accepted = dropped.filter((file) => matchesAccept(file, accept));
        const rejected = dropped.filter((file) => !matchesAccept(file, accept));
        if (rejected.length > 0) {
            notifications.show({
                color: "red",
                title: "Dateityp nicht unterstützt",
                message: rejected.map((file) => `„${file.name}"`).join(", "),
            });
        }
        if (accepted.length === 0) return;
        onFiles(multiple ? accepted : accepted.slice(0, 1));
    }

    return (
        <Box
            pos="relative"
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {children}
            {active && (
                <Box
                    data-testid="file-drop-overlay"
                    pos="absolute"
                    inset={-6}
                    style={{
                        border: "2px dashed var(--mantine-color-blue-6)",
                        borderRadius: "var(--mantine-radius-md)",
                        background: "color-mix(in srgb, var(--mantine-color-blue-6) 10%, var(--mantine-color-body))",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        pointerEvents: "none",
                        zIndex: 10,
                    }}
                >
                    <Text size="sm" fw={600} c="blue.7">{label}</Text>
                </Box>
            )}
        </Box>
    );
}
