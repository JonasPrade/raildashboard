import { fireEvent, render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, expect, it, vi } from "vitest";

import MapOverlapList from "./MapOverlapList";

const projects = [
    { id: 1, name: "ABS Korridor Nord", project_number: "2-032-V01", groupColor: "#6E50FA" },
    { id: 2, name: "Elektrifizierung Mitte", project_number: null, groupColor: "#00DCFA" },
];

function renderList() {
    const onHighlight = vi.fn();
    const onSelect = vi.fn();
    render(
        <MantineProvider>
            <MapOverlapList projects={projects} onHighlight={onHighlight} onSelect={onSelect} />
        </MantineProvider>,
    );
    return { onHighlight, onSelect };
}

describe("MapOverlapList", () => {
    it("names the number of projects and lists each with its number", () => {
        renderList();
        expect(screen.getByText("2 Projekte an dieser Stelle")).toBeInTheDocument();
        expect(screen.getByText("ABS Korridor Nord")).toBeInTheDocument();
        expect(screen.getByText("2-032-V01")).toBeInTheDocument();
        expect(screen.getByText("Elektrifizierung Mitte")).toBeInTheDocument();
    });

    it("highlights an entry on hover and clears it on leave", () => {
        const { onHighlight } = renderList();
        const row = screen.getByRole("button", { name: /Elektrifizierung Mitte/ });
        fireEvent.mouseEnter(row);
        expect(onHighlight).toHaveBeenLastCalledWith(2);
        fireEvent.mouseLeave(row);
        expect(onHighlight).toHaveBeenLastCalledWith(null);
    });

    it("selects an entry on click", () => {
        const { onSelect } = renderList();
        fireEvent.click(screen.getByRole("button", { name: /ABS Korridor Nord/ }));
        expect(onSelect).toHaveBeenCalledWith(1);
    });
});
