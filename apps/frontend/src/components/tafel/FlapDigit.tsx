import type { CSSProperties, ReactNode } from "react";

type Variant = "default" | "section" | "tafel";

type Props = {
    children: ReactNode;
    width?: number;
    height?: number;
    fontSize?: number;
    variant?: Variant;
    style?: CSSProperties;
};

const variantBg: Record<Variant, { bg: string; color: string; border: string; seam: string }> = {
    default: { bg: "var(--bg2)", color: "var(--ink)", border: "var(--ruleHot)", seam: "var(--rule)" },
    section: { bg: "var(--bg2)", color: "var(--ink)", border: "var(--ruleHot)", seam: "var(--rule)" },
    tafel:   { bg: "var(--board2)", color: "var(--ledHot)", border: "var(--boardRule)", seam: "rgba(0,0,0,0.6)" },
};

export default function FlapDigit({
    children,
    width = 38,
    height = 48,
    fontSize = 30,
    variant = "default",
    style,
}: Props) {
    const v = variantBg[variant];
    return (
        <span
            style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width,
                height,
                background: v.bg,
                color: v.color,
                border: `1px solid ${v.border}`,
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize,
                lineHeight: 1,
                letterSpacing: "-0.03em",
                position: "relative",
                flex: "0 0 auto",
                ...style,
            }}
        >
            {children}
            <span
                aria-hidden
                style={{
                    content: "''",
                    position: "absolute",
                    left: 0,
                    right: 0,
                    top: "50%",
                    height: 1,
                    background: v.seam,
                    pointerEvents: "none",
                }}
            />
        </span>
    );
}

type FlapNumberProps = {
    n: number | string;
    digits?: number;
    width?: number;
    height?: number;
    fontSize?: number;
    variant?: Variant;
    gap?: number;
    style?: CSSProperties;
};

export function FlapNumber({
    n,
    digits,
    width,
    height,
    fontSize,
    variant,
    gap = 4,
    style,
}: FlapNumberProps) {
    const raw = String(n);
    const padded = digits ? raw.padStart(digits, "0") : raw;
    return (
        <span style={{ display: "inline-flex", gap, ...style }}>
            {[...padded].map((c, i) => (
                <FlapDigit key={`${i}-${c}`} width={width} height={height} fontSize={fontSize} variant={variant}>
                    {c}
                </FlapDigit>
            ))}
        </span>
    );
}

type FlapTextProps = {
    text: string;
    width?: number;
    height?: number;
    fontSize?: number;
    variant?: Variant;
    gap?: number;
    style?: CSSProperties;
};

export function FlapText({ text, width, height, fontSize, variant, gap = 4, style }: FlapTextProps) {
    return (
        <span style={{ display: "inline-flex", gap, ...style }}>
            {[...text.toUpperCase()].map((c, i) => (
                <FlapDigit key={`${i}-${c}`} width={width} height={height} fontSize={fontSize} variant={variant}>
                    {c === " " ? " " : c}
                </FlapDigit>
            ))}
        </span>
    );
}
