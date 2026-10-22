import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";

import ProgressConflictsAdminPage from "./ProgressConflictsAdminPage";

vi.mock("../../lib/auth", () => ({
    useAuth: () => ({ can: () => true }),
}));

vi.mock("../../shared/api/queries", () => ({
    useProgressConflicts: () => ({
        isLoading: false,
        data: [
            {
                project_id: 7,
                project_name: "ABS Beispiel",
                project_number: "2-001",
                computed_phase: "BAU",
                conflict: {
                    observation_id: 2,
                    source_type: "VIB",
                    asserted_phase: "VORPLANUNG",
                    observed_date: "2025-12-31",
                    date_precision: "EXACT",
                    date_text: "31.12.2025",
                    trust: 0.6,
                    contradicted_ids: [1],
                    contradicted_phase: "BAU",
                    applied: false,
                },
                contradicted: [
                    {
                        observation_id: 1,
                        source_type: "FINVE",
                        track: "MAIN",
                        asserted_state: "BAU",
                        observed_date: "2015-01-01",
                        date_precision: "YEAR",
                        date_text: "2015",
                        effective_confidence: 0.7,
                        was_decisive: true,
                        trust: 0.7,
                        is_lower_bound: true,
                        in_conflict: true,
                    },
                ],
            },
        ],
    }),
}));

describe("ProgressConflictsAdminPage", () => {
    it("lists a held-back conflict with its project and sources", () => {
        render(
            <MantineProvider>
                <MemoryRouter>
                    <ProgressConflictsAdminPage />
                </MemoryRouter>
            </MantineProvider>,
        );
        expect(screen.getByRole("link", { name: "ABS Beispiel" })).toHaveAttribute("href", "/projects/7");
        expect(screen.getByText("zurückgehalten")).toBeInTheDocument();
        expect(screen.getByText(/1 neuere Meldung/)).toBeInTheDocument();
        expect(screen.getByText(/FinVe · 2015 \(/)).toHaveTextContent("Untergrenze");
    });
});
