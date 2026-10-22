import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import { type Project, invalidateAfterGeometryChange, queryKeys } from "./queries";

function seededClient() {
    const client = new QueryClient();
    client.setQueryData(queryKeys.projectGroupGeometries(1, true), { geometries: {} });
    client.setQueryData(queryKeys.project(7), { id: 7 });
    client.setQueryData(queryKeys.project(8), { id: 8 });
    return client;
}

const isStale = (client: QueryClient, key: readonly unknown[]) =>
    client.getQueryState(key)?.isInvalidated ?? false;

describe("invalidateAfterGeometryChange", () => {
    it("marks the overview-map geometries and the parent project stale", () => {
        const client = seededClient();
        invalidateAfterGeometryChange(client, { id: 9, superior_project_id: 7 } as Project);

        expect(isStale(client, queryKeys.projectGroupGeometries(1, true))).toBe(true);
        expect(isStale(client, queryKeys.project(7))).toBe(true);
        expect(isStale(client, queryKeys.project(8))).toBe(false);
    });
});
