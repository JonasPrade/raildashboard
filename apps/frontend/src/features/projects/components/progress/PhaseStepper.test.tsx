import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, expect, it } from "vitest";

import PhaseStepper, { type StepperForecastStep } from "./PhaseStepper";

const renderStepper = (forecastSteps: StepperForecastStep[] | null) =>
    render(
        <MantineProvider>
            <PhaseStepper current="NICHT_GESTARTET" unknown forecastSteps={forecastSteps} />
        </MantineProvider>,
    );

describe("PhaseStepper forecast row", () => {
    it("shows only forecast steps with a known date", () => {
        renderStepper([
            { phase: "VORPLANUNG", expected_date: null, source: "Schätzung" },
            { phase: "BAU", expected_date: null, source: "Schätzung" },
            { phase: "IN_BETRIEB", expected_date: "2030-12-01", source: "GVFG" },
        ]);
        expect(screen.getByText("Prognose")).toBeInTheDocument();
        expect(screen.getByText("12/2030")).toBeInTheDocument();
        expect(screen.getByText("GVFG")).toBeInTheDocument();
        expect(screen.queryByText("Schätzung")).not.toBeInTheDocument();
    });

    it("omits the row when no step has a date", () => {
        renderStepper([{ phase: "BAU", expected_date: null, source: "Schätzung" }]);
        expect(screen.queryByText("Prognose")).not.toBeInTheDocument();
    });
});
