import { useCallback, useEffect, useState } from "react";
import { ActionIcon, Stack, Text, Tooltip, UnstyledButton } from "@mantine/core";

export interface TocSection {
    id: string;
    label: string;
    ref: React.RefObject<HTMLDivElement | null>;
    visible: boolean;
    /** Section is hidden behind a Collapse — clicking should expand it first */
    isCollapsible?: boolean;
    isOpen?: boolean;
    onOpen?: () => void;
}

interface Props {
    sections: TocSection[];
    /** When provided, renders a second left-edge icon that creates a task. */
    onCreateTask?: () => void;
}

// Minimal inline SVG icons – no external icon library needed
function IconMenu() {
    return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
    );
}

function IconClose() {
    return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
    );
}

// Checklist with a plus – "create task"
function IconTaskAdd() {
    return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 5h12" />
            <path d="M3 12h8" />
            <path d="M3 19h8" />
            <path d="M17 14v6" />
            <path d="M14 17h6" />
        </svg>
    );
}

export function ProjectTableOfContents({ sections, onCreateTask }: Props) {
    const [open, setOpen] = useState(false);
    const [activeId, setActiveId] = useState<string | null>(null);

    // Track which section is currently visible using IntersectionObserver.
    // The topmost intersecting section in document order becomes "active".
    useEffect(() => {
        const visibleSections = sections.filter((s) => s.visible && s.ref.current);
        const intersecting = new Map<string, boolean>();
        const observers: IntersectionObserver[] = [];

        visibleSections.forEach(({ id, ref }) => {
            if (!ref.current) return;

            const obs = new IntersectionObserver(
                ([entry]) => {
                    intersecting.set(id, entry.isIntersecting);
                    const first = visibleSections.find((s) => intersecting.get(s.id));
                    setActiveId(first?.id ?? null);
                },
                // Trigger when the top portion of a section crosses the upper viewport region
                { rootMargin: "0px 0px -70% 0px", threshold: 0 },
            );

            obs.observe(ref.current);
            observers.push(obs);
        });

        return () => observers.forEach((o) => o.disconnect());
    }, [sections]);

    const handleClick = useCallback((section: TocSection) => {
        if (section.isCollapsible && !section.isOpen && section.onOpen) {
            // Open the collapsed section first, then scroll after the animation settles
            section.onOpen();
            setTimeout(() => {
                section.ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 200);
        } else {
            section.ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }, []);

    const visibleSections = sections.filter((s) => s.visible);
    if (visibleSections.length === 0) return null;

    return (
        <div
            style={{
                position: "fixed",
                left: 0,
                top: "50%",
                transform: "translateY(-50%)",
                zIndex: 200,
                display: "flex",
                alignItems: "flex-start",
            }}
        >
            {/* Left-edge icon column: TOC toggle + optional "create task" */}
            <Stack gap={6}>
                <Tooltip label={open ? "Schließen" : "Inhaltsverzeichnis"} position="right" withArrow>
                    <ActionIcon
                        variant="filled"
                        color="preussen"
                        size={42}
                        radius={0}
                        style={{ borderRadius: "0 6px 6px 0" }}
                        onClick={() => setOpen((o) => !o)}
                        aria-label={open ? "Inhaltsverzeichnis schließen" : "Inhaltsverzeichnis öffnen"}
                    >
                        {open ? <IconClose /> : <IconMenu />}
                    </ActionIcon>
                </Tooltip>

                {onCreateTask && (
                    <Tooltip label="Aufgabe erstellen" position="right" withArrow>
                        <ActionIcon
                            variant="filled"
                            color="preussen"
                            size={42}
                            radius={0}
                            style={{ borderRadius: "0 6px 6px 0" }}
                            onClick={onCreateTask}
                            aria-label="Aufgabe erstellen"
                        >
                            <IconTaskAdd />
                        </ActionIcon>
                    </Tooltip>
                )}
            </Stack>

            {/* Section list panel */}
            {open && (
                <div style={{
                    minWidth: 200,
                    background: "var(--bg)",
                    border: "1px solid var(--rule)",
                    boxShadow: "var(--shadow-float)",
                    borderRadius: 0,
                    padding: "8px",
                }}>
                    <Stack gap={2}>
                        {visibleSections.map((section) => (
                            <UnstyledButton
                                key={section.id}
                                onClick={() => handleClick(section)}
                                style={{
                                    padding: "5px 8px",
                                    borderRadius: 0,
                                    backgroundColor:
                                        activeId === section.id
                                            ? "var(--bg2)"
                                            : undefined,
                                    transition: "background-color 100ms ease",
                                }}
                            >
                                <Text size="sm" fw={activeId === section.id ? 600 : 400}>
                                    {section.label}
                                </Text>
                            </UnstyledButton>
                        ))}
                    </Stack>
                </div>
            )}
        </div>
    );
}
