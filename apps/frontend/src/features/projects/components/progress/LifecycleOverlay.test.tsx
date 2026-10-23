import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import LifecycleOverlay from "./LifecycleOverlay";

const renderOverlay = (props: Parameters<typeof LifecycleOverlay>[0]) =>
    render(
        <MantineProvider>
            <MemoryRouter>
                <LifecycleOverlay {...props} />
            </MemoryRouter>
        </MantineProvider>,
    );

describe("LifecycleOverlay", () => {
    it("links a replaced project to its successor with reason and date", () => {
        renderOverlay({
            status: "ERSETZT",
            note: "Eigenständiges Vorhaben D-14",
            date: "2023-05-01",
            replacedBy: { id: 1535, name: "NBS/ABS Bielefeld – Seelze", project_number: "D-14" },
        });
        expect(screen.getByText("Projekt Ersetzt")).toBeInTheDocument();
        const link = screen.getByRole("link", { name: "NBS/ABS Bielefeld – Seelze (D-14)" });
        expect(link).toHaveAttribute("href", "/projects/1535");
        expect(screen.getByText(/seit 01\.05\.2023/)).toBeInTheDocument();
        expect(screen.getByText("Begründung: Eigenständiges Vorhaben D-14")).toBeInTheDocument();
    });

    it("shows the back-reference on an active successor", () => {
        renderOverlay({ status: "AKTIV", replaces: [{ id: 1477, name: "ABS/NBS Hannover - Bielefeld (BVWP)" }] });
        expect(screen.getByText("Nachfolgeprojekt")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "ABS/NBS Hannover - Bielefeld (BVWP)" })).toHaveAttribute(
            "href",
            "/projects/1477",
        );
    });

    it("renders nothing for an active project that replaces nothing", () => {
        renderOverlay({ status: "AKTIV" });
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
});
