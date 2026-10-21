import type { CSSProperties } from "react";

type Props = {
    size?: number;
    title?: string;
    style?: CSSProperties;
};

export default function Signet({ size = 44, title = "Schienendashboard", style }: Props) {
    const inner = Math.round(size * 0.32);
    return (
        <span
            role="img"
            aria-label={title}
            style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: size,
                height: size,
                // Brand surface: ink in both schemes.
                background: "var(--idt-ink)",
                flex: "0 0 auto",
                ...style,
            }}
        >
            <span
                aria-hidden
                style={{
                    width: inner,
                    height: inner,
                    background: "var(--accent-primary)",
                    boxShadow: `0 0 0 2px var(--idt-ink), 0 0 0 3px var(--accent-primary)`,
                }}
            />
        </span>
    );
}
