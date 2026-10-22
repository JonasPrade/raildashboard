import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Alert, Badge, Button, MantineProvider, Table, mergeMantineTheme, DEFAULT_THEME } from "@mantine/core";

import { colorFamily, theme } from "./theme";

const full = mergeMantineTheme(DEFAULT_THEME, theme);
const resolve = (variant: string, color?: string) =>
    full.variantColorResolver({ color: color ?? full.primaryColor, theme: full, variant });

function renderWithTheme(ui: React.ReactNode) {
    return render(<MantineProvider theme={theme}>{ui}</MantineProvider>);
}

describe("IDT theme — colour semantics", () => {
    it("maps Mantine colour names onto DS families", () => {
        expect(colorFamily("violet")).toBe("primary");
        expect(colorFamily(undefined)).toBe("primary");
        expect(colorFamily("red.6")).toBe("red");
        expect(colorFamily("blue")).toBe("ink");
        expect(colorFamily("orange")).toBe("amber");
        expect(colorFamily("var(--text-strong)")).toBeNull();
    });

    it("fills the primary action with the DS accent in both schemes", () => {
        const c = resolve("filled");
        expect(c.background).toBe("var(--accent-primary)");
        expect(c.hover).toBe("var(--accent-primary-hover)");
        expect(c.color).toBe("var(--text-on-accent)");
    });

    it("frames default and outline in ink, red outline in danger", () => {
        expect(resolve("default").border).toContain("var(--border-frame)");
        expect(resolve("outline", "teal").border).toContain("var(--border-frame)");
        expect(resolve("outline", "teal").color).toBe("var(--text-strong)");
        const red = resolve("outline", "red");
        expect(red.border).toContain("var(--idt-danger)");
        expect(red.color).toBe("var(--idt-danger-text)");
    });

    it("never colours the text of a light tag", () => {
        for (const color of ["violet", "cyan", "teal", "gray", "red", "green", "yellow"]) {
            expect(resolve("light", color).color).toBe("var(--text-strong)");
        }
        expect(resolve("light", "violet").background).toBe("var(--idt-violet-soft)");
        expect(resolve("light", "cyan").background).toBe("var(--idt-cyan-soft)");
        expect(resolve("light", "gray").background).toBe("var(--surface-alt)");
    });

    it("keeps Mantine's logic for CSS colour strings", () => {
        expect(resolve("outline", "var(--text-strong)").color).toBe("var(--text-strong)");
    });
});

describe("IDT theme — component classes", () => {
    it("marks buttons, badges and alerts with their tone", () => {
        renderWithTheme(
            <>
                <Button color="red" variant="outline">Entfernen</Button>
                <Badge variant="light" color="cyan">Nahverkehr</Badge>
                <Alert color="red" title="Fehler">Nicht geladen</Alert>
            </>,
        );
        expect(screen.getByRole("button", { name: "Entfernen" })).toHaveClass("idt-button", "idt-tone-red");
        expect(screen.getByText("Nahverkehr").closest(".mantine-Badge-root")).toHaveClass("idt-badge", "idt-tone-cyan");
        expect(screen.getByRole("alert")).toHaveClass("idt-alert", "idt-tone-red");
    });

    it("forces table striping off and puts .idt-table on every table", () => {
        const { container } = renderWithTheme(
            <Table>
                <Table.Tbody>
                    <Table.Tr>
                        <Table.Td>a</Table.Td>
                    </Table.Tr>
                </Table.Tbody>
            </Table>,
        );
        const table = container.querySelector("table");
        expect(table).toHaveClass("idt-table");
        expect(table).not.toHaveAttribute("data-striped");
    });
});
