import { useEffect } from "react";
import { useComputedColorScheme } from "@mantine/core";

/** localStorage key of the explicit light/dark choice (docs/DESIGN.md → Dunkelfassung).
 *  index.html reads the same key before first paint; keep both in sync. */
export const COLOR_SCHEME_STORAGE_KEY = "schienendashboard.thema";

/** Mirrors Mantine's computed colour scheme into <html data-theme>, where the DS
 *  dark tokens (tokens.css → [data-theme="dark"]) apply. Renders nothing. */
export function ThemeAttributeSync() {
    const scheme = useComputedColorScheme("light");
    useEffect(() => {
        document.documentElement.dataset.theme = scheme;
    }, [scheme]);
    return null;
}
