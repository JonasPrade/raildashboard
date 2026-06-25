import { lazy, type ComponentType } from "react";

/**
 * Wrapper around React.lazy that recovers from "Failed to fetch dynamically
 * imported module" errors.
 *
 * These happen when the chunk a route points at no longer exists at the
 * expected URL — typically after a new deploy (hashed filenames changed) or,
 * in dev, after Vite rebuilt its module graph. The page the user already had
 * open still references the old chunk URL, so the import() rejects.
 *
 * Recovery: reload the page once so the browser fetches the current index.html
 * and the fresh chunk URLs. A sessionStorage flag prevents an endless reload
 * loop if the failure is genuine (e.g. the chunk really has a syntax error) —
 * after one failed retry we rethrow so the router's errorElement can render.
 */
export function lazyWithRetry<T extends ComponentType<unknown>>(
    factory: () => Promise<{ default: T }>,
) {
    const RELOAD_FLAG = "chunk-reload-attempted";

    return lazy(async () => {
        try {
            const mod = await factory();
            // Loaded fine — clear the flag so a future stale chunk can retry too.
            window.sessionStorage.removeItem(RELOAD_FLAG);
            return mod;
        } catch (err) {
            const alreadyRetried = window.sessionStorage.getItem(RELOAD_FLAG);
            if (!alreadyRetried) {
                window.sessionStorage.setItem(RELOAD_FLAG, "1");
                window.location.reload();
                // Keep Suspense hanging until the reload takes effect.
                return new Promise<never>(() => {});
            }
            throw err;
        }
    });
}
