import { useState, type ReactNode } from "react";
import { act, render, screen } from "@testing-library/react";
import { MantineProvider, Table } from "@mantine/core";
import { describe, it, expect } from "vitest";

import { ResponsiveTable } from "./ResponsiveTable";

function renderTable(minWidth?: number) {
    return render(
        <MantineProvider>
            <ResponsiveTable minWidth={minWidth}>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Projekt</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    <Table.Tr>
                        <Table.Td>Ausbau Hanau–Würzburg</Table.Td>
                    </Table.Tr>
                </Table.Tbody>
            </ResponsiveTable>
        </MantineProvider>,
    );
}

type Row = { name: string; phase: string; km: number };

function ProjectTable({ rows, sortControl }: { rows: Row[]; sortControl?: ReactNode }) {
    return (
        <ResponsiveTable sortControl={sortControl}>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th className="idt-check-cell" />
                    <Table.Th>Projekt</Table.Th>
                    <Table.Th data-role="status">Phase</Table.Th>
                    <Table.Th className="num">
                        Länge <span>(km)</span>
                    </Table.Th>
                    <Table.Th data-card="hide">Aktionen</Table.Th>
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {rows.map((r) => (
                    <Table.Tr key={r.name}>
                        <Table.Td className="idt-check-cell">
                            <input type="checkbox" aria-label={`${r.name} auswählen`} />
                        </Table.Td>
                        <Table.Td>{r.name}</Table.Td>
                        <Table.Td>{r.phase}</Table.Td>
                        <Table.Td className="num">{r.km}</Table.Td>
                        <Table.Td>
                            <button type="button">Bearbeiten</button>
                        </Table.Td>
                    </Table.Tr>
                ))}
                <Table.Tr>
                    <Table.Td colSpan={5}>Ende der Liste</Table.Td>
                </Table.Tr>
            </Table.Tbody>
        </ResponsiveTable>
    );
}

const ROWS: Row[] = [
    { name: "Knoten Frankfurt", phase: "Bau", km: 28 },
    { name: "NBS Dresden–Prag", phase: "Vorplanung", km: 43 },
];

describe("ResponsiveTable", () => {
    it("renders the table contents unchanged", () => {
        renderTable();
        expect(screen.getByRole("table")).toBeInTheDocument();
        expect(screen.getByText("Ausbau Hanau–Würzburg")).toBeInTheDocument();
    });

    it("puts the table inside a scrollable wrapper instead of letting it widen the page", () => {
        renderTable(720);
        // table → scrollContainerInner → scrollContainer
        const scrollContainer = screen.getByRole("table").parentElement?.parentElement as HTMLElement;

        expect(scrollContainer.className).toContain("TableScrollContainer");
        expect(scrollContainer.style.getPropertyValue("--table-overflow")).toBe("auto");
        // 720px / 16 = 45rem
        expect(scrollContainer.style.getPropertyValue("--table-min-width")).toContain("45rem");
    });

    it("wraps the table in the 2px frame and gives it the idt-table class", () => {
        renderTable();
        const table = screen.getByRole("table");
        expect(table).toHaveClass("idt-table");
        expect(table.closest(".idt-table-frame")).not.toBeNull();
        expect(table.closest(".idt-rtable")).toHaveAttribute("data-card-mode", "cards");
    });

    it("card mode: writes the column head text as data-label onto every cell", () => {
        render(
            <MantineProvider>
                <ProjectTable rows={ROWS} />
            </MantineProvider>,
        );
        const km = screen.getByText("43").closest("td")!;
        expect(km).toHaveAttribute("data-label", "Länge (km)");
        expect(screen.getByText("Vorplanung").closest("td")).toHaveAttribute("data-label", "Phase");
    });

    it("card mode: first content cell is the heading, the checkbox cell sits in front of it", () => {
        render(
            <MantineProvider>
                <ProjectTable rows={ROWS} />
            </MantineProvider>,
        );
        const name = screen.getByText("Knoten Frankfurt").closest("td")!;
        expect(name).toHaveAttribute("data-card-title");
        const check = screen.getByLabelText("Knoten Frankfurt auswählen").closest("td")!;
        expect(check).toHaveAttribute("data-card-check");
        expect(check).not.toHaveAttribute("data-card-title");
        expect(name.closest("tr")).toHaveAttribute("data-card-has-check");
    });

    it("card mode: marks the status cell from the column head", () => {
        render(
            <MantineProvider>
                <ProjectTable rows={ROWS} />
            </MantineProvider>,
        );
        expect(screen.getByText("Bau").closest("td")).toHaveAttribute("data-card-status");
        expect(screen.getByText("43").closest("td")).not.toHaveAttribute("data-card-status");
    });

    it("card mode: hides columns opted out with data-card=hide", () => {
        render(
            <MantineProvider>
                <ProjectTable rows={ROWS} />
            </MantineProvider>,
        );
        const actions = screen.getAllByRole("button", { name: "Bearbeiten" })[0]!.closest("td")!;
        expect(actions).toHaveAttribute("data-card-hidden");
        expect(screen.getByText("43").closest("td")).not.toHaveAttribute("data-card-hidden");
    });

    it("card mode: a cell spanning the whole row gets no label", () => {
        render(
            <MantineProvider>
                <ProjectTable rows={ROWS} />
            </MantineProvider>,
        );
        const full = screen.getByText("Ende der Liste").closest("td")!;
        expect(full).toHaveAttribute("data-card-full");
        expect(full).toHaveAttribute("data-label", "");
        expect(full).not.toHaveAttribute("data-card-title");
    });

    it("card mode: labels rows that appear after the first render", () => {
        function Growing() {
            const [rows, setRows] = useState<Row[]>(ROWS.slice(0, 1));
            return (
                <>
                    <button type="button" onClick={() => setRows(ROWS)}>
                        mehr
                    </button>
                    <ProjectTable rows={rows} />
                </>
            );
        }
        render(
            <MantineProvider>
                <Growing />
            </MantineProvider>,
        );
        act(() => screen.getByRole("button", { name: "mehr" }).click());
        const added = screen.getByText("NBS Dresden–Prag").closest("td")!;
        expect(added).toHaveAttribute("data-card-title");
        expect(screen.getByText("43").closest("td")).toHaveAttribute("data-label", "Länge (km)");
    });

    it("card mode: labels columns under a grouped two-row head", () => {
        render(
            <MantineProvider>
                <ResponsiveTable>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th rowSpan={2}>Bezeichnung</Table.Th>
                            <Table.Th colSpan={2}>Kosten</Table.Th>
                            <Table.Th rowSpan={2} data-role="status">Status</Table.Th>
                        </Table.Tr>
                        <Table.Tr>
                            <Table.Th className="num">Vorjahr</Table.Th>
                            <Table.Th className="num">Aktuell</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        <Table.Tr>
                            <Table.Td>Knoten Hamburg</Table.Td>
                            <Table.Td className="num">10</Table.Td>
                            <Table.Td className="num">12</Table.Td>
                            <Table.Td>offen</Table.Td>
                        </Table.Tr>
                    </Table.Tbody>
                </ResponsiveTable>
            </MantineProvider>,
        );
        expect(screen.getByText("Knoten Hamburg").closest("td")).toHaveAttribute("data-card-title");
        expect(screen.getByText("10").closest("td")).toHaveAttribute("data-label", "Vorjahr");
        expect(screen.getByText("12").closest("td")).toHaveAttribute("data-label", "Aktuell");
        expect(screen.getByText("offen").closest("td")).toHaveAttribute("data-card-status");
    });

    it("renders the sort control only when given", () => {
        const { rerender } = render(
            <MantineProvider>
                <ProjectTable rows={ROWS} />
            </MantineProvider>,
        );
        expect(document.querySelector(".idt-rtable__sort")).toBeNull();
        rerender(
            <MantineProvider>
                <ProjectTable rows={ROWS} sortControl={<span>Sortiert: Projekt</span>} />
            </MantineProvider>,
        );
        expect(screen.getByText("Sortiert: Projekt").closest(".idt-rtable__sort")).not.toBeNull();
    });

    it("tables without a head row are left plain (no cards)", () => {
        render(
            <MantineProvider>
                <ResponsiveTable variant="vertical">
                    <Table.Tbody>
                        <Table.Tr>
                            <Table.Th>Länge</Table.Th>
                            <Table.Td>12 km</Table.Td>
                        </Table.Tr>
                    </Table.Tbody>
                </ResponsiveTable>
            </MantineProvider>,
        );
        const table = screen.getByRole("table");
        expect(table.closest(".idt-rtable")).toHaveAttribute("data-card-mode", "plain");
        expect(screen.getByText("12 km")).not.toHaveAttribute("data-label");
    });
});
