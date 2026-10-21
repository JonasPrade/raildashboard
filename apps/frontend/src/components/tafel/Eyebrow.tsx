import type { CSSProperties, ReactNode } from "react";

type Props = {
    children: ReactNode;
    color?: "ink" | "led" | "info";
    style?: CSSProperties;
};

const colorMap = {
    ink:  "var(--text-muted)",
    led:  "var(--text-link)",
    info: "var(--text-strong)",
} as const;

export default function Eyebrow({ children, color = "ink", style }: Props) {
    return (
        <div
            style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                letterSpacing: "var(--ls-label)",
                textTransform: "uppercase",
                color: colorMap[color],
                fontWeight: 700,
                ...style,
            }}
        >
            ▸ {children}
        </div>
    );
}
