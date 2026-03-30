import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { AuthProvider, useAuth } from "./auth";

// ---------------------------------------------------------------------------
// Mock the generated API client so no real HTTP requests are made
// ---------------------------------------------------------------------------

vi.mock("../shared/api/client", () => ({
    api: vi.fn(),
}));

vi.mock("./query", () => ({
    queryClient: { clear: vi.fn() },
}));

import { api } from "../shared/api/client";
import { queryClient } from "./query";

const mockApi = api as ReturnType<typeof vi.fn>;

// Wrap hooks in AuthProvider
function wrapper({ children }: { children: React.ReactNode }) {
    return createElement(AuthProvider, null, children);
}

// ---------------------------------------------------------------------------
// Initial session restore
// ---------------------------------------------------------------------------

describe("AuthProvider — session restore on mount", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("sets user when /users/me succeeds", async () => {
        const fakeUser = { id: 1, username: "alice", role: "viewer" as const };
        mockApi.mockResolvedValueOnce(fakeUser);

        const { result } = renderHook(() => useAuth(), { wrapper });

        await waitFor(() => expect(result.current.user).not.toBeNull());
        expect(result.current.user?.username).toBe("alice");
    });

    it("keeps user null when /users/me fails (no session)", async () => {
        mockApi.mockRejectedValueOnce(new Error("401"));

        const { result } = renderHook(() => useAuth(), { wrapper });

        await waitFor(() => expect(result.current.user).toBeNull());
    });
});

// ---------------------------------------------------------------------------
// login()
// ---------------------------------------------------------------------------

describe("useAuth — login", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("sets user on successful login", async () => {
        const fakeUser = { id: 2, username: "bob", role: "editor" as const };
        // First call: /users/me on mount → reject (not logged in)
        mockApi.mockRejectedValueOnce(new Error("401"));
        // Second call: POST /auth/session → success
        mockApi.mockResolvedValueOnce(undefined);
        // Third call: /users/me after login → return user
        mockApi.mockResolvedValueOnce(fakeUser);

        const { result } = renderHook(() => useAuth(), { wrapper });
        await waitFor(() => expect(result.current.user).toBeNull());

        await act(async () => {
            await result.current.login("bob", "secret");
        });

        expect(result.current.user?.username).toBe("bob");
        expect(result.current.user?.role).toBe("editor");
    });

    it("throws on failed login", async () => {
        // Mount: /users/me → reject
        mockApi.mockRejectedValueOnce(new Error("401"));
        // Login POST → reject (bad credentials)
        mockApi.mockRejectedValueOnce(new Error("401"));

        const { result } = renderHook(() => useAuth(), { wrapper });
        await waitFor(() => expect(result.current.user).toBeNull());

        await expect(
            act(async () => {
                await result.current.login("bad", "creds");
            })
        ).rejects.toThrow("Ungültige Anmeldedaten");
    });
});

// ---------------------------------------------------------------------------
// logout()
// ---------------------------------------------------------------------------

describe("useAuth — logout", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("clears user and query cache on logout", async () => {
        const fakeUser = { id: 1, username: "alice", role: "viewer" as const };
        // Mount: /users/me → return user (already logged in)
        mockApi.mockResolvedValueOnce(fakeUser);
        // Logout: DELETE /auth/session → success
        mockApi.mockResolvedValueOnce(undefined);

        const { result } = renderHook(() => useAuth(), { wrapper });
        await waitFor(() => expect(result.current.user?.username).toBe("alice"));

        await act(async () => {
            await result.current.logout();
        });

        expect(result.current.user).toBeNull();
        expect(queryClient.clear).toHaveBeenCalled();
    });
});
