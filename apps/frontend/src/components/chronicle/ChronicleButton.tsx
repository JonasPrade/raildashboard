import { useState } from "react";
import type { ReactNode, CSSProperties, MouseEventHandler } from "react";

type Variant = "solid" | "primary" | "outline" | "ghost";
type Size = "md" | "sm";

type Props = {
    children: ReactNode;
    variant?: Variant;
    size?: Size;
    onClick?: MouseEventHandler<HTMLButtonElement>;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
    className?: string;
    style?: CSSProperties;
};

type StateStyle = {
    bg: string;
    color: string;
    border: string;
    hoverBg: string;
    hoverColor: string;
    hoverBorder: string;
};

const variantMap: Record<Variant, StateStyle> = {
    solid: {
        bg: "var(--ink)",
        color: "#fff",
        border: "var(--ink)",
        hoverBg: "var(--led)",
        hoverColor: "var(--ink)",
        hoverBorder: "var(--led)",
    },
    primary: {
        bg: "var(--info)",
        color: "#fff",
        border: "var(--info)",
        hoverBg: "var(--ink)",
        hoverColor: "var(--led)",
        hoverBorder: "var(--ink)",
    },
    outline: {
        bg: "var(--bg)",
        color: "var(--info)",
        border: "var(--info)",
        hoverBg: "var(--info)",
        hoverColor: "#fff",
        hoverBorder: "var(--info)",
    },
    ghost: {
        bg: "transparent",
        color: "var(--ink)",
        border: "transparent",
        hoverBg: "var(--ink)",
        hoverColor: "var(--led)",
        hoverBorder: "var(--ink)",
    },
};

const sizeMap: Record<Size, { padding: string; fontSize: string; tracking: string }> = {
    md: { padding: "14px 20px", fontSize: "12.5px", tracking: "0.08em" },
    sm: { padding: "10px 14px", fontSize: "11px", tracking: "0.06em" },
};

export default function ChronicleButton({
    children,
    variant = "primary",
    size = "md",
    onClick,
    disabled,
    type = "button",
    className,
    style,
}: Props) {
    const [hover, setHover] = useState(false);
    const v = variantMap[variant];
    const s = sizeMap[size];
    const active = hover && !disabled;

    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            className={className}
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                fontFamily: "var(--font-mono)",
                fontWeight: 700,
                textTransform: "uppercase",
                fontSize: s.fontSize,
                letterSpacing: s.tracking,
                padding: s.padding,
                borderRadius: 0,
                background: active ? v.hoverBg : v.bg,
                color: active ? v.hoverColor : v.color,
                border: `1px solid ${active ? v.hoverBorder : v.border}`,
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.45 : 1,
                transition: "all 0.12s",
                ...style,
            }}
        >
            {children}
        </button>
    );
}
