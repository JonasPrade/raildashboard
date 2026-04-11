import type { ReactNode, CSSProperties, MouseEventHandler } from "react";

type Variant = "primary" | "ghost";

type Props = {
    children: ReactNode;
    variant?: Variant;
    onClick?: MouseEventHandler<HTMLButtonElement>;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
    className?: string;
    style?: CSSProperties;
};

const primaryStyle: CSSProperties = {
    background: "linear-gradient(135deg, #041920 0%, #1a2e35 100%)",
    color: "var(--c-on-primary)",
    border: "none",
};

const ghostStyle: CSSProperties = {
    background: "",
    color: "var(--c-secondary)",
    border: "1px solid var(--c-outline-ghost)",
};

export default function ChronicleButton({
    children,
    variant = "primary",
    onClick,
    disabled,
    type = "button",
    className,
    style,
}: Props) {
    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={className}
            style={{
                ...(variant === "primary" ? primaryStyle : ghostStyle),
                borderRadius: "var(--radius-sharp)",
                fontFamily: "var(--font-sans)",
                fontSize: "0.875rem",
                fontWeight: 500,
                padding: "8px 16px",
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.5 : 1,
                letterSpacing: "0.01em",
                ...style,
            }}
        >
            {children}
        </button>
    );
}
