import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClientProvider } from "@tanstack/react-query";
import { pdfjs } from "react-pdf";
import "@mantine/core/styles.css";
import "./components/chronicle/tokens.css";
import "@mantine/charts/styles.css";
import "@mantine/notifications/styles.css";
import "maplibre-gl/dist/maplibre-gl.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

import { theme } from "./theme";
import { router } from "./router";
import "./app.css";
import { queryClient } from "./lib/query";
import { AuthProvider } from "./lib/auth";

const root = document.getElementById("app");
if (!root) throw new Error("Root element #app not found");

createRoot(root).render(
    <MantineProvider theme={theme} defaultColorScheme="light">
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
