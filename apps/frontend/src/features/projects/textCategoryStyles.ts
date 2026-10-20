import type { Icon } from "@tabler/icons-react";
import { IconAlertOctagon, IconAlertTriangle, IconInfoCircle, IconNote } from "@tabler/icons-react";

import type { ProjectText, ProjectTextCategory } from "../../shared/api/queries";

/**
 * Display of the fixed text-category styles — the one place to change icon or
 * border per style. Colours come from the semantic tokens `--text-cat-*` in
 * tokens.css, so recolouring a style never touches components.
 * See docs/features/feature-text-categories.md.
 */
export type TextCategoryStyle = ProjectTextCategory["style"];

type StyleDisplay = {
    label: string;
    color: string;
    icon: Icon;
    /** Left border on the text card — only for styles that need attention. */
    border: boolean;
};

export const TEXT_CATEGORY_STYLES: Record<TextCategoryStyle, StyleDisplay> = {
    neutral: { label: "Neutral", color: "var(--text-cat-neutral)", icon: IconNote, border: false },
    info: { label: "Info", color: "var(--text-cat-info)", icon: IconInfoCircle, border: false },
    warning: { label: "Warnung", color: "var(--text-cat-warning)", icon: IconAlertTriangle, border: true },
    critical: { label: "Kritisch", color: "var(--text-cat-critical)", icon: IconAlertOctagon, border: true },
};

export const TEXT_CATEGORY_STYLE_ORDER: TextCategoryStyle[] = ["neutral", "info", "warning", "critical"];

const DEFAULT_CATEGORY_NAME = "Info";

/** „Info“, or the oldest category — mirrors the backend default. */
export function defaultCategory(categories: ProjectTextCategory[] | undefined): ProjectTextCategory | null {
    if (!categories || categories.length === 0) return null;
    return (
        categories.find((c) => c.name.toLowerCase() === DEFAULT_CATEGORY_NAME.toLowerCase()) ??
        [...categories].sort((a, b) => a.id - b.id)[0]
    );
}

/** Texts written before categories existed carry none and show as the default. */
export function categoryOf(
    text: ProjectText,
    categories: ProjectTextCategory[] | undefined,
): ProjectTextCategory | null {
    return text.category ?? defaultCategory(categories);
}
