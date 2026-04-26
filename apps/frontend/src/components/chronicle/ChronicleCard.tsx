import type { ReactNode, CSSProperties } from "react";

type Tone = "paper" | "board";

type Props = {
    children: ReactNode;
    accent?: boolean;
    float?: boolean;
    tone?: Tone;
    className?: string;
    style?: CSSProperties;
};

export default function ChronicleCard({
    children,
    accent,
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
        padding: "24px",
        display: "block",
        ...(accent
            ? { borderLeft: `3px solid ${isBoard ? "var(--ledHot)" : "var(--info)"}` }
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
