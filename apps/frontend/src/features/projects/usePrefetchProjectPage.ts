import { useCallback, useRef } from "react";

import { usePrefetchProject } from "../../shared/api/queries";

/**
 * Warms both halves of a project detail page on hover/focus of a link to it:
 * the lazily loaded route chunk and the project data. By the time the click
 * lands, the page usually renders immediately instead of showing two spinners
 * in a row (chunk, then data).
 */
export function usePrefetchProjectPage() {
    const prefetchProject = usePrefetchProject();
    const chunkRequested = useRef(false);
    return useCallback(
        (projectId: number) => {
            if (!chunkRequested.current) {
                chunkRequested.current = true;
                // Same specifier as the route in router.tsx → same chunk.
                void import("./ProjectDetail").catch(() => {
                    chunkRequested.current = false;
                });
            }
            prefetchProject(projectId);
        },
        [prefetchProject],
    );
}
