import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ChronicleHeadline from "./ChronicleHeadline";

describe("ChronicleHeadline", () => {
    it("renders children as h1 by default", () => {
        render(<ChronicleHeadline>Haupttitel</ChronicleHeadline>);
        expect(screen.getByRole("heading", { level: 1, name: "Haupttitel" })).toBeInTheDocument();
    });

    it("renders as h2 when as='h2'", () => {
        render(<ChronicleHeadline as="h2">Abschnitt</ChronicleHeadline>);
        expect(screen.getByRole("heading", { level: 2, name: "Abschnitt" })).toBeInTheDocument();
    });

    it("renders as h3 when as='h3'", () => {
        render(<ChronicleHeadline as="h3">Unterabschnitt</ChronicleHeadline>);
        expect(screen.getByRole("heading", { level: 3, name: "Unterabschnitt" })).toBeInTheDocument();
    });

    it("applies extra className when provided", () => {
        const { container } = render(
            <ChronicleHeadline className="my-class">Titel</ChronicleHeadline>
        );
        expect(container.firstChild).toHaveClass("my-class");
    });
});
