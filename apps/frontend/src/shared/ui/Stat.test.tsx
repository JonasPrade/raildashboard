import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { Stat, StatBand } from "./Stat";

describe("Stat", () => {
    it("renders figure, unit, title and label", () => {
        const { container } = render(<Stat value="3,8" unit="Mrd €" title="Gesamtkosten" label="VIB 2025" />);
        expect(container.querySelector(".idt-stat__num")).toHaveTextContent("3,8Mrd €");
        expect(container.querySelector(".idt-stat__num small")).toHaveTextContent("Mrd €");
        expect(screen.getByText("Gesamtkosten")).toHaveClass("idt-stat__title");
        expect(screen.getByText("VIB 2025")).toHaveClass("idt-stat__label");
    });

    it("uses the 56px figure for size lg and omits empty parts", () => {
        const { container } = render(<Stat value={312} size="lg" />);
        expect(container.querySelector(".idt-stat__num")).toHaveClass("idt-stat__num--lg");
        expect(container.querySelector(".idt-stat__title")).toBeNull();
        expect(container.querySelector(".idt-stat__label")).toBeNull();
    });

    it("applies an emphasis colour token to the figure", () => {
        const { container } = render(<Stat value={48} color="var(--accent-primary)" />);
        expect(container.querySelector(".idt-stat__num")).toHaveStyle({ color: "var(--accent-primary)" });
    });
});

describe("StatBand", () => {
    it("sets the column count for the grid", () => {
        const { container } = render(
            <StatBand columns={3}>
                <Stat value={1} />
                <Stat value={2} />
                <Stat value={3} />
            </StatBand>,
        );
        const band = container.querySelector(".idt-statband") as HTMLElement;
        expect(band.style.getPropertyValue("--statband-cols")).toBe("3");
        expect(band.querySelectorAll(".idt-stat")).toHaveLength(3);
    });
});
