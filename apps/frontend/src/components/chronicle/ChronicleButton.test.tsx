import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ChronicleButton from "./ChronicleButton";

describe("ChronicleButton", () => {
    it("renders label", () => {
        render(<ChronicleButton>Projektgruppen</ChronicleButton>);
        expect(screen.getByRole("button", { name: "Projektgruppen" })).toBeInTheDocument();
    });

    it("calls onClick when clicked", async () => {
        const handler = vi.fn();
        render(<ChronicleButton onClick={handler}>Klick</ChronicleButton>);
        await userEvent.click(screen.getByRole("button"));
        expect(handler).toHaveBeenCalledOnce();
    });

    it("is disabled when disabled prop is set", () => {
        render(<ChronicleButton disabled>Gesperrt</ChronicleButton>);
        expect(screen.getByRole("button")).toBeDisabled();
    });

    it("renders ghost variant without gradient background", () => {
        const { container } = render(<ChronicleButton variant="ghost">Ghost</ChronicleButton>);
        const btn = container.firstChild as HTMLElement;
        expect(btn.style.background).toBe("");
    });
});
