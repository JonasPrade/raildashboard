import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmBadge } from "./index";

function renderBadge(props: Parameters<typeof ConfirmBadge>[0]) {
    return render(
        <MantineProvider>
            <ConfirmBadge {...props} />
        </MantineProvider>,
    );
}

describe("ConfirmBadge", () => {
    it("offers an explicit button once a project is assigned", async () => {
        const onToggle = vi.fn();
        renderBadge({ confirmed: false, canConfirm: true, onToggle });

        const button = screen.getByRole("button", { name: /übernehmen/i });
        await userEvent.click(button);
        expect(onToggle).toHaveBeenCalledOnce();
    });

    it("shows the confirmed badge and revokes on click", async () => {
        const onToggle = vi.fn();
        renderBadge({ confirmed: true, canConfirm: true, onToggle });

        expect(screen.queryByRole("button", { name: /übernehmen/i })).not.toBeInTheDocument();
        await userEvent.click(screen.getByText("aktiv"));
        expect(onToggle).toHaveBeenCalledOnce();
    });

    it("stays inert while no project is assigned", async () => {
        const onToggle = vi.fn();
        renderBadge({ confirmed: false, canConfirm: false, onToggle });

        await userEvent.click(screen.getByText("offen"));
        expect(onToggle).not.toHaveBeenCalled();
    });
});
