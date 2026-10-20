import type { ReactNode, CSSProperties } from "react";

type Tone = "paper" | "board";

type Props = {
    children: ReactNode;
    accent?: boolean;
    /** Left accent border in this colour (a CSS value, e.g. a token); implies `accent`. */
    accentColor?: string;
    float?: boolean;
    tone?: Tone;
    className?: string;
    style?: CSSProperties;
};

export default function ChronicleCard({
    children,
    accent,
    accentColor,
    float,
    tone = "paper",
    className,
    style,
}: Props) {
    const isBoard = tone === "board";
    const combined: CSSProperties = {
        backgroundColor: isBoard ? "var(--board)" : "var(--bg)",
        color: isBoard ? "#f5f3ed" : "inherit",
        border: `1px solid ${isBoard ? "var(--boardRule)" : "var(--rule)"}`,
        borderRadius: 0,
        // Token instead of a fixed value: cards get tighter on phones.
        padding: "var(--card-pad, 24px)",
        display: "block",
        ...(accent || accentColor
            ? {
                  borderLeft: `3px solid ${
                      accentColor ?? (isBoard ? "var(--ledHot)" : "var(--info)")
                  }`,
              }
            : {}),
        ...(float ? { boxShadow: "var(--shadow-float)" } : {}),
        ...style,
    };

    return (
        <div className={className} style={combined}>
            {children}
        </div>
    );
}
