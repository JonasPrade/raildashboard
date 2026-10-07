import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, beforeEach, vi } from "vitest";

import ApiKeysAdminPage from "./ApiKeysAdminPage";

const permissions = new Set<string>();
const createKey = vi.fn();

vi.mock("../../lib/auth", () => ({
    useAuth: () => ({ can: (perm: string) => permissions.has(perm) }),
}));

vi.mock("../../shared/api/queries", () => ({
    useApiKeys: () => ({
        data: [
            {
                id: 1,
                name: "Laptop",
                prefix: "abcdefghijkl",
                scopes: ["mcp.access"],
                user_id: 1,
                username: "admin",
                created_at: "2026-10-01T10:00:00",
                last_used_at: null,
                expires_at: "2099-01-01T10:00:00",
                revoked_at: null,
            },
        ],
        isLoading: false,
        isError: false,
    }),
    useAllApiKeys: () => ({ data: [] }),
    useCreateApiKey: () => ({ mutateAsync: createKey, isPending: false }),
    useRevokeApiKey: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function renderPage() {
    return render(
        <MantineProvider>
            <MemoryRouter>
                <ApiKeysAdminPage />
            </MemoryRouter>
        </MantineProvider>,
    );
}

describe("ApiKeysAdminPage", () => {
    beforeEach(() => {
        permissions.clear();
        createKey.mockReset();
    });

    it("denies access without mcp.access", () => {
        renderPage();
        expect(screen.getByText("Kein Zugriff")).toBeInTheDocument();
    });

    it("lists own keys with their read-only preset", () => {
        permissions.add("mcp.access");
        renderPage();
        expect(screen.getByText("Laptop")).toBeInTheDocument();
        expect(screen.getByText("Nur lesen")).toBeInTheDocument();
        expect(screen.getByText("rdb_abcdefghijkl_…")).toBeInTheDocument();
        // The admin-wide table needs user.manage.
        expect(screen.queryByText("Alle Keys")).not.toBeInTheDocument();
    });

    it("creates a read-only key by default and shows the token once", async () => {
        permissions.add("mcp.access");
        createKey.mockResolvedValue({
            id: 2,
            name: "Claude",
            prefix: "zzzzzzzzzzzz",
            scopes: ["mcp.access"],
            user_id: 1,
            username: "admin",
            created_at: "2026-10-07T10:00:00",
            last_used_at: null,
            expires_at: "2027-01-05T10:00:00",
            revoked_at: null,
            token: "rdb_zzzzzzzzzzzz_secret-value",
        });
        const user = userEvent.setup();
        renderPage();

        await user.click(screen.getByRole("button", { name: "Neuen Key anlegen" }));
        await user.type(await screen.findByRole("textbox", { name: /Bezeichnung/ }), "Claude");
        await user.click(screen.getByRole("button", { name: "Key erstellen" }));

        expect(createKey).toHaveBeenCalledWith({ name: "Claude", scopes: ["mcp.access"] });
        expect(await screen.findByText("rdb_zzzzzzzzzzzz_secret-value")).toBeInTheDocument();
        expect(screen.getByText("Nur jetzt sichtbar")).toBeInTheDocument();
    });
});
