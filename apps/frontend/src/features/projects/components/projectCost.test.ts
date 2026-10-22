import { describe, expect, it } from "vitest";

import type { FinveWithBudgets, GvfgProjectEntry } from "../../../shared/api/queries";
import { committedFinveMio, gvfgAidMio } from "./projectCost";

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

function gvfg(key: string, year: number, projectIds: number[], aid: string | null, cost: string | null): GvfgProjectEntry {
    return {
        key,
        program: { year_from: year },
        projects: projectIds.map((id) => ({ id, name: `P${id}` })),
        amounts: [{ category: "SUM", aid_total: aid, cost_total: cost, periods: {} }],
    } as unknown as GvfgProjectEntry;
}

describe("gvfgAidMio", () => {
    it("sums the newest edition per key of the project's own entries", () => {
        const result = gvfgAidMio(
            [
                gvfg("K1", 2024, [7], "10", "20"),
                gvfg("K1", 2025, [7], "12.5", "25"),
                gvfg("K2", 2025, [7], "3", null),
                gvfg("K3", 2025, [8], "100", "200"),
            ],
            7,
        );
        expect(result).toEqual({ aid: 15.5, cost: 25, count: 2, fromSubprojects: false });
    });

    it("falls back to sub-project entries without own ones", () => {
        expect(gvfgAidMio([gvfg("K3", 2025, [8], "4", "8")], 7)).toEqual({
            aid: 4,
            cost: 8,
            count: 1,
            fromSubprojects: true,
        });
    });

    it("is null without any aid", () => {
        expect(gvfgAidMio([gvfg("K1", 2025, [7], null, "5")], 7)).toBeNull();
        expect(gvfgAidMio([], 7)).toBeNull();
    });
});
