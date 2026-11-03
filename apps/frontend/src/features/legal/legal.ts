/** Admin page with the four legal-page fields (LegalSettingsPage). */
export const LEGAL_SETTINGS_PATH = "/admin/rechtliches";

type LegalFields = {
    impressum_url?: string | null;
    impressum_markdown?: string | null;
    datenschutz_url?: string | null;
    datenschutz_markdown?: string | null;
};

function pageState(url?: string | null, markdown?: string | null): string {
    if (url?.trim()) return "Weiterleitung";
    if (markdown?.trim()) return "eigene Seite";
    return "leer";
}

/** One-line state of both pages, shown on the admin tile. */
export function legalStatusLabel(settings: LegalFields): string {
    return (
        `Impressum: ${pageState(settings.impressum_url, settings.impressum_markdown)} · ` +
        `Datenschutz: ${pageState(settings.datenschutz_url, settings.datenschutz_markdown)}`
    );
}
