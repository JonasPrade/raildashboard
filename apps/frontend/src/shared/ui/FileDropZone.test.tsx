import { fireEvent, render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, it, expect, vi } from "vitest";

import { FileDropZone } from "./FileDropZone";
import { matchesAccept } from "./fileAccept";

vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

const pdf = new File(["%PDF"], "bericht.pdf", { type: "application/pdf" });
const png = new File([""], "logo.png", { type: "image/png" });

function dataTransfer(files: File[]) {
    return { types: ["Files"], files, dropEffect: "none" };
}

function renderZone(onFiles: (files: File[]) => void, multiple = false) {
    render(
        <MantineProvider>
            <FileDropZone accept="application/pdf" multiple={multiple} onFiles={onFiles} label="PDF hier ablegen">
                <span>Zone</span>
            </FileDropZone>
        </MantineProvider>,
    );
    return screen.getByText("Zone").parentElement as HTMLElement;
}

describe("matchesAccept", () => {
    it("matches MIME types, wildcards and extensions", () => {
        expect(matchesAccept(pdf, "application/pdf")).toBe(true);
        expect(matchesAccept(png, "image/*")).toBe(true);
        expect(matchesAccept(pdf, ".PDF")).toBe(true);
        expect(matchesAccept(png, "application/pdf,.docx")).toBe(false);
        expect(matchesAccept(png, undefined)).toBe(true);
    });
});

describe("FileDropZone", () => {
    it("shows the overlay while a file is dragged over and hides it again", () => {
        const zone = renderZone(vi.fn());
        fireEvent.dragEnter(zone, { dataTransfer: dataTransfer([pdf]) });
        expect(screen.getByText("PDF hier ablegen")).toBeInTheDocument();
        fireEvent.dragLeave(zone, { dataTransfer: dataTransfer([pdf]) });
        expect(screen.queryByText("PDF hier ablegen")).not.toBeInTheDocument();
    });

    it("passes only accepted files on, and only the first one unless multiple", () => {
        const onFiles = vi.fn();
        const zone = renderZone(onFiles);
        const second = new File(["%PDF"], "anhang.pdf", { type: "application/pdf" });
        fireEvent.drop(zone, { dataTransfer: dataTransfer([png, pdf, second]) });
        expect(onFiles).toHaveBeenCalledWith([pdf]);
    });

    it("does not call onFiles when nothing matches", () => {
        const onFiles = vi.fn();
        const zone = renderZone(onFiles, true);
        fireEvent.drop(zone, { dataTransfer: dataTransfer([png]) });
        expect(onFiles).not.toHaveBeenCalled();
    });
});
