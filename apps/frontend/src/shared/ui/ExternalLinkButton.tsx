import type { ReactNode } from "react";
import { Button } from "@mantine/core";
import { ExternalLink } from "lucide-react";

/** Host of a URL without a leading "www.", or null when it does not parse. */
function linkHost(url: string): string | null {
    try {
        return new URL(url).hostname.replace(/^www\./, "") || null;
    } catch {
        return null;
    }
}

/**
 * An external link as a compact button instead of the raw URL: long URLs
 * have no break points and overflow narrow cards (360 px). The label is the
 * given text, else the host; the full URL stays in the tooltip and the
 * accessible name. Long labels are cut with an ellipsis, never overflow.
 */
export function ExternalLinkButton({ url, label }: { url: string; label?: ReactNode }) {
    const host = linkHost(url);
    const text = label ?? (host ? `Link öffnen · ${host}` : "Link öffnen");
    return (
        <Button
            component="a"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            size="xs"
            variant="light"
            leftSection={<ExternalLink size={14} aria-hidden />}
            title={url}
            maw="100%"
            style={{ alignSelf: "flex-start" }}
            styles={{
                inner: { minWidth: 0 },
                label: { minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", display: "block" },
            }}
        >
            {text}
        </Button>
    );
}
