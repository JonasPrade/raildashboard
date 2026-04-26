import type { CSSProperties, ReactNode } from "react";

type Props = {
    children: ReactNode;
    color?: "ink" | "led" | "info";
    style?: CSSProperties;
};

const colorMap = {
    ink:  "var(--ink3)",
    led:  "var(--led)",
    info: "var(--info)",
} as const;

export default function Eyebrow({ children, color = "ink", style }: Props) {
    return (
        <div
            style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                letterSpacing: "0.18em",
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
