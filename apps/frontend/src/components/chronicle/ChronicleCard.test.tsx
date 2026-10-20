import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ChronicleCard from "./ChronicleCard";

describe("ChronicleCard", () => {
    it("renders children", () => {
        render(<ChronicleCard>Inhalt</ChronicleCard>);
        expect(screen.getByText("Inhalt")).toBeInTheDocument();
    });

    it("renders as a div by default", () => {
        const { container } = render(<ChronicleCard>Karte</ChronicleCard>);
        expect(container.firstChild?.nodeName).toBe("DIV");
    });

    it("applies accent style when accent prop is true", () => {
        const { container } = render(<ChronicleCard accent>Aktiv</ChronicleCard>);
        const el = container.firstChild as HTMLElement;
        expect(el.style.borderLeft).toBeTruthy();
    });

    it("uses accentColor for the left border", () => {
        const { container } = render(<ChronicleCard accentColor="var(--text-cat-warning)">Warnung</ChronicleCard>);
        const el = container.firstChild as HTMLElement;
        expect(el.style.borderLeft).toContain("var(--text-cat-warning)");
    });

    it("has no left accent border by default", () => {
        const { container } = render(<ChronicleCard>Normal</ChronicleCard>);
        const el = container.firstChild as HTMLElement;
        expect(el.style.borderLeft).toBe("");
    });

    it("applies float shadow when float prop is true", () => {
        const { container } = render(<ChronicleCard float>Float</ChronicleCard>);
        const el = container.firstChild as HTMLElement;
        expect(el.style.boxShadow).toBeTruthy();
    });
});
