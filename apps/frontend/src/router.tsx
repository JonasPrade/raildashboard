import { Suspense } from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { AppShell, Loader, Group } from "@mantine/core";
import { Header } from "./components/Header";
import RouteErrorBoundary from "./components/RouteErrorBoundary";
import { lazyWithRetry } from "./lib/lazyWithRetry";
import MapPage from "./features/map/MapPage";
import DocumentationPage from "./features/documentation/DocumentationPage";

// Lazy like all other routes: ProjectDetail transitively pulls in recharts,
// react-markdown and terra-draw, which would otherwise land in the entry chunk.
const ProjectDetail = lazyWithRetry(() => import("./features/projects/ProjectDetail"));
const AdminOverviewPage = lazyWithRetry(() => import("./features/admin/AdminOverviewPage"));
const UsersPage = lazyWithRetry(() => import("./features/admin/UsersPage"));
const RolesAdminPage = lazyWithRetry(() => import("./features/admin/RolesAdminPage"));
const ProjectGroupsAdminPage = lazyWithRetry(() => import("./features/admin/ProjectGroupsAdminPage"));
const HaushaltsImportPage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsImportPage"));
const HaushaltsReviewPage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsReviewPage"));
const HaushaltsUnmatchedPage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsUnmatchedPage"));
const HaushaltsGuidePage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsGuidePage"));
const FinveOverviewPage = lazyWithRetry(() => import("./features/finves/FinveOverviewPage"));
const VibImportPage = lazyWithRetry(() => import("./features/vib-import/VibImportPage"));
const VibReviewPage = lazyWithRetry(() => import("./features/vib-import/VibReviewPage"));
const VibStructurePreviewPage = lazyWithRetry(() => import("./features/vib-import/VibStructurePreviewPage"));
const BauportalImportPage = lazyWithRetry(() => import("./features/bauportal-import/BauportalImportPage"));
const MediaImportPage = lazyWithRetry(() => import("./features/media-import/MediaImportPage"));
const FuldaImportPage = lazyWithRetry(() => import("./features/fulda-import/FuldaImportPage"));
const FuldaYearDetailPage = lazyWithRetry(() => import("./features/fulda-import/FuldaYearDetailPage"));
const UnassignedPage = lazyWithRetry(() => import("./features/admin/UnassignedPage"));
const FinveProgressAdminPage = lazyWithRetry(() => import("./features/admin/FinveProgressAdminPage"));
const NewProjectPage = lazyWithRetry(() => import("./features/admin/new-project/NewProjectPage"));
const TasksPage = lazyWithRetry(() => import("./features/todos/TasksPage"));
const DraftsPage = lazyWithRetry(() => import("./features/admin/drafts/DraftsPage"));
const AnleitungenPage = lazyWithRetry(() => import("./features/guides/AnleitungenPage"));
const ProjektfortschrittGuidePage = lazyWithRetry(() => import("./features/guides/ProjektfortschrittGuidePage"));
const FuldaGuidePage = lazyWithRetry(() => import("./features/guides/FuldaGuidePage"));
const BauportalGuidePage = lazyWithRetry(() => import("./features/guides/BauportalGuidePage"));
const VibGuidePage = lazyWithRetry(() => import("./features/guides/VibGuidePage"));
const MedienGuidePage = lazyWithRetry(() => import("./features/guides/MedienGuidePage"));
const ProjektAnlegenGuidePage = lazyWithRetry(() => import("./features/guides/ProjektAnlegenGuidePage"));
const GeometrieGuidePage = lazyWithRetry(() => import("./features/guides/GeometrieGuidePage"));

function Layout() {
    return (
        <AppShell header={{ height: 60 }} padding="md">
            <AppShell.Header>
                <Header />
            </AppShell.Header>
            <AppShell.Main>
                <Outlet />
            </AppShell.Main>
        </AppShell>
    );
}

export const router = createBrowserRouter([
    {
        path: "/",
        element: <Layout />,
        errorElement: <RouteErrorBoundary />,
        children: [
            { index: true, element: <MapPage /> },
            { path: "documentation", element: <DocumentationPage /> },
            { path: "projects", element: <Navigate to="/?view=list" replace /> },
            {
                path: "projects/:projectId",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <ProjectDetail />
                    </Suspense>
                ),
            },
            {
                path: "tasks",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <TasksPage />
                    </Suspense>
                ),
            },
            {
                path: "admin",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <AdminOverviewPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/users",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <UsersPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/roles",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <RolesAdminPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/project-groups",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <ProjectGroupsAdminPage />
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
            {
                path: "admin/finve-progress",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <FinveProgressAdminPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/vib-import",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <VibImportPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/vib-import/review/:taskId",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <VibReviewPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/vib-import/preview/:taskId",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <VibStructurePreviewPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/bauportal-import",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <BauportalImportPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/media-import",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <MediaImportPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/fulda-import",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <FuldaImportPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/fulda-import/year/:year",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <FuldaYearDetailPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/unassigned",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <UnassignedPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/projects/new",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <NewProjectPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/projects/new/:projectId",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <NewProjectPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/drafts",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <DraftsPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <AnleitungenPage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen/projektfortschritt",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <ProjektfortschrittGuidePage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen/fulda",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <FuldaGuidePage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen/bauportal",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <BauportalGuidePage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen/vib",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <VibGuidePage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen/medien",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <MedienGuidePage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen/projekt-anlegen",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <ProjektAnlegenGuidePage />
                    </Suspense>
                ),
            },
            {
                path: "admin/anleitungen/geometrie",
                element: (
                    <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                        <GeometrieGuidePage />
                    </Suspense>
                ),
            },
        ]
    }
]);
