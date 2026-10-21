import { render, screen, fireEvent } from "@testing-library/react";
import { Button, MantineProvider } from "@mantine/core";
import { describe, it, expect, vi } from "vitest";
import type { ReactNode } from "react";

import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";
import { SaveStatus } from "./SaveStatus";

function renderUi(ui: ReactNode) {
    return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("LoadingState", () => {
    it("is a busy status region with the default label and no spinner", () => {
        const { container } = renderUi(<LoadingState />);
        const status = screen.getByRole("status", { name: "Lädt …" });
        expect(status).toHaveAttribute("aria-busy", "true");
        expect(container.querySelector(".mantine-Loader-root")).toBeNull();
        expect(screen.getAllByTestId("loading-bar")).toHaveLength(3);
    });

    it("renders n rows", () => {
        renderUi(<LoadingState rows={6} label="Projekte laden" />);
        expect(screen.getByRole("status", { name: "Projekte laden" })).toBeInTheDocument();
        expect(screen.getAllByTestId("loading-bar")).toHaveLength(6);
    });

    it("renders a single block of the given height", () => {
        renderUi(<LoadingState height={320} />);
        const bars = screen.getAllByTestId("loading-bar");
        expect(bars).toHaveLength(1);
        expect(bars[0].style.getPropertyValue("--skeleton-height")).toContain("20rem");
    });
});

describe("EmptyState", () => {
    it("shows title, sentence and action", () => {
        renderUi(
            <EmptyState title="Keine Projekte" action={<Button variant="default">Projekt anlegen</Button>}>
                Lege das erste Projekt an.
            </EmptyState>,
        );
        expect(screen.getByRole("heading", { name: "Keine Projekte" })).toBeInTheDocument();
        expect(screen.getByText("Lege das erste Projekt an.")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Projekt anlegen" })).toBeInTheDocument();
    });
});

describe("ErrorState", () => {
    it("is an alert with the default title and calls onRetry", () => {
        const onRetry = vi.fn();
        renderUi(<ErrorState onRetry={onRetry}>Die Liste kam nicht an.</ErrorState>);
        const alert = screen.getByRole("alert");
        expect(alert).toHaveTextContent("Laden fehlgeschlagen");
        expect(alert).toHaveTextContent("Die Liste kam nicht an.");
        fireEvent.click(screen.getByRole("button", { name: "Erneut versuchen" }));
        expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it("omits the retry button without onRetry", () => {
        renderUi(<ErrorState title="Kaputt" />);
        expect(screen.getByRole("alert")).toHaveTextContent("Kaputt");
        expect(screen.queryByRole("button")).toBeNull();
    });
});

describe("SaveStatus", () => {
    it("shows the save time when saved", () => {
        renderUi(<SaveStatus state="saved" savedAt={new Date(2026, 9, 21, 12, 4)} />);
        expect(screen.getByText("gespeichert 12:04")).toBeInTheDocument();
    });

    it("shows the running state", () => {
        renderUi(<SaveStatus state="saving" />);
        expect(screen.getByText("schreibt …")).toBeInTheDocument();
    });

    it("shows the error state with a retry link", () => {
        const onRetry = vi.fn();
        renderUi(<SaveStatus state="error" onRetry={onRetry} />);
        expect(screen.getByText("nicht gespeichert")).toBeInTheDocument();
        fireEvent.click(screen.getByRole("button", { name: "erneut" }));
        expect(onRetry).toHaveBeenCalledTimes(1);
    });
});
