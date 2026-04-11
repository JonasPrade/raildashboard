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
