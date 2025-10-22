import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";

import { theme } from "./theme";
import { router } from "./router";
import "./app.css";

const root = document.getElementById("app");
if (!root) throw new Error("Root element #app not found");

createRoot(root).render(
    <MantineProvider theme={theme} defaultColorScheme="light">
        <Notifications />
        <RouterProvider router={router} />
    </MantineProvider>
);