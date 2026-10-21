import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { Drawer } from "@mantine/core";
import { ChevronLeft, ChevronRight, ListPlus, Menu } from "lucide-react";
import { useIsCompact } from "../../shared/hooks/useBreakpoint";
import "./ProjectRegister.css";

/**
 * Left-edge register of the project page (Anwendungsebene, feature-idt-design.md
 * → Q26). From 62em a sticky 240px column next to the content that folds into a
 * 26px tab; below that a fixed 44px button „Abschnitte“ that opens the same list
 * as a bottom drawer.
 *
 * Place it as the first child of an element with the class
 * `project-register-layout`; the grid there sizes its column to the register.
 */

export interface RegisterSection {
    id: string;
    label: string;
    ref: RefObject<HTMLDivElement | null>;
    visible: boolean;
    /** Section is hidden behind a Collapse — clicking should expand it first */
    isCollapsible?: boolean;
    isOpen?: boolean;
    onOpen?: () => void;
    /** 2 = indented sub-entry under the preceding section. */
    level?: 1 | 2;
}

interface Props {
    sections: RegisterSection[];
    /** When provided, the register ends with an „Aufgabe erstellen“ action. */
    onCreateTask?: () => void;
}

export const REGISTER_STORAGE_KEY = "schienendashboard.register";

function readCollapsed(): boolean {
    try {
        return window.localStorage.getItem(REGISTER_STORAGE_KEY) === "closed";
    } catch {
        return false;
    }
}

function writeCollapsed(collapsed: boolean) {
    try {
        window.localStorage.setItem(REGISTER_STORAGE_KEY, collapsed ? "closed" : "open");
    } catch {
        // Private mode or blocked storage: the register still works, it just forgets.
    }
}

/**
 * Tracks which section is currently in view. The topmost intersecting section
 * in document order becomes "active".
 */
function useActiveSection(sections: RegisterSection[]): string | null {
    const [activeId, setActiveId] = useState<string | null>(null);

    useEffect(() => {
        if (typeof IntersectionObserver === "undefined") return;
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

    return activeId;
}

function scrollToSection(section: RegisterSection) {
    if (section.isCollapsible && !section.isOpen && section.onOpen) {
        // Open the collapsed section first, then scroll after the animation settles
        section.onOpen();
        setTimeout(() => {
            section.ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 200);
    } else {
        section.ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

interface ListProps {
    sections: RegisterSection[];
    activeId: string | null;
    onSelect: (section: RegisterSection) => void;
    onCreateTask?: () => void;
}

function RegisterList({ sections, activeId, onSelect, onCreateTask }: ListProps) {
    return (
        <>
            <ul className="project-register__list">
                {sections.map((section) => {
                    const active = activeId === section.id;
                    return (
                        <li key={section.id}>
                            <button
                                type="button"
                                className="project-register__entry"
                                data-active={active || undefined}
                                data-level={section.level === 2 ? 2 : undefined}
                                aria-current={active ? "location" : undefined}
                                onClick={() => onSelect(section)}
                            >
                                {section.label}
                            </button>
                        </li>
                    );
                })}
            </ul>
            {onCreateTask && (
                <button type="button" className="project-register__action" onClick={onCreateTask}>
                    <ListPlus size={16} strokeWidth={2} aria-hidden="true" />
                    Aufgabe erstellen
                </button>
            )}
        </>
    );
}

export function ProjectRegister({ sections, onCreateTask }: Props) {
    const isCompact = useIsCompact();
    const activeId = useActiveSection(sections);
    const [collapsed, setCollapsed] = useState(readCollapsed);
    const [drawerOpen, setDrawerOpen] = useState(false);
    // Section picked in the drawer; scrolled to once the drawer has closed and
    // released the scroll lock.
    const pendingRef = useRef<RegisterSection | null>(null);

    const toggleCollapsed = useCallback((next: boolean) => {
        setCollapsed(next);
        writeCollapsed(next);
    }, []);

    const visibleSections = sections.filter((s) => s.visible);
    if (visibleSections.length === 0) return null;

    if (isCompact) {
        return (
            <>
                <button
                    type="button"
                    className="project-register-button"
                    aria-haspopup="dialog"
                    aria-expanded={drawerOpen}
                    onClick={() => setDrawerOpen(true)}
                >
                    <Menu size={20} strokeWidth={2} aria-hidden="true" />
                    Abschnitte
                </button>
                <Drawer
                    opened={drawerOpen}
                    onClose={() => setDrawerOpen(false)}
                    onExitTransitionEnd={() => {
                        const pending = pendingRef.current;
                        pendingRef.current = null;
                        if (pending) scrollToSection(pending);
                    }}
                    position="bottom"
                    title={<span className="idt-eyebrow">Abschnitte</span>}
                    classNames={{ content: "project-register-drawer", body: "project-register-drawer__body" }}
                >
                    <nav aria-label="Abschnitte" className="project-register project-register--sheet">
                        <RegisterList
                            sections={visibleSections}
                            activeId={activeId}
                            onSelect={(section) => {
                                pendingRef.current = section;
                                setDrawerOpen(false);
                            }}
                            onCreateTask={
                                onCreateTask
                                    ? () => {
                                          setDrawerOpen(false);
                                          onCreateTask();
                                      }
                                    : undefined
                            }
                        />
                    </nav>
                </Drawer>
            </>
        );
    }

    if (collapsed) {
        return (
            <div className="project-register-slot">
                <button
                    type="button"
                    className="project-register-tab"
                    aria-expanded={false}
                    aria-label="Abschnitte aufklappen"
                    onClick={() => toggleCollapsed(false)}
                >
                    <ChevronRight size={16} strokeWidth={2} aria-hidden="true" />
                    <span className="project-register-tab__label">Abschnitte</span>
                </button>
            </div>
        );
    }

    return (
        <div className="project-register-slot">
            <nav aria-label="Abschnitte" className="project-register">
                <div className="project-register__head">
                    <span className="idt-eyebrow">Abschnitte</span>
                    <button
                        type="button"
                        className="project-register__collapse"
                        aria-expanded={true}
                        aria-label="Abschnitte einklappen"
                        onClick={() => toggleCollapsed(true)}
                    >
                        <ChevronLeft size={16} strokeWidth={2} aria-hidden="true" />
                    </button>
                </div>
                <RegisterList
                    sections={visibleSections}
                    activeId={activeId}
                    onSelect={scrollToSection}
                    onCreateTask={onCreateTask}
                />
            </nav>
        </div>
    );
}
