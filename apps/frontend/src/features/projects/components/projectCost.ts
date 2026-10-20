import type { FinveWithBudgets } from "../../../shared/api/queries";

/**
 * Funds committed by the federal budget, in Mio. €: per (non-collective)
 * FinVe the current cost of its newest budget line, else its original cost.
 * Collective FinVes (Sammel-FinVe) carry no per-project amount.
 */
export function committedFinveMio(finves: FinveWithBudgets[]): { total: number; count: number } | null {
    let total = 0;
    let count = 0;
    for (const f of finves) {
        if (f.is_sammel_finve) continue;
        const last = [...f.budgets].sort((a, b) => a.budget_year - b.budget_year).at(-1);
        const tEuro = last?.cost_estimate_actual ?? f.cost_estimate_original ?? null;
        if (tEuro == null) continue;
        total += tEuro / 1000;
        count += 1;
    }
    return count > 0 ? { total, count } : null;
}
