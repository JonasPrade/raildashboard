import { createRef } from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectRegister, REGISTER_STORAGE_KEY, type RegisterSection } from "./ProjectRegister";

const originalMatchMedia = window.matchMedia;

function setCompact(compact: boolean) {
    window.matchMedia = ((query: string) => ({
        matches: compact && query.includes("62em"),
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
}

function makeSection(id: string, label: string, extra: Partial<RegisterSection> = {}): RegisterSection {
    const ref = createRef<HTMLDivElement>() as React.RefObject<HTMLDivElement | null>;
    const el = document.createElement("div");
    el.scrollIntoView = vi.fn();
    (ref as { current: HTMLDivElement | null }).current = el;
    return { id, label, ref, visible: true, ...extra };
}

function renderRegister(sections: RegisterSection[], onCreateTask?: () => void) {
    return render(
        <MantineProvider>
            <ProjectRegister sections={sections} onCreateTask={onCreateTask} />
        </MantineProvider>,
    );
}

beforeEach(() => {
    window.localStorage.clear();
    setCompact(false);
});

afterEach(() => {
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
});

describe("ProjectRegister (from 62em)", () => {
    it("lists only the visible sections under the label „Abschnitte“", () => {
        renderRegister([
            makeSection("details", "Projektdetails"),
            makeSection("texts", "Texte", { visible: false }),
            makeSection("finve", "FinVe"),
        ]);
        const nav = screen.getByRole("navigation", { name: "Abschnitte" });
        expect(within(nav).getByRole("button", { name: "Projektdetails" })).toBeInTheDocument();
        expect(within(nav).getByRole("button", { name: "FinVe" })).toBeInTheDocument();
        expect(within(nav).queryByRole("button", { name: "Texte" })).not.toBeInTheDocument();
    });

    it("renders nothing when no section is visible", () => {
        const { container } = renderRegister([makeSection("a", "A", { visible: false })]);
        expect(container.querySelector(".project-register")).toBeNull();
    });

    it("scrolls to a section on click", async () => {
        const finve = makeSection("finve", "FinVe");
        renderRegister([makeSection("details", "Projektdetails"), finve]);
        await userEvent.click(screen.getByRole("button", { name: "FinVe" }));
        expect(finve.ref.current?.scrollIntoView).toHaveBeenCalled();
    });

    it("opens a collapsed section before scrolling to it", async () => {
        const onOpen = vi.fn();
        renderRegister([makeSection("history", "Versionshistorie", { isCollapsible: true, isOpen: false, onOpen })]);
        await userEvent.click(screen.getByRole("button", { name: "Versionshistorie" }));
        expect(onOpen).toHaveBeenCalledOnce();
    });

    it("folds into a tab and remembers the state", async () => {
        const sections = [makeSection("details", "Projektdetails")];
        const { unmount } = renderRegister(sections);

        await userEvent.click(screen.getByRole("button", { name: "Abschnitte einklappen" }));
        expect(window.localStorage.getItem(REGISTER_STORAGE_KEY)).toBe("closed");
        expect(screen.queryByRole("button", { name: "Projektdetails" })).not.toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Abschnitte aufklappen" })).toBeInTheDocument();

        unmount();
        renderRegister(sections);
        expect(screen.getByRole("button", { name: "Abschnitte aufklappen" })).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: "Abschnitte aufklappen" }));
        expect(window.localStorage.getItem(REGISTER_STORAGE_KEY)).toBe("open");
        expect(screen.getByRole("button", { name: "Projektdetails" })).toBeInTheDocument();
    });

    it("still works when localStorage is unavailable", async () => {
        vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
            throw new Error("blocked");
        });
        vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
            throw new Error("blocked");
        });
        renderRegister([makeSection("details", "Projektdetails")]);
        await userEvent.click(screen.getByRole("button", { name: "Abschnitte einklappen" }));
        expect(screen.getByRole("button", { name: "Abschnitte aufklappen" })).toBeInTheDocument();
    });

    it("offers „Aufgabe erstellen“ when a handler is given", async () => {
        const onCreateTask = vi.fn();
        renderRegister([makeSection("details", "Projektdetails")], onCreateTask);
        await userEvent.click(screen.getByRole("button", { name: "Aufgabe erstellen" }));
        expect(onCreateTask).toHaveBeenCalledOnce();
    });
});

describe("ProjectRegister (below 62em)", () => {
    it("shows a button that opens the register as a sheet and closes it after a pick", async () => {
        setCompact(true);
        const finve = makeSection("finve", "FinVe");
        renderRegister([makeSection("details", "Projektdetails"), finve]);

        expect(screen.queryByRole("navigation", { name: "Abschnitte" })).not.toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: "Abschnitte" }));

        const nav = await screen.findByRole("navigation", { name: "Abschnitte" });
        await userEvent.click(within(nav).getByRole("button", { name: "FinVe" }));

        await waitFor(() =>
            expect(screen.queryByRole("navigation", { name: "Abschnitte" })).not.toBeInTheDocument(),
        );
        await waitFor(() => expect(finve.ref.current?.scrollIntoView).toHaveBeenCalled());
    });
});
