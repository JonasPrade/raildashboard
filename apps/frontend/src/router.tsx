import { Suspense } from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { AppShell, Loader, Group } from "@mantine/core";
import { Header } from "./components/Header";
import RouteErrorBoundary from "./components/RouteErrorBoundary";
import { lazyWithRetry } from "./lib/lazyWithRetry";
import MapPage from "./features/map/MapPage";

const DocumentationPage = lazyWithRetry(() => import("./features/documentation/DocumentationPage"));
// Lazy like all other routes: ProjectDetail transitively pulls in recharts,
// react-markdown and terra-draw, which would otherwise land in the entry chunk.
const ProjectDetail = lazyWithRetry(() => import("./features/projects/ProjectDetail"));
const AdminOverviewPage = lazyWithRetry(() => import("./features/admin/AdminOverviewPage"));
const UsersPage = lazyWithRetry(() => import("./features/admin/UsersPage"));
const RolesAdminPage = lazyWithRetry(() => import("./features/admin/RolesAdminPage"));
const SystemStatusPage = lazyWithRetry(() => import("./features/admin/SystemStatusPage"));
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
const AbgeordnetePage = lazyWithRetry(() => import("./features/abgeordnete/AbgeordnetePage"));
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
                {/* One boundary for all lazy route chunks: the header stays
                    visible while a page's chunk is loading. */}
                <Suspense fallback={<Group justify="center" py="xl"><Loader /></Group>}>
                    <Outlet />
                </Suspense>
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
                element: <ProjectDetail />,
            },
            {
                path: "abgeordnete",
                element: <AbgeordnetePage />,
            },
            {
                path: "tasks",
                element: <TasksPage />,
            },
            {
                path: "admin",
                element: <AdminOverviewPage />,
            },
            {
                path: "admin/users",
                element: <UsersPage />,
            },
            {
                path: "admin/roles",
                element: <RolesAdminPage />,
            },
            {
                path: "admin/system",
                element: <SystemStatusPage />,
            },
            {
                path: "admin/project-groups",
                element: <ProjectGroupsAdminPage />,
            },
            {
                path: "admin/haushalt-import",
                element: <HaushaltsImportPage />,
            },
            {
                path: "admin/haushalt-import/review/:parseResultId",
                element: <HaushaltsReviewPage />,
            },
            {
                path: "admin/haushalt-import/guide",
                element: <HaushaltsGuidePage />,
            },
            {
                path: "admin/haushalt-unmatched",
                element: <HaushaltsUnmatchedPage />,
            },
            {
                path: "finves",
                element: <FinveOverviewPage />,
            },
            {
                path: "admin/finve-progress",
                element: <FinveProgressAdminPage />,
            },
            {
                path: "admin/vib-import",
                element: <VibImportPage />,
            },
            {
                path: "admin/vib-import/review/:taskId",
                element: <VibReviewPage />,
            },
            {
                path: "admin/vib-import/preview/:taskId",
                element: <VibStructurePreviewPage />,
            },
            {
                path: "admin/bauportal-import",
                element: <BauportalImportPage />,
            },
            {
                path: "admin/media-import",
                element: <MediaImportPage />,
            },
            {
                path: "admin/fulda-import",
                element: <FuldaImportPage />,
            },
            {
                path: "admin/fulda-import/year/:year",
                element: <FuldaYearDetailPage />,
            },
            {
                path: "admin/unassigned",
                element: <UnassignedPage />,
            },
            {
                path: "admin/projects/new",
                element: <NewProjectPage />,
            },
            {
                path: "admin/projects/new/:projectId",
                element: <NewProjectPage />,
            },
            {
                path: "admin/drafts",
                element: <DraftsPage />,
            },
            {
                path: "admin/anleitungen",
                element: <AnleitungenPage />,
            },
            {
                path: "admin/anleitungen/projektfortschritt",
                element: <ProjektfortschrittGuidePage />,
            },
            {
                path: "admin/anleitungen/fulda",
                element: <FuldaGuidePage />,
            },
            {
                path: "admin/anleitungen/bauportal",
                element: <BauportalGuidePage />,
            },
            {
                path: "admin/anleitungen/vib",
                element: <VibGuidePage />,
            },
            {
                path: "admin/anleitungen/medien",
                element: <MedienGuidePage />,
            },
            {
                path: "admin/anleitungen/projekt-anlegen",
                element: <ProjektAnlegenGuidePage />,
            },
            {
                path: "admin/anleitungen/geometrie",
                element: <GeometrieGuidePage />,
            },
        ]
    }
]);
