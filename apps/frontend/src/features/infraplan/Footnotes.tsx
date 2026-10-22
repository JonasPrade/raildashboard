import { Tooltip } from "@mantine/core";

/** Footnote markers as superscript numbers; the text shows on hover, focus or tap. */
export default function Footnotes({ footnotes }: { footnotes: Record<string, string> | null | undefined }) {
    const entries = Object.entries(footnotes ?? {});
    if (entries.length === 0) return null;
    return (
        <>
            {entries.map(([nr, text]) => (
                <Tooltip key={nr} label={text} multiline w={300} withArrow events={{ hover: true, focus: true, touch: true }}>
                    <sup tabIndex={0} style={{ cursor: "help", color: "var(--text-link)", marginLeft: 2 }}>
                        {nr}
                    </sup>
                </Tooltip>
            ))}
        </>
    );
}
