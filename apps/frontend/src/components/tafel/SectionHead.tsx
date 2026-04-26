import type { CSSProperties, ReactNode } from "react";
import { FlapNumber } from "./FlapDigit";

type Props = {
    /** Two-digit section index — rendered as Split-Flap (e.g. 1 → "01") */
    n: number | string;
    /** Mono uppercase eyebrow above the headline */
    eyebrow?: ReactNode;
    /** Display headline */
    children: ReactNode;
    /** Optional right-aligned description block */
    description?: ReactNode;
    style?: CSSProperties;
};

export default function SectionHead({ n, eyebrow, children, description, style }: Props) {
    return (
        <div
            style={{
                display: "grid",
                gridTemplateColumns: description ? "auto 1fr auto" : "auto 1fr",
                alignItems: "end",
                gap: 24,
                marginBottom: 24,
                paddingBottom: 14,
                borderBottom: "1px solid var(--rule)",
                ...style,
            }}
        >
            <FlapNumber n={n} digits={2} width={56} height={60} fontSize={40} />
            <div>
                {eyebrow && (
                    <div
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: 10.5,
                            letterSpacing: "0.18em",
                            textTransform: "uppercase",
                            color: "var(--ink3)",
                            marginBottom: 6,
                            fontWeight: 700,
                        }}
                    >
                        {eyebrow}
                    </div>
                )}
                <h2
                    style={{
                        fontFamily: "var(--font-display)",
                        fontSize: 26,
                        fontWeight: 700,
                        margin: 0,
                        textTransform: "uppercase",
                        letterSpacing: "-0.015em",
                        lineHeight: 0.95,
                        color: "var(--ink)",
                    }}
                >
                    {children}
                </h2>
            </div>
            {description && (
                <div
                    style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: 12.5,
                        color: "var(--ink2)",
                        maxWidth: 320,
                        lineHeight: 1.55,
                        justifySelf: "end",
                    }}
                >
                    {description}
                </div>
            )}
        </div>
    );
}
