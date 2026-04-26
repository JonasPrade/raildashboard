import type { CSSProperties, ReactNode } from "react";

type Props = {
    items: ReactNode[];
    /** Auto-scroll the band horizontally. Default: false (static, like a board with current entries). */
    scrolling?: boolean;
    style?: CSSProperties;
};

export default function Ticker({ items, scrolling, style }: Props) {
    const joined = items.flatMap((it, i) => (i === 0 ? [it] : [
        <span key={`sep-${i}`} style={{ margin: "0 12px", opacity: 0.5 }}>·</span>,
        it,
    ]));

    return (
        <div
            style={{
                background: "#fcecb3",
                color: "var(--ink)",
                padding: "10px 16px",
                fontFamily: "var(--font-mono)",
                fontSize: 11.5,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                overflow: "hidden",
                whiteSpace: "nowrap",
                border: "1px solid var(--led)",
                borderLeft: "2px solid var(--led)",
                fontWeight: 700,
                ...(scrolling
                    ? {
                          // basic CSS marquee-style scroll; the wrapper hides overflow.
                          display: "block",
                      }
                    : {}),
                ...style,
            }}
        >
            <div
                style={
                    scrolling
                        ? {
                              display: "inline-block",
                              animation: "tafel-ticker 32s linear infinite",
                              willChange: "transform",
                          }
                        : undefined
                }
            >
                {joined}
            </div>
            {scrolling && (
                <style>{`@keyframes tafel-ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }`}</style>
            )}
        </div>
    );
}
