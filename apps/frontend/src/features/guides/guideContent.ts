/**
 * Shared types for the data-driven guide pages ("Anleitungen").
 *
 * Guide content is authored as markdown strings (versioned defaults in code);
 * users with the "guides.edit" permission can override single section bodies
 * in-app (stored server-side, see useGuideOverrides). Section keys are the
 * stable identifiers those overrides are keyed by — never rename them once a
 * guide has shipped, or existing overrides silently detach.
 *
 * Supported markdown (rendered by GuideMarkdown):
 * - paragraphs, **bold**, *italic*, ordered/unordered lists
 * - [Link](/interner/pfad) → router link, external URLs open in a new tab
 * - `Chip` → ChronicleDataChip
 * - Alert blocks:  > [!yellow] Titel   (colors: blue, yellow, green, red)
 *                  > Fließtext der Box …
 */

export type GuideSection = {
    /** Stable override key (per guide). */
    key: string;
    title: string;
    /** Default markdown body; replaced by a server-side override when present. */
    body: string;
    /** Optional key into GUIDE_EXAMPLES, rendered below the body (not editable). */
    exampleKey?: string;
};

export type GuideDef = {
    /** Stable slug, also used in the override API (e.g. "fulda"). */
    slug: string;
    title: string;
    /** Chip next to the headline (e.g. "Schritt für Schritt"). */
    chip: string;
    /** Dimmed intro paragraph (markdown, editable, key "intro"). */
    intro: string;
    /** Markdown list inside the green "Voraussetzungen" alert (editable, key "voraussetzungen"). */
    prerequisites?: string;
    steps: GuideSection[];
    /** Optional contained accordion with special cases / troubleshooting. */
    troubleshooting?: GuideSection[];
};
