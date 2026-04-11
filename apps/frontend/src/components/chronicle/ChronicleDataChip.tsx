import type { ReactNode } from "react";

type Props = {
    children: ReactNode;
    className?: string;
    style?: React.CSSProperties;
};

export default function ChronicleDataChip({ children, className, style }: Props) {
    return (
        <span
            className={className}
            style={{
                display: "inline-block",
                padding: "2px 8px",
                backgroundColor: "var(--c-tertiary-container)",
                color: "var(--c-on-surface)",
                fontFamily: "var(--font-sans)",
                fontSize: "var(--font-size-label)",
                letterSpacing: "var(--letter-spacing-data)",
                borderRadius: "var(--radius-sharp)",
                fontWeight: 500,
                lineHeight: "1.6",
                ...style,
            }}
        >
            {children}
        </span>
    );
}
