import type { ReactNode, CSSProperties } from "react";

import { DATA_CHIP_DOT_COLOR } from "../../shared/theme/semanticColors";

type Status = keyof typeof DATA_CHIP_DOT_COLOR;

type Props = {
    children: ReactNode;
    status?: Status;
    /** Dot in a data-category colour from semanticColors.ts (e.g. TRAFFIC_COLOR); overrides `status`. */
    dotColor?: string;
    className?: string;
    style?: CSSProperties;
};

export default function ChronicleDataChip({ children, status = "default", dotColor, className, style }: Props) {
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
                    background: dotColor ?? DATA_CHIP_DOT_COLOR[status],
                    borderRadius: "50%",
                    flex: "0 0 auto",
                }}
            />
            {children}
        </span>
    );
}
