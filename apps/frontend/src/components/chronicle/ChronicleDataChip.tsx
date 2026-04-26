import type { ReactNode, CSSProperties } from "react";

type Status = "default" | "go" | "signal" | "info";

type Props = {
    children: ReactNode;
    status?: Status;
    className?: string;
    style?: CSSProperties;
};

const dotColor: Record<Status, string> = {
    default: "var(--led)",
    go: "var(--go)",
    signal: "var(--signal)",
    info: "var(--info)",
};

export default function ChronicleDataChip({ children, status = "default", className, style }: Props) {
    return (
        <span
            className={className}
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "7px",
                padding: "3px 8px",
                background: "var(--bg2)",
                color: "var(--ink2)",
                fontFamily: "var(--font-mono)",
                fontSize: "11.5px",
                fontWeight: 600,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                borderRadius: 0,
                lineHeight: 1.5,
                ...style,
            }}
        >
            <span
                aria-hidden
                style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    background: dotColor[status],
                    borderRadius: "50%",
                    flex: "0 0 auto",
                }}
            />
            {children}
        </span>
    );
}
