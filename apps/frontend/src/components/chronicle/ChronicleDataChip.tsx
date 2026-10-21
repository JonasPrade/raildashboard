import type { ReactNode, CSSProperties } from "react";

type Status = "default" | "go" | "signal" | "info";

type Props = {
    children: ReactNode;
    status?: Status;
    className?: string;
    style?: CSSProperties;
};

const dotColor: Record<Status, string> = {
    default: "var(--accent-primary)",
    go: "var(--idt-success)",
    signal: "var(--idt-danger)",
    info: "var(--idt-info)",
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
                background: "var(--surface-alt)",
                color: "var(--text-body)",
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
