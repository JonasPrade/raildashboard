import type { CSSProperties, ReactNode } from "react";

type StatProps = {
    /** The figure; pass a number already formatted for German locale. */
    value: ReactNode;
    /** Unit set smaller after the figure, e.g. "Mrd €". */
    unit?: ReactNode;
    title?: ReactNode;
    /** Upper-case label below the title (source, period). */
    label?: ReactNode;
    /** "lg" = 56px band figure, default 36px (docs/DESIGN.md rule 6). */
    size?: "md" | "lg";
    /** Emphasis colour of the figure, a token such as "var(--accent-primary)". */
    color?: string;
};

/** Kennzahl after the DS Stat (docs/features/feature-idt-design.md → Stufe 4). */
export function Stat({ value, unit, title, label, size = "md", color }: StatProps) {
    return (
        <div className="idt-stat">
            <div className={size === "lg" ? "idt-stat__num idt-stat__num--lg" : "idt-stat__num"} style={color ? { color } : undefined}>
                {value}
                {unit != null && <small>{unit}</small>}
            </div>
            {title != null && <div className="idt-stat__title">{title}</div>}
            {label != null && <div className="idt-stat__label">{label}</div>}
        </div>
    );
}

/** Kennzahlenband: Stat cells in a 2px frame with 2px dividers. */
export function StatBand({ children, columns }: { children: ReactNode; columns?: 2 | 3 | 4 }) {
    return (
        <div className="idt-statband" style={{ "--statband-cols": columns ?? 4 } as CSSProperties}>
            {children}
        </div>
    );
}
