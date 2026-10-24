/** Archive date as "23.10.2026", or null for a missing/invalid value. */
export function formatArchivedAt(value: string | null | undefined): string | null {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString("de-DE");
}
