import type { ReactNode } from "react";

type HeadingLevel = "h1" | "h2" | "h3" | "h4";

type Props = {
    as?: HeadingLevel;
    children: ReactNode;
    className?: string;
    style?: React.CSSProperties;
};

const sizeMap: Record<HeadingLevel, { fontSize: string; lineHeight: string; letterSpacing: string }> = {
    h1: { fontSize: "40px", lineHeight: "1", letterSpacing: "-0.02em" },
    h2: { fontSize: "26px", lineHeight: "1.05", letterSpacing: "-0.015em" },
    h3: { fontSize: "20px", lineHeight: "1.1", letterSpacing: "-0.005em" },
    h4: { fontSize: "16px", lineHeight: "1.15", letterSpacing: "-0.005em" },
};

export default function ChronicleHeadline({ as: Tag = "h1", children, className, style }: Props) {
    return (
        <Tag
            className={className}
            style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                textTransform: "uppercase",
                color: "var(--ink)",
                margin: 0,
                ...sizeMap[Tag],
                ...style,
            }}
        >
            {children}
        </Tag>
    );
}
