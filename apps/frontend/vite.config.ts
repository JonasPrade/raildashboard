/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    envPrefix: ["VITE_", "REACT_APP_"],
    envDir: "../../",
    build: {
        rollupOptions: {
            output: {
                // Stable vendor chunks so a release only invalidates the chunks
                // whose contents actually changed. @mantine/charts is excluded:
                // it drags recharts along and must stay in the lazy chunks of
                // the pages that use it.
                manualChunks(id: string) {
                    if (!id.includes("node_modules")) return undefined;
                    if (id.includes("maplibre-gl")) return "maplibre";
                    if (id.includes("@mantine/charts")) return undefined;
                    if (id.includes("@mantine")) return "mantine";
                    if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "react-vendor";
                    return undefined;
                },
            },
        },
    },
    test: {
        environment: "jsdom",
        globals: true,
        setupFiles: ["src/test-setup.ts"],
    },
});
