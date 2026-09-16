import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { TaskProgressIndicator } from "./index";

function renderIndicator(props: Parameters<typeof TaskProgressIndicator>[0]) {
    return render(
        <MantineProvider>
            <MemoryRouter>
                <TaskProgressIndicator {...props} />
            </MemoryRouter>
        </MantineProvider>,
    );
}

describe("TaskProgressIndicator", () => {
    it("shows the stage the task reports, not a generic spinner text", () => {
        renderIndicator({
            progress: {
                step: "extract",
                step_label: "Seite 12 / 42 gelesen — 318 Tabellenzeilen",
                current_page: 12,
                total_pages: 42,
                rows_found: 318,
            },
        });

        expect(screen.getByText("Seite 12 / 42 gelesen — 318 Tabellenzeilen")).toBeInTheDocument();
    });

    it("falls back to the page counter when the task sends no label", () => {
        renderIndicator({ progress: { current_page: 3, total_pages: 9 } });

        expect(screen.getByText("Seite 3 / 9")).toBeInTheDocument();
    });

    it("names the cause and links to the system status when nothing starts", () => {
        renderIndicator({
            progress: null,
            warning: "Kein Worker online. Aufträge werden angenommen, aber niemand arbeitet sie ab.",
        });

        expect(screen.getByText(/kein worker online/i)).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /systemstatus/i })).toHaveAttribute(
            "href",
            "/admin/system",
        );
    });

    it("stays quiet while the task is simply running", () => {
        renderIndicator({ progress: { step_label: "Tabellen zuordnen…" }, warning: null });

        expect(screen.queryByText(/worker/i)).not.toBeInTheDocument();
    });
});
