import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, expect, it } from "vitest";

import PhaseBadge from "./PhaseBadge";

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
});
