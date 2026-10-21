import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { localStorageColorSchemeManager, MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClientProvider } from "@tanstack/react-query";
import "@mantine/core/styles.css";
import "./shared/theme/tokens.css";
import "./shared/theme/mantine-bridge.css";
// Layout tokens only (page/card padding, map and header height, row height) until stage 4.
import "./components/chronicle/tokens.css";
import "@mantine/notifications/styles.css";

import { COLOR_SCHEME_STORAGE_KEY, theme, ThemeAttributeSync } from "./shared/theme";
import { router } from "./router";
import "./app.css";
import { queryClient } from "./lib/query";
import { AuthProvider } from "./lib/auth";

const root = document.getElementById("app");
if (!root) throw new Error("Root element #app not found");

// Default follows the system setting; the header toggle stores an explicit choice.
// index.html sets data-theme / data-mantine-color-scheme before first paint.
const colorSchemeManager = localStorageColorSchemeManager({ key: COLOR_SCHEME_STORAGE_KEY });

createRoot(root).render(
    <MantineProvider theme={theme} defaultColorScheme="auto" colorSchemeManager={colorSchemeManager}>
        <ThemeAttributeSync />
        <ModalsProvider>
            <QueryClientProvider client={queryClient}>
                <AuthProvider>
                    <Notifications />
                    <RouterProvider router={router} />
                </AuthProvider>
            </QueryClientProvider>
        </ModalsProvider>
    </MantineProvider>
);
