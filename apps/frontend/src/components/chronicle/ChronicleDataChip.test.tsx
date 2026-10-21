import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ChronicleDataChip from "./ChronicleDataChip";

describe("ChronicleDataChip", () => {
    it("renders label text", () => {
        render(<ChronicleDataChip>Elektrifizierung</ChronicleDataChip>);
        expect(screen.getByText("Elektrifizierung")).toBeInTheDocument();
    });

    it("applies extra className", () => {
        const { container } = render(
            <ChronicleDataChip className="extra">Label</ChronicleDataChip>
        );
        expect(container.firstChild).toHaveClass("extra");
    });
});

describe("ChronicleDataChip dot", () => {
    it("takes the dot colour from the mapping or a category colour", () => {
        const { container, rerender } = render(<ChronicleDataChip>A</ChronicleDataChip>);
        const dot = () => container.querySelector("span[aria-hidden]") as HTMLElement;
        expect(dot().style.background).toBe("var(--accent-primary)");
        rerender(<ChronicleDataChip dotColor="var(--idt-chart-3)">A</ChronicleDataChip>);
        expect(dot().style.background).toBe("var(--idt-chart-3)");
    });
});
