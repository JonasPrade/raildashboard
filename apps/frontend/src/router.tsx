import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { AppShell, Loader, Group } from "@mantine/core";
import { Header } from "./components/Header";
import MapPage from "./features/map/MapPage";
import DocumentationPage from "./features/documentation/DocumentationPage";
import ProjectDetail from "./features/projects/ProjectDetail";

const UsersPage = lazy(() => import("./features/admin/UsersPage"));
const HaushaltsImportPage = lazy(() => import("./features/haushalt-import/HaushaltsImportPage"));
const HaushaltsReviewPage = lazy(() => import("./features/haushalt-import/HaushaltsReviewPage"));
const HaushaltsUnmatchedPage = lazy(() => import("./features/haushalt-import/HaushaltsUnmatchedPage"));
const HaushaltsGuidePage = lazy(() => import("./features/haushalt-import/HaushaltsGuidePage"));
const FinveOverviewPage = lazy(() => import("./features/finves/FinveOverviewPage"));

function Layout() {
    return (
        <AppShell header={{ height: 60 }} padding="md" style={{ minHeight: "100vh" }}>
            <AppShell.Header>
                <Header />
            </AppShell.Header>
            <AppShell.Main style={{ position: "relative", minHeight: "calc(100vh - 60px)" }}>
                <Outlet />
            </AppShell.Main>
        </AppShell>
    );
}

export const router = createBrowserRouter([
    {
        path: "/",
        element: <Layout />,
        children: [
            { index: true, element: <MapPage /> },
            { path: "documentation", element: <DocumentationPage /> },
            { path: "projects", element: <Navigate to="/?view=list" replace /> },
            { path: "projects/:projectId", element: <ProjectDetail /> },
            {
                path: "admin",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <UsersPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/haushalt-import",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <HaushaltsImportPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/haushalt-import/review/:parseResultId",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <HaushaltsReviewPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/haushalt-import/guide",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <HaushaltsGuidePage />
                    </Suspense>
                ),
            },
            {
                path: "admin/haushalt-unmatched",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <HaushaltsUnmatchedPage />
                    </Suspense>
                ),
            },
            {
                path: "finves",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <FinveOverviewPage />
                    </Suspense>
                ),
            },
        ]
    }
]);
