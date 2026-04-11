import type { ReactNode, CSSProperties } from "react";

type Props = {
    children: ReactNode;
    accent?: boolean;
    float?: boolean;
    className?: string;
    style?: CSSProperties;
};

const baseStyle: CSSProperties = {
    backgroundColor: "var(--c-surface-lowest)",
    borderRadius: "var(--radius-sharp)",
    padding: "24px",
    color: "inherit",
    display: "block",
};

export default function ChronicleCard({ children, accent, float, className, style }: Props) {
    const combined: CSSProperties = {
        ...baseStyle,
        ...(accent ? { borderLeft: "var(--border-accent)" } : {}),
        ...(float ? { boxShadow: "var(--shadow-float)" } : {}),
        ...style,
    };

    return (
        <div className={className} style={combined}>
            {children}
        </div>
    );
}
