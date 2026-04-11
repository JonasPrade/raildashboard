import type { ReactNode } from "react";

type HeadingLevel = "h1" | "h2" | "h3";

type Props = {
    as?: HeadingLevel;
    children: ReactNode;
    className?: string;
    style?: React.CSSProperties;
};

const sizeMap: Record<HeadingLevel, string> = {
    h1: "var(--font-size-display)",
    h2: "var(--font-size-headline)",
    h3: "var(--font-size-headline)",
};

export default function ChronicleHeadline({ as: Tag = "h1", children, className, style }: Props) {
    return (
        <Tag
            className={className}
            style={{
                fontFamily: "var(--font-serif)",
                fontSize: sizeMap[Tag],
                letterSpacing: "var(--letter-spacing-tight)",
                color: "var(--c-primary)",
                fontWeight: Tag === "h1" ? 700 : 600,
                margin: 0,
                ...style,
            }}
        >
            {children}
        </Tag>
    );
}
