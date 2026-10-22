// Date qualification of planning-state dates — the frontend twin of
// apps/backend/dashboard_backend/services/date_precision.py
// (docs/features/feature-project-progress.md → „Datumsqualifikation“).
// A stored date is only the sort value; it is never shown without its precision.

import type { components } from "./api/types.gen";

export type DatePrecision = components["schemas"]["ProgressObservationSchema"]["date_precision"];

export const DATE_PRECISIONS: readonly DatePrecision[] = ["EXACT", "MONTH", "YEAR", "NOT_BEFORE", "ASSUMED"];

/** Labels and help texts of the precision select (edit drawer). */
export const DATE_PRECISION_META: Record<DatePrecision, { label: string; help: string }> = {
    EXACT: { label: "Tag", help: "Konkretes Datum veröffentlicht (06.02.2026)" },
    MONTH: { label: "Monat", help: "Nur der Monat ist bekannt (02/2027)" },
    YEAR: { label: "Jahr", help: "Nur das Jahr ist bekannt (2028)" },
    NOT_BEFORE: {
        label: "Untergrenze",
        help: "Kein Termin, nur eine Untergrenze — Datum = erster möglicher Tag, z. B. 01.01.2032 für „nach 2031“",
    },
    ASSUMED: { label: "Annahme", help: "Nicht veröffentlicht, aus einer Regel abgeleitet (ca. 07/2028)" },
};

function parts(iso: string): [number, number, number] {
    const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
    return [y!, m ?? 1, d ?? 1];
}

const pad = (n: number) => String(n).padStart(2, "0");

export function asPrecision(value: string | null | undefined): DatePrecision {
    return DATE_PRECISIONS.includes(value as DatePrecision) ? (value as DatePrecision) : "EXACT";
}

/**
 * German display text of an ISO date at its precision: EXACT 06.02.2026 ·
 * MONTH 02/2027 · YEAR 2028 · NOT_BEFORE „nach 2031“ (bound on 1 Jan, else
 * „frühestens 07/2032“) · ASSUMED „ca. 07/2028 (Annahme)“.
 */
export function formatQualifiedDate(iso: string | null | undefined, precision?: string | null): string | null {
    if (!iso) return null;
    const [y, m, d] = parts(iso);
    switch (asPrecision(precision)) {
        case "MONTH":
            return `${pad(m)}/${y}`;
        case "YEAR":
            return String(y);
        case "NOT_BEFORE":
            return m === 1 && d === 1 ? `nach ${y - 1}` : `frühestens ${pad(m)}/${y}`;
        case "ASSUMED":
            return `ca. ${pad(m)}/${y} (Annahme)`;
        default:
            return `${pad(d)}.${pad(m)}.${y}`;
    }
}

/** Display text plus the optional free-text label („nach 2031 – Priorisierung 2027 offen“). */
export function qualifiedDateText(
    iso: string | null | undefined,
    precision?: string | null,
    label?: string | null,
): string | null {
    const base = formatQualifiedDate(iso, precision);
    const extra = label?.trim() || null;
    if (base && extra) return `${base} – ${extra}`;
    return base ?? extra;
}

/** Sort value of a coarse date: MONTH → 1st of the month, YEAR → 1 Jan. */
export function normalizeSortDate(iso: string, precision: string | null | undefined): string {
    const [y, m] = parts(iso);
    const p = asPrecision(precision);
    if (p === "MONTH") return `${y}-${pad(m)}-01`;
    if (p === "YEAR") return `${y}-01-01`;
    return iso.slice(0, 10);
}

/** Only a lower bound — no point in time at all. */
export const isOpenDate = (precision: string | null | undefined) => asPrecision(precision) === "NOT_BEFORE";

/** Days a qualified date may stand for as ISO [first, last], or null for a lower bound. */
export function coveredPeriod(iso: string, precision: string | null | undefined): [string, string] | null {
    const [y, m] = parts(iso);
    switch (asPrecision(precision)) {
        case "NOT_BEFORE":
            return null;
        case "YEAR":
            return [`${y}-01-01`, `${y}-12-31`];
        case "MONTH": {
            const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
            return [`${y}-${pad(m)}-01`, `${y}-${pad(m)}-${pad(last)}`];
        }
        default:
            return [iso.slice(0, 10), iso.slice(0, 10)];
    }
}

/**
 * Whether a qualified date falls into the filter period (ISO bounds, open ends
 * allowed). A lower bound („nach 2031“) never counts as a hit; a YEAR / MONTH
 * date counts when its period overlaps.
 */
export function inPeriod(
    iso: string | null | undefined,
    precision: string | null | undefined,
    start: string | null,
    end: string | null,
): boolean {
    if (!iso) return false;
    const period = coveredPeriod(iso, precision);
    if (!period) return false;
    const [first, last] = period;
    if (start && last < start) return false;
    if (end && first > end) return false;
    return true;
}

/** Forecast step text: „voraussichtlich 2028“, „Termin offen – nach 2031“, „ca. 07/2028 (Annahme)“. */
export function formatExpected(step: {
    expected_date?: string | null;
    date_precision?: string | null;
    date_label?: string | null;
}): string {
    const text = qualifiedDateText(step.expected_date, step.date_precision, step.date_label);
    if (!text) return "Termin offen";
    if (isOpenDate(step.date_precision)) return `Termin offen – ${text}`;
    if (step.date_precision === "ASSUMED") return text;
    return `voraussichtlich ${text}`;
}
