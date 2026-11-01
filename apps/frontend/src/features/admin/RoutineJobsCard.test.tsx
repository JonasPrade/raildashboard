import { render, screen, within } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RoutineJobsCard from "./RoutineJobsCard";
import { formatDuration, triggerLabel } from "./routineJobs";

const api = vi.hoisted(() => vi.fn());
vi.mock("../../shared/api/client", () => ({ api }));

function renderCard() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
        <QueryClientProvider client={client}>
            <MantineProvider>
                <MemoryRouter>
                    <RoutineJobsCard />
                </MemoryRouter>
            </MantineProvider>
        </QueryClientProvider>,
    );
}

const job = (key: string, over: Record<string, unknown> = {}) => ({
    key,
    label: { bauportal: "DB-Bauportal", parliament: "Abgeordnete (abgeordnetenwatch)", progress_recompute: "Planungsstand neu berechnen" }[key],
    schedule_label: "täglich 02:40 Uhr",
    interval_hours: 24,
    next_run_at: "2026-11-02T01:40:00Z",
    admin_path: "/admin/bauportal-import",
    admin_label: "Zum Bauportal-Abruf",
    running_since: null,
    last_run: {
        started_at: "2026-11-01T01:40:00Z",
        finished_at: "2026-11-01T01:40:12Z",
        duration_seconds: 12,
        status: "success",
        error: null,
        stats: null,
        triggered_by_user_id: null,
        triggered_by_username: null,
    },
    last_success_at: "2026-11-01T01:40:00Z",
    overdue: false,
    needs_attention: false,
    ...over,
});

beforeEach(() => api.mockReset());

describe("RoutineJobsCard", () => {
    it("lists every job with schedule, trigger, duration and status", async () => {
        api.mockResolvedValue({
            enabled: true,
            timezone: "Europe/Berlin",
            needs_attention: false,
            jobs: [job("bauportal"), job("parliament"), job("progress_recompute")],
        });
        renderCard();
        const entry = await screen.findByTestId("routine-job-bauportal");
        expect(api).toHaveBeenCalledWith("/api/v1/system/routine-jobs");
        expect(within(entry).getByText("DB-Bauportal")).toBeInTheDocument();
        expect(entry.textContent).toContain("täglich 02:40 Uhr");
        expect(entry.textContent).toContain("nächster Termin");
        expect(entry.textContent).toContain("Zeitplan");
        expect(entry.textContent).toContain("Dauer 12 s");
        expect(within(entry).getByText("erfolgreich")).toBeInTheDocument();
        expect(within(entry).getByRole("link", { name: /Zum Bauportal-Abruf/ })).toHaveAttribute(
            "href",
            "/admin/bauportal-import",
        );
        expect(screen.getAllByTestId(/routine-job-/)).toHaveLength(3);
        expect(screen.getByText("Alles im Plan")).toBeInTheDocument();
    });

    it("shows the error text and the reason for attention", async () => {
        api.mockResolvedValue({
            enabled: true,
            timezone: "Europe/Berlin",
            needs_attention: true,
            jobs: [
                job("bauportal", {
                    needs_attention: true,
                    last_run: { ...job("bauportal").last_run, status: "error", error: "ConnectError: no route" },
                }),
                job("parliament", { overdue: true, needs_attention: true, last_run: null, last_success_at: null }),
            ],
        });
        renderCard();
        const failed = await screen.findByTestId("routine-job-bauportal");
        expect(within(failed).getByText("ConnectError: no route")).toBeInTheDocument();
        expect(within(failed).getByText("Letzter Lauf fehlgeschlagen")).toBeInTheDocument();
        const never = screen.getByTestId("routine-job-parliament");
        expect(within(never).getByText("noch kein Lauf")).toBeInTheDocument();
        expect(within(never).getByText("Noch kein erfolgreicher Lauf")).toBeInTheDocument();
        expect(screen.getByText("Bitte prüfen")).toBeInTheDocument();
    });

    it("says when the schedule is switched off", async () => {
        api.mockResolvedValue({
            enabled: false,
            timezone: "Europe/Berlin",
            needs_attention: true,
            jobs: [job("bauportal", { next_run_at: null, needs_attention: true })],
        });
        renderCard();
        expect(await screen.findByText("Zeitplan abgeschaltet (Env)")).toBeInTheDocument();
        expect(screen.getByTestId("routine-job-bauportal").textContent).not.toContain("nächster Termin");
    });

    it("stays readable at a 360 px viewport (one column, no table)", async () => {
        window.innerWidth = 360;
        window.dispatchEvent(new Event("resize"));
        api.mockResolvedValue({
            enabled: true,
            timezone: "Europe/Berlin",
            needs_attention: false,
            jobs: [job("bauportal")],
        });
        const { container } = renderCard();
        await screen.findByTestId("routine-job-bauportal");
        // Cards instead of a wide table: nothing forces horizontal scrolling.
        expect(container.querySelector("table")).toBeNull();
    });
});

describe("routineJobs helpers", () => {
    it("names the scheduler as „Zeitplan“ and a user by name", () => {
        expect(triggerLabel({ triggered_by_user_id: null })).toBe("Zeitplan");
        expect(triggerLabel({ triggered_by_user_id: 3, triggered_by_username: "jonas" })).toBe("von jonas");
    });

    it("formats durations", () => {
        expect(formatDuration(12)).toBe("12 s");
        expect(formatDuration(185)).toBe("3 min 5 s");
        expect(formatDuration(3720)).toBe("1 h 2 min");
        expect(formatDuration(null)).toBe("—");
    });
});
