// Shared German-locale formatting helpers (issue #74).
// All date helpers render in the Berlin timezone so server timestamps are
// shown consistently regardless of the viewer's local timezone.

const BERLIN_TZ = "Europe/Berlin";

/** "1.234 T€" — dash for null/0 (matches the FinVe tables' semantics). */
export function formatTEuro(val: number | null | undefined): string {
    if (val === null || val === undefined || val === 0) return "–";
    return val.toLocaleString("de-DE") + " T€";
}

/** "1.234 T€" — dash only for null/undefined; 0 renders as "0 T€" (charts, import review). */
export function formatTEuroWithZero(val: number | null | undefined): string {
    if (val === null || val === undefined) return "–";
    return val.toLocaleString("de-DE") + " T€";
}

/** Plain German-locale number — dash for null/undefined. */
export function formatNumberDe(val: number | null | undefined): string {
    if (val === null || val === undefined) return "–";
    return val.toLocaleString("de-DE");
}

/** Chart-safe number: null → 0. */
export function chartNum(val: number | null | undefined): number {
    return val ?? 0;
}

/** Timestamp incl. time, Berlin timezone: "7.7.2026, 14:03:12" style. */
export function formatDateTime(value: string | Date): string {
    return new Date(value).toLocaleString("de-DE", { timeZone: BERLIN_TZ });
}

/** Date + time without seconds, padded numeric: "07.07.2026, 14:03". */
export function formatDateTimeShort(value: string | Date): string {
    return new Date(value).toLocaleString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: BERLIN_TZ,
    });
}

/** Date only, medium style, Berlin timezone: "7. Juli 2026" style. */
export function formatDate(value: string | Date): string {
    return new Date(value).toLocaleDateString("de-DE", { dateStyle: "medium", timeZone: BERLIN_TZ });
}

/** Date only, padded numeric: "07.07.2026". */
export function formatDateShort(value: string | Date): string {
    return new Date(value).toLocaleDateString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        timeZone: BERLIN_TZ,
    });
}

/** Date only, unpadded numeric, Berlin timezone: "7.7.2026". */
export function formatDateNumeric(value: string | Date): string {
    return new Date(value).toLocaleDateString("de-DE", { timeZone: BERLIN_TZ });
}
