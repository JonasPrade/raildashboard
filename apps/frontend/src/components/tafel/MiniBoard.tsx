import type { CSSProperties, ReactNode } from "react";

export type MiniBoardState = "go" | "delay" | "wait" | "info";

export type MiniBoardRow = {
    /** Left column — typically year, time, or short tag */
    time: ReactNode;
    /** Main label — display font, uppercase */
    title: ReactNode;
    /** Optional centre marker — gleis/track number, badge */
    track?: ReactNode;
    /** Right column status text */
    status?: ReactNode;
    state?: MiniBoardState;
    /** Optional click handler for navigation */
    onClick?: () => void;
};

type Props = {
    rows: MiniBoardRow[];
    title?: ReactNode;
    subtitle?: ReactNode;
    state?: MiniBoardState;
    /** Light variant uses --bg2 surface; dark uses --board (true Tafel). Default: dark. */
    tone?: "dark" | "light";
    emptyMessage?: ReactNode;
    style?: CSSProperties;
};

const dotColor: Record<MiniBoardState, string> = {
    go:    "var(--go)",
    delay: "var(--signal)",
    wait:  "var(--led)",
    info:  "var(--info)",
};

function Dot({ state = "wait" }: { state?: MiniBoardState }) {
    return (
        <span
            aria-hidden
            style={{
                display: "inline-block",
                width: 8,
                height: 8,
                background: dotColor[state],
                borderRadius: "50%",
                flex: "0 0 auto",
            }}
        />
    );
}

export default function MiniBoard({
    rows,
    title,
    subtitle,
    state = "wait",
    tone = "dark",
    emptyMessage = "▸ Keine Einträge",
    style,
}: Props) {
    const dark = tone === "dark";
    return (
        <div
            style={{
                background: dark ? "var(--board)" : "var(--bg2)",
                color: dark ? "#f5f3ed" : "var(--ink)",
                padding: "18px 20px",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                border: `1px solid ${dark ? "var(--boardRule)" : "var(--rule)"}`,
                ...style,
            }}
        >
            {(title || subtitle) && (
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: 12,
                        fontSize: 9.5,
                        letterSpacing: "0.16em",
                        textTransform: "uppercase",
                        color: dark ? "#a8adb5" : "var(--ink3)",
                        paddingBottom: 10,
                        borderBottom: `1px solid ${dark ? "var(--boardRule)" : "var(--rule)"}`,
                        marginBottom: 10,
                        fontWeight: 700,
                    }}
                >
                    {title && (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                            <Dot state={state} />
                            <b style={{ color: dark ? "var(--ledHot)" : "var(--info)" }}>{title}</b>
                        </span>
                    )}
                    {subtitle && <span>{subtitle}</span>}
                </div>
            )}

            {rows.length === 0 ? (
                <div
                    style={{
                        padding: "16px 0",
                        color: dark ? "#7a8390" : "var(--ink3)",
                        fontWeight: 700,
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                    }}
                >
                    {emptyMessage}
                </div>
            ) : (
                rows.map((r, i) => (
                    <div
                        key={i}
                        onClick={r.onClick}
                        style={{
                            display: "grid",
                            gridTemplateColumns: "60px 1fr 32px 110px",
                            gap: 12,
                            alignItems: "center",
                            padding: "10px 0",
                            borderBottom:
                                i === rows.length - 1
                                    ? "none"
                                    : `1px dashed ${dark ? "var(--boardRule)" : "var(--rule)"}`,
                            cursor: r.onClick ? "pointer" : "default",
                        }}
                    >
                        <span
                            style={{
                                color: dark ? "var(--ledHot)" : "var(--info)",
                                fontWeight: 700,
                                letterSpacing: "0.04em",
                            }}
                        >
                            {r.time}
                        </span>
                        <span
                            style={{
                                color: dark ? "#f5f3ed" : "var(--ink)",
                                fontFamily: "var(--font-display)",
                                fontWeight: 700,
                                textTransform: "uppercase",
                                fontSize: 13.5,
                                letterSpacing: "-0.005em",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                            }}
                        >
                            {r.title}
                        </span>
                        <span
                            style={{
                                color: dark ? "var(--ledHot)" : "var(--led)",
                                textAlign: "right",
                                fontWeight: 700,
                            }}
                        >
                            {r.track ?? ""}
                        </span>
                        <span
                            style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 7,
                                fontSize: 10.5,
                                letterSpacing: "0.1em",
                                textTransform: "uppercase",
                                color: dark ? "#b5bac2" : "var(--ink2)",
                                fontWeight: 700,
                                justifyContent: "flex-end",
                            }}
                        >
                            {r.status && <Dot state={r.state ?? "wait"} />}
                            {r.status}
                        </span>
                    </div>
                ))
            )}
        </div>
    );
}
