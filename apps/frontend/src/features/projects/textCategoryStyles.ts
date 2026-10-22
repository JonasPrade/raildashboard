import type { LucideIcon } from "lucide-react";
import { OctagonAlert, TriangleAlert, Info, FileText } from "lucide-react";

import type { ProjectText, ProjectTextCategory } from "../../shared/api/queries";
import { TEXT_CATEGORY_STYLE } from "../../shared/theme/semanticColors";

/**
 * Display of the fixed text-category styles. Edge and icon colour come from
 * `TEXT_CATEGORY_STYLE` in shared/theme/semanticColors.ts (W5); this map only
 * adds the German label and resolves the Lucide icon.
 * See docs/features/feature-text-categories.md.
 */
export type TextCategoryStyle = ProjectTextCategory["style"];

type StyleDisplay = {
    label: string;
    icon: LucideIcon;
    /** Icon colour — ink, only `critical` red. */
    iconColor: string;
    /** 8px left edge of the text card in the status colour; null = no edge. */
    edge: string | null;
};

const ICONS: Record<(typeof TEXT_CATEGORY_STYLE)[TextCategoryStyle]["icon"], LucideIcon> = {
    FileText,
    Info,
    TriangleAlert,
    OctagonAlert,
};

const LABELS: Record<TextCategoryStyle, string> = {
    neutral: "Neutral",
    info: "Info",
    warning: "Warnung",
    critical: "Kritisch",
};

export const TEXT_CATEGORY_STYLE_ORDER: TextCategoryStyle[] = ["neutral", "info", "warning", "critical"];

export const TEXT_CATEGORY_STYLES: Record<TextCategoryStyle, StyleDisplay> = Object.fromEntries(
    TEXT_CATEGORY_STYLE_ORDER.map((style) => {
        const def = TEXT_CATEGORY_STYLE[style];
        return [style, { label: LABELS[style], icon: ICONS[def.icon], iconColor: def.iconColor, edge: def.edge }];
    }),
) as Record<TextCategoryStyle, StyleDisplay>;

/** Width of the text card's left edge (DS callout). */
export const TEXT_CATEGORY_EDGE_WIDTH = 8;

/** Card style of a text: 8px edge in the style colour, no frame, no fill (DS callout). */
export function textCardStyle(edge: string | null): { borderLeft: string; paddingLeft: number } {
    return {
        borderLeft: edge ? `${TEXT_CATEGORY_EDGE_WIDTH}px solid ${edge}` : `${TEXT_CATEGORY_EDGE_WIDTH}px solid transparent`,
        paddingLeft: 16,
    };
}

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
