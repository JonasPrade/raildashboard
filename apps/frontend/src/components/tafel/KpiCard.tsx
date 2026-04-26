import type { CSSProperties, ReactNode } from "react";

type Props = {
    label: ReactNode;
    value: ReactNode;
    unit?: ReactNode;
    description?: ReactNode;
    /** Dark Tafel variant: gold value on board surface. Default: light KPI on warm-grey. */
    tone?: "light" | "dark";
    style?: CSSProperties;
};

export default function KpiCard({ label, value, unit, description, tone = "light", style }: Props) {
    const dark = tone === "dark";
    return (
        <div
            style={{
                background: dark ? "var(--board)" : "var(--bg2)",
                color: dark ? "#f5f3ed" : "var(--ink)",
                padding: "24px 20px",
                position: "relative",
                borderLeft: `3px solid ${dark ? "var(--ledHot)" : "var(--info)"}`,
                ...style,
            }}
        >
            <div
                style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    letterSpacing: "0.16em",
                    color: dark ? "#a8adb5" : "var(--ink3)",
                    textTransform: "uppercase",
                    fontWeight: 700,
                }}
            >
                {label}
            </div>
            <div
                style={{
                    fontFamily: "var(--font-display)",
                    fontSize: 56,
                    fontWeight: 700,
                    color: dark ? "var(--ledHot)" : "var(--info)",
                    lineHeight: 0.9,
                    letterSpacing: "-0.03em",
                    margin: "14px 0 8px",
                }}
            >
                {value}
                {unit && (
                    <span style={{ fontSize: 28, color: dark ? "#a8adb5" : "var(--ink3)" }}>
                        {unit}
                    </span>
                )}
            </div>
            {description && (
                <div
                    style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        color: dark ? "#b5bac2" : "var(--ink2)",
                        lineHeight: 1.55,
                    }}
                >
                    {description}
                </div>
            )}
        </div>
    );
}
