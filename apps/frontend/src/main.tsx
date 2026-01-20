import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClientProvider } from "@tanstack/react-query";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "maplibre-gl/dist/maplibre-gl.css";

import { theme } from "./theme";
import { router } from "./router";
import "./app.css";
import { queryClient } from "./lib/query";

const root = document.getElementById("app");
if (!root) throw new Error("Root element #app not found");

createRoot(root).render(
    <MantineProvider theme={theme} defaultColorScheme="light">
        <QueryClientProvider client={queryClient}>
            <Notifications />
            <RouterProvider router={router} />
        </QueryClientProvider>
    </MantineProvider>
);
