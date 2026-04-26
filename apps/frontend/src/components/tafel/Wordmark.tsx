import type { CSSProperties, ReactNode } from "react";

type Size = "lg" | "md" | "sm";

type Props = {
    size?: Size;
    inverse?: boolean;
    children?: ReactNode;
    style?: CSSProperties;
};

const sizeMap: Record<Size, { fontSize: string; lineHeight: string }> = {
    lg: { fontSize: "48px", lineHeight: "1" },
    md: { fontSize: "28px", lineHeight: "1" },
    sm: { fontSize: "18px", lineHeight: "1" },
};

export default function Wordmark({ size = "md", inverse, children = "Schienendashboard", style }: Props) {
    const s = sizeMap[size];
    return (
        <span
            style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "-0.015em",
                color: inverse ? "#f5f3ed" : "var(--ink)",
                background: inverse ? "var(--ink)" : "transparent",
                padding: inverse ? "10px 14px" : 0,
                display: "inline-flex",
                alignItems: "baseline",
                gap: 2,
                ...s,
                ...style,
            }}
        >
            {children}
            <span style={{ color: inverse ? "var(--ledHot)" : "var(--led)" }}>.</span>
        </span>
    );
}
