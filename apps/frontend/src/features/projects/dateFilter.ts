/**
 * Pure helpers behind the date filters of the list and timeline (`/`):
 * construction start / commissioning by year range and „Termin offen“
 * (docs/features/feature-project-progress.md → „Datumsqualifikation“).
 *
 * The dates are the cached forecast dates of the list items
 * (`construction_start_*`, `commissioning_*`). A range uses
 * `inPeriod`: a year-only date matches when its year overlaps, a lower bound
 * („nach 2031“) never matches — it is no date. „Termin offen“ selects exactly
 * those projects whose Baubeginn or Inbetriebnahme is only a lower bound.
 *
 * URL: `?bau_von=2028&bau_bis=2030&ib_von=…&ib_bis=…&termin_offen=1`.
 */

import { inPeriod, isOpenDate } from "../../shared/datePrecision";

export type DateFilter = {
    bauFrom: number | null;
    bauTo: number | null;
    ibFrom: number | null;
    ibTo: number | null;
    open: boolean;
};

export const EMPTY_DATE_FILTER: DateFilter = { bauFrom: null, bauTo: null, ibFrom: null, ibTo: null, open: false };

const PARAMS = { bauFrom: "bau_von", bauTo: "bau_bis", ibFrom: "ib_von", ibTo: "ib_bis" } as const;
const OPEN_PARAM = "termin_offen";

export type DateFilterable = {
    construction_start_date?: string | null;
    construction_start_precision?: string | null;
    commissioning_date?: string | null;
    commissioning_precision?: string | null;
};

function parseYear(raw: string | null): number | null {
    if (!raw || !/^\d{4}$/.test(raw.trim())) return null;
    return Number(raw.trim());
}

/** Read the filter from the URL; malformed values are dropped. */
export function parseDateFilter(params: URLSearchParams): DateFilter {
    return {
        bauFrom: parseYear(params.get(PARAMS.bauFrom)),
        bauTo: parseYear(params.get(PARAMS.bauTo)),
        ibFrom: parseYear(params.get(PARAMS.ibFrom)),
        ibTo: parseYear(params.get(PARAMS.ibTo)),
        open: params.get(OPEN_PARAM) === "1",
    };
}

/** Write the filter into ``params`` (mutates and returns it, for setSearchParams). */
export function writeDateFilter(params: URLSearchParams, filter: DateFilter): URLSearchParams {
    for (const key of Object.keys(PARAMS) as (keyof typeof PARAMS)[]) {
        const value = filter[key];
        if (value !== null) params.set(PARAMS[key], String(value));
        else params.delete(PARAMS[key]);
    }
    if (filter.open) params.set(OPEN_PARAM, "1");
    else params.delete(OPEN_PARAM);
    return params;
}

export function isDateFilterActive(filter: DateFilter): boolean {
    return filter.open || [filter.bauFrom, filter.bauTo, filter.ibFrom, filter.ibTo].some((v) => v !== null);
}

const yearStart = (year: number | null) => (year === null ? null : `${year}-01-01`);
const yearEnd = (year: number | null) => (year === null ? null : `${year}-12-31`);

/**
 * Projects matching every active part of the filter. An inactive filter
 * returns the input unchanged (same array), so memoised consumers do not re-render.
 */
export function filterProjectsByDate<T extends DateFilterable>(projects: T[], filter: DateFilter): T[] {
    if (!isDateFilterActive(filter)) return projects;
    const bauActive = filter.bauFrom !== null || filter.bauTo !== null;
    const ibActive = filter.ibFrom !== null || filter.ibTo !== null;
    return projects.filter((p) => {
        if (
            bauActive &&
            !inPeriod(p.construction_start_date, p.construction_start_precision, yearStart(filter.bauFrom), yearEnd(filter.bauTo))
        ) {
            return false;
        }
        if (
            ibActive &&
            !inPeriod(p.commissioning_date, p.commissioning_precision, yearStart(filter.ibFrom), yearEnd(filter.ibTo))
        ) {
            return false;
        }
        if (filter.open && !isDateOpen(p)) return false;
        return true;
    });
}

/** Baubeginn or Inbetriebnahme only known as a lower bound. */
export function isDateOpen(project: DateFilterable): boolean {
    return (
        (Boolean(project.construction_start_date) && isOpenDate(project.construction_start_precision)) ||
        (Boolean(project.commissioning_date) && isOpenDate(project.commissioning_precision))
    );
}

function rangeLabel(prefix: string, from: number | null, to: number | null): string | null {
    if (from === null && to === null) return null;
    if (from !== null && to !== null) return from === to ? `${prefix} ${from}` : `${prefix} ${from}–${to}`;
    return from !== null ? `${prefix} ab ${from}` : `${prefix} bis ${to}`;
}

/** Removable filter marks: label plus the filter without that part. */
export function dateFilterMarks(filter: DateFilter): { label: string; without: DateFilter }[] {
    const marks: { label: string; without: DateFilter }[] = [];
    const bau = rangeLabel("Bau", filter.bauFrom, filter.bauTo);
    if (bau) marks.push({ label: bau, without: { ...filter, bauFrom: null, bauTo: null } });
    const ib = rangeLabel("IB", filter.ibFrom, filter.ibTo);
    if (ib) marks.push({ label: ib, without: { ...filter, ibFrom: null, ibTo: null } });
    if (filter.open) marks.push({ label: "Termin offen", without: { ...filter, open: false } });
    return marks;
}
