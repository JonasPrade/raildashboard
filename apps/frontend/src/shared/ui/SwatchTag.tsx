import type { CSSProperties, ReactNode } from "react";
import { Badge, type BadgeProps } from "@mantine/core";
import { Check } from "lucide-react";

import { STATUS_TONE, type StatusTone } from "../theme/semanticColors";

/** 9px square in a data-category colour (phase, traffic type, source). */
export function Swatch({ color, size = 9 }: { color: string; size?: number }) {
    return (
        <span
            aria-hidden
            style={{
                display: "inline-block",
                width: size,
                height: size,
                flex: "0 0 auto",
                background: color,
                // Light ramp steps (seq-1) need an edge to reach 3:1 on paper.
                boxShadow: "inset 0 0 0 1px var(--border-strong)",
            }}
        />
    );
}

type SwatchTagProps = {
    /** CSS colour value from semanticColors.ts. */
    color: string;
    children: ReactNode;
    size?: BadgeProps["size"];
    title?: string;
    style?: CSSProperties;
    /** Paused/aborted context: muted text, the square keeps its colour. */
    muted?: boolean;
    /** Category does not apply: muted text and an empty square. Both replace
     *  fading the tag — opacity would drop the text below 4.5:1. */
    inactive?: boolean;
};

/**
 * Tag for a data category: outline badge in ink with a square in the category
 * colour and the label — colour is never the only signal (DESIGN.md). Caps like
 * every Badge (11.5/600, .06em; theme → components.css).
 */
export function SwatchTag({ color, children, size = "sm", title, style, muted = false, inactive = false }: SwatchTagProps) {
    return (
        <Badge
            size={size}
            variant="outline"
            radius={0}
            color={muted || inactive ? "var(--text-muted)" : "var(--text-strong)"}
            leftSection={<Swatch color={inactive ? "transparent" : color} />}
            title={title}
            style={style}
        >
            {children}
        </Badge>
    );
}

type StatusTagProps = {
    tone: StatusTone;
    children: ReactNode;
    size?: BadgeProps["size"];
    title?: string;
};

/**
 * Tag for a workflow status (Anwendungsebene "Status"): neutral and active
 * stay without colour weight, done carries a check, only danger is red.
 */
export function StatusTag({ tone, children, size = "sm", title }: StatusTagProps) {
    return (
        <Badge
            size={size}
            variant="outline"
            radius={0}
            color={STATUS_TONE[tone]}
            leftSection={tone === "done" ? <Check size={12} aria-hidden /> : undefined}
            title={title}
        >
            {children}
        </Badge>
    );
}
