import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, expect, it } from "vitest";

import PhaseBadge, { PhaseTag } from "./PhaseBadge";

const renderBadge = (phase: string | null, lifecycle?: string | null) =>
    render(
        <MantineProvider>
            <PhaseBadge phase={phase} lifecycle={lifecycle} />
        </MantineProvider>,
    );

describe("PhaseBadge", () => {
    it("shows the German phase label", () => {
        renderBadge("GENEHMIGUNGSPLANUNG", "AKTIV");
        expect(screen.getByText("Genehmigungsplanung")).toBeInTheDocument();
        expect(screen.queryByText("Pausiert")).not.toBeInTheDocument();
    });

    it("shows Unbekannt for a missing or invalid phase", () => {
        renderBadge(null);
        expect(screen.getByText("Unbekannt")).toBeInTheDocument();
    });

    it("adds the lifecycle for paused projects but keeps the phase", () => {
        renderBadge("BAU", "PAUSIERT");
        expect(screen.getByText("Bau")).toBeInTheDocument();
        expect(screen.getByText("Pausiert")).toBeInTheDocument();
    });

    it("draws the phase tag with a square in the phase colour next to the text", () => {
        const { container } = render(
            <MantineProvider>
                <PhaseTag phase="IN_BETRIEB" />
            </MantineProvider>,
        );
        expect(screen.getByText("In Betrieb")).toBeInTheDocument();
        const square = container.querySelector("span[aria-hidden]") as HTMLElement;
        expect(square.style.background).toBe("var(--idt-success)");
    });
});
