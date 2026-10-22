import { describe, expect, it } from "vitest";

import type { FinveWithBudgets } from "../../../shared/api/queries";
import { committedFinveMio } from "./projectCost";

function finve(overrides: Partial<FinveWithBudgets>): FinveWithBudgets {
    return { id: 1, is_sammel_finve: false, budgets: [], ...overrides } as FinveWithBudgets;
}

describe("committedFinveMio", () => {
    it("sums the newest current cost per FinVe in Mio. € and skips collective FinVes", () => {
        const result = committedFinveMio([
            finve({
                id: 1,
                cost_estimate_original: 1000,
                budgets: [
                    { budget_year: 2025, cost_estimate_actual: 120_000, titel_entries: [] },
                    { budget_year: 2024, cost_estimate_actual: 100_000, titel_entries: [] },
                ] as FinveWithBudgets["budgets"],
            }),
            finve({ id: 2, cost_estimate_original: 30_500, from_subprojects: true }),
            finve({ id: 3, is_sammel_finve: true, cost_estimate_original: 999_999 }),
        ]);
        expect(result).toEqual({ total: 150.5, count: 2, fromSubprojects: 1 });
    });

    it("is null without any amount", () => {
        expect(committedFinveMio([finve({ id: 1 })])).toBeNull();
    });
});
