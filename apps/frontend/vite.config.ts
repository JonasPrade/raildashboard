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
                // whose contents actually changed. Mantine and React/react-dom/
                // scheduler are merged into a single "vendor-react" chunk on
                // purpose: splitting them into separate chunks previously
                // produced a circular import between the two output files
                // (react-vendor's first statement imported from mantine, which
                // in turn depends on React), which crashed the app on load with
                // "can't access property useLayoutEffect of undefined". Mantine
                // is a peer-dependent UI layer used almost everywhere in this
                // app, so there's no meaningful cache-granularity loss from
                // shipping it together with React. @mantine/charts is excluded:
                // it drags recharts along and must stay in the lazy chunks of
                // the pages that use it.
                manualChunks(id: string) {
                    if (!id.includes("node_modules")) return undefined;
                    if (id.includes("maplibre-gl")) return "maplibre";
                    if (id.includes("@mantine/charts")) return undefined;
                    if (id.includes("@mantine")) return "vendor-react";
                    if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "vendor-react";
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
