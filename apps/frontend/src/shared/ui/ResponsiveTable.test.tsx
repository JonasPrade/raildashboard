import { render, screen } from "@testing-library/react";
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
});
