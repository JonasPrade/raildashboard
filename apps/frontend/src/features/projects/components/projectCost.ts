import type { FinveWithBudgets, GvfgProjectEntry } from "../../../shared/api/queries";
import { num, sumLine } from "../../gvfg/gvfgFormat";

/**
 * Funds committed by the federal budget, in Mio. €: per (non-collective)
 * FinVe the current cost of its newest budget line, else its original cost.
 * Collective FinVes (Sammel-FinVe) carry no per-project amount.
 * ``fromSubprojects`` counts those linked only to a sub-project.
 */
export function committedFinveMio(
    finves: FinveWithBudgets[],
): { total: number; count: number; fromSubprojects: number } | null {
    let total = 0;
    let count = 0;
    let fromSubprojects = 0;
    for (const f of finves) {
        if (f.is_sammel_finve) continue;
        const last = [...f.budgets].sort((a, b) => a.budget_year - b.budget_year).at(-1);
        const tEuro = last?.cost_estimate_actual ?? f.cost_estimate_original ?? null;
        if (tEuro == null) continue;
        total += tEuro / 1000;
        count += 1;
        if (f.from_subprojects) fromSubprojects += 1;
    }
    return count > 0 ? { total, count, fromSubprojects } : null;
}

/**
 * Federal aid from the GVFG-Bundesprogramm, in Mio. €: the ∑ line of the
 * newest edition per key (each key once). The project's own entries count;
 * only without any, those of its sub-projects (``fromSubprojects``) — a
 * parent's own entry and its children's may overlap, so they are never added.
 */
export function gvfgAidMio(
    entries: GvfgProjectEntry[],
    projectId: number,
): { aid: number; cost: number | null; count: number; fromSubprojects: boolean } | null {
    const own = entries.filter((e) => e.projects.some((p) => p.id === projectId));
    const fromSubprojects = own.length === 0;
    const newest = new Map<string, GvfgProjectEntry>();
    for (const e of fromSubprojects ? entries : own) {
        const seen = newest.get(e.key);
        if (!seen || e.program.year_from > seen.program.year_from) newest.set(e.key, e);
    }
    let aid = 0;
    let cost = 0;
    let hasCost = false;
    let count = 0;
    for (const e of newest.values()) {
        const line = sumLine(e);
        const a = num(line?.aid_total);
        if (a === null) continue;
        aid += a;
        count += 1;
        const c = num(line?.cost_total);
        if (c !== null) {
            cost += c;
            hasCost = true;
        }
    }
    return count > 0 ? { aid, cost: hasCost ? cost : null, count, fromSubprojects } : null;
}
