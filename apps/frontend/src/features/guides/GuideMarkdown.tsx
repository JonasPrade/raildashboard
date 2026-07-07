import type { ReactNode } from "react";
import { Alert, Anchor, Box, List, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChronicleDataChip } from "../../components/chronicle";

/**
 * Renders guide markdown in the guide look: paragraphs as small Text, inline
 * code as ChronicleDataChip, internal links as router links, and "> [!color]"
 * blockquote blocks as Mantine Alerts (see guideContent.ts for the syntax).
 */

type Segment =
    | { type: "md"; text: string }
    | { type: "alert"; color: string; title: string | null; text: string };

const ALERT_COLORS = new Set(["blue", "yellow", "green", "red"]);
const ALERT_MARKER = /^\[!(\w+)\]\s*(.*)$/;

/** Split markdown into plain segments and blockquote-alert segments. */
function splitSegments(markdown: string): Segment[] {
    const segments: Segment[] = [];
    let plain: string[] = [];
    let quote: string[] | null = null;

    const flushPlain = () => {
        const text = plain.join("\n").trim();
        if (text) segments.push({ type: "md", text });
        plain = [];
    };
    const flushQuote = () => {
        if (quote === null) return;
        let color = "blue";
        let title: string | null = null;
        let body = quote;
        const marker = quote[0]?.match(ALERT_MARKER);
        if (marker) {
            if (ALERT_COLORS.has(marker[1].toLowerCase())) color = marker[1].toLowerCase();
            title = marker[2].trim() || null;
            body = quote.slice(1);
        }
        segments.push({ type: "alert", color, title, text: body.join("\n").trim() });
        quote = null;
    };

    for (const line of markdown.split("\n")) {
        if (/^\s*>/.test(line)) {
            if (quote === null) {
                flushPlain();
                quote = [];
            }
            quote.push(line.replace(/^\s*>\s?/, ""));
        } else {
            flushQuote();
            plain.push(line);
        }
    }
    flushQuote();
    flushPlain();
    return segments;
}

function MarkdownBlock({ text, dimmed }: { text: string; dimmed?: boolean }) {
    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
                p: ({ children }) => (
                    <Text size="sm" c={dimmed ? "dimmed" : undefined} mb={6}>
                        {children}
                    </Text>
                ),
                ul: ({ children }) => (
                    <List size="sm" spacing={4} mb={6}>
                        {children}
                    </List>
                ),
                ol: ({ children }) => (
                    <List size="sm" spacing={4} mb={6} type="ordered">
                        {children}
                    </List>
                ),
                li: ({ children }) => <List.Item>{children}</List.Item>,
                a: ({ href, children }) => {
                    const target = href ?? "#";
                    if (target.startsWith("/")) {
                        return (
                            <Anchor component={Link} to={target} size="sm">
                                {children}
                            </Anchor>
                        );
                    }
                    return (
                        <Anchor href={target} target="_blank" rel="noreferrer" size="sm">
                            {children}
                        </Anchor>
                    );
                },
                code: ({ children }) => {
                    const raw = String(children);
                    if (raw.includes("\n")) {
                        return (
                            <Box
                                component="pre"
                                p="xs"
                                my={6}
                                style={{
                                    fontFamily: "var(--mantine-font-family-monospace)",
                                    fontSize: 12,
                                    background: "var(--mantine-color-gray-0)",
                                    borderRadius: 4,
                                    overflowX: "auto",
                                }}
                            >
                                {raw}
                            </Box>
                        );
                    }
                    return <ChronicleDataChip>{raw}</ChronicleDataChip>;
                },
                pre: ({ children }) => <>{children}</>,
            }}
        >
            {text}
        </ReactMarkdown>
    );
}

export default function GuideMarkdown({
    text,
    dimmed,
}: {
    text: string;
    dimmed?: boolean;
}): ReactNode {
    const segments = splitSegments(text);
    return (
        <>
            {segments.map((seg, i) =>
                seg.type === "md" ? (
                    <MarkdownBlock key={i} text={seg.text} dimmed={dimmed} />
                ) : (
                    <Alert
                        key={i}
                        color={seg.color}
                        variant="light"
                        title={seg.title ?? undefined}
                        my={6}
                    >
                        <MarkdownBlock text={seg.text} />
                    </Alert>
                ),
            )}
        </>
    );
}
