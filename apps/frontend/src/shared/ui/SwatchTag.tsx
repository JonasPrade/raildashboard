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
};

/**
 * Tag for a data category: outline badge in ink with a square in the category
 * colour and the label — colour is never the only signal (DESIGN.md).
 */
export function SwatchTag({ color, children, size = "sm", title, style }: SwatchTagProps) {
    return (
        <Badge
            size={size}
            variant="outline"
            radius={0}
            color="var(--text-strong)"
            leftSection={<Swatch color={color} />}
            title={title}
            style={{ textTransform: "none", ...style }}
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
