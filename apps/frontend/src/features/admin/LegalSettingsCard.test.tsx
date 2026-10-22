import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LegalSettingsCard } from "./LegalSettingsCard";

const mutate = vi.fn();

vi.mock("../../shared/api/queries", () => ({
    useAppSettings: () => ({
        data: {
            map_group_mode: "preconfigured",
            impressum_url: null,
            impressum_markdown: "Alter Text",
            datenschutz_url: null,
            datenschutz_markdown: null,
        },
    }),
    useUpdateAppSettings: () => ({ mutate, isPending: false }),
}));

function renderCard() {
    return render(
        <MantineProvider>
            <MemoryRouter>
                <LegalSettingsCard />
            </MemoryRouter>
        </MantineProvider>,
    );
}

describe("LegalSettingsCard", () => {
    beforeEach(() => mutate.mockReset());

    it("sends only the changed fields, empty text clears", async () => {
        const user = userEvent.setup();
        renderCard();

        await user.type(screen.getByLabelText(/Datenschutz – URL/), "https://example.org/ds");
        await user.clear(screen.getByLabelText(/Impressum – Text/));
        await user.click(screen.getByRole("button", { name: "Speichern" }));

        expect(mutate).toHaveBeenCalledWith(
            { datenschutz_url: "https://example.org/ds", impressum_markdown: "" },
            expect.anything(),
        );
    });

    it("blocks saving a URL without http(s)", async () => {
        const user = userEvent.setup();
        renderCard();

        await user.type(screen.getByLabelText(/Impressum – URL/), "example.org");

        expect(screen.getByText("Adresse muss mit http:// oder https:// beginnen")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Speichern" })).toBeDisabled();
    });
});
