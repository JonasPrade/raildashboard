import { Suspense } from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { AppFrame } from "./components/AppFrame";
import RouteErrorBoundary from "./components/RouteErrorBoundary";
import { lazyWithRetry } from "./lib/lazyWithRetry";
import MapPage from "./features/map/MapPage";
import { LoadingState } from "./shared/ui/LoadingState";

const DocumentationPage = lazyWithRetry(() => import("./features/documentation/DocumentationPage"));
const LegalPage = lazyWithRetry(() => import("./features/legal/LegalPage"));
// Lazy like all other routes: ProjectDetail transitively pulls in recharts,
// react-markdown and terra-draw, which would otherwise land in the entry chunk.
const ProjectDetail = lazyWithRetry(() => import("./features/projects/ProjectDetail"));
const AdminOverviewPage = lazyWithRetry(() => import("./features/admin/AdminOverviewPage"));
const UsersPage = lazyWithRetry(() => import("./features/admin/UsersPage"));
const RolesAdminPage = lazyWithRetry(() => import("./features/admin/RolesAdminPage"));
const ApiKeysAdminPage = lazyWithRetry(() => import("./features/admin/ApiKeysAdminPage"));
const SystemStatusPage = lazyWithRetry(() => import("./features/admin/SystemStatusPage"));
const ProjectGroupsAdminPage = lazyWithRetry(() => import("./features/admin/ProjectGroupsAdminPage"));
const HaushaltsImportPage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsImportPage"));
const HaushaltsReviewPage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsReviewPage"));
const HaushaltsUnmatchedPage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsUnmatchedPage"));
const HaushaltsGuidePage = lazyWithRetry(() => import("./features/haushalt-import/HaushaltsGuidePage"));
const GvfgImportPage = lazyWithRetry(() => import("./features/gvfg-import/GvfgImportPage"));
const GvfgReviewPage = lazyWithRetry(() => import("./features/gvfg-import/GvfgReviewPage"));
const InfraplanImportPage = lazyWithRetry(() => import("./features/infraplan-import/InfraplanImportPage"));
const InfraplanReviewPage = lazyWithRetry(() => import("./features/infraplan-import/InfraplanReviewPage"));
const InfraplanKpiPage = lazyWithRetry(() => import("./features/infraplan-import/InfraplanKpiPage"));
const InfraplanPage = lazyWithRetry(() => import("./features/infraplan/InfraplanPage"));
const FinveOverviewPage = lazyWithRetry(() => import("./features/finves/FinveOverviewPage"));
const FinanzenLayout = lazyWithRetry(() => import("./features/finanzen/FinanzenLayout"));
const FinvesRedirect = lazyWithRetry(() => import("./features/finanzen/FinvesRedirect"));
const GvfgOverviewPage = lazyWithRetry(() => import("./features/gvfg/GvfgOverviewPage"));
const VibImportPage = lazyWithRetry(() => import("./features/vib-import/VibImportPage"));
const VibReviewPage = lazyWithRetry(() => import("./features/vib-import/VibReviewPage"));
const VibStructurePreviewPage = lazyWithRetry(() => import("./features/vib-import/VibStructurePreviewPage"));
const BauportalImportPage = lazyWithRetry(() => import("./features/bauportal-import/BauportalImportPage"));
const MediaImportPage = lazyWithRetry(() => import("./features/media-import/MediaImportPage"));
const FuldaImportPage = lazyWithRetry(() => import("./features/fulda-import/FuldaImportPage"));
const FuldaYearDetailPage = lazyWithRetry(() => import("./features/fulda-import/FuldaYearDetailPage"));
const UnassignedPage = lazyWithRetry(() => import("./features/admin/UnassignedPage"));
const FinveProgressAdminPage = lazyWithRetry(() => import("./features/admin/FinveProgressAdminPage"));
const ProgressConflictsAdminPage = lazyWithRetry(() => import("./features/admin/ProgressConflictsAdminPage"));
const NewProjectPage = lazyWithRetry(() => import("./features/admin/new-project/NewProjectPage"));
const TasksPage = lazyWithRetry(() => import("./features/todos/TasksPage"));
const AbgeordnetePage = lazyWithRetry(() => import("./features/abgeordnete/AbgeordnetePage"));
const ParliamentAdminPage = lazyWithRetry(() => import("./features/admin/ParliamentAdminPage"));
const DraftsPage =lazyWithRetry(() => import("./features/admin/drafts/DraftsPage"));
const AnleitungenPage = lazyWithRetry(() => import("./features/guides/AnleitungenPage"));
const ProjektfortschrittGuidePage = lazyWithRetry(() => import("./features/guides/ProjektfortschrittGuidePage"));
const FuldaGuidePage = lazyWithRetry(() => import("./features/guides/FuldaGuidePage"));
const BauportalGuidePage = lazyWithRetry(() => import("./features/guides/BauportalGuidePage"));
const VibGuidePage = lazyWithRetry(() => import("./features/guides/VibGuidePage"));
const MedienGuidePage = lazyWithRetry(() => import("./features/guides/MedienGuidePage"));
const ProjektAnlegenGuidePage = lazyWithRetry(() => import("./features/guides/ProjektAnlegenGuidePage"));
const GeometrieGuidePage = lazyWithRetry(() => import("./features/guides/GeometrieGuidePage"));
const InfraplanGuidePage = lazyWithRetry(() => import("./features/guides/InfraplanGuidePage"));

function Layout() {
    return (
        // Header, footer and page padding: components/AppFrame.tsx.
        <AppFrame>
            {/* One boundary for all lazy route chunks: the header stays
                visible while a page's chunk is loading. */}
            <Suspense fallback={<LoadingState rows={6} />}>
                <Outlet />
            </Suspense>
        </AppFrame>
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
            { path: "impressum", element: <LegalPage kind="impressum" /> },
            { path: "datenschutz", element: <LegalPage kind="datenschutz" /> },
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
                path: "admin/api-keys",
                element: <ApiKeysAdminPage />,
            },
            {
                path: "admin/system",
                element: <SystemStatusPage />,
            },
            {
                path: "admin/abgeordnete",
                element: <ParliamentAdminPage />,
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
                path: "admin/gvfg-import",
                element: <GvfgImportPage />,
            },
            {
                path: "admin/gvfg-import/review/:parseResultId",
                element: <GvfgReviewPage />,
            },
            {
                path: "admin/infraplan-import",
                element: <InfraplanImportPage />,
            },
            {
                path: "admin/infraplan-import/review/:parseResultId",
                element: <InfraplanReviewPage />,
            },
            {
                path: "admin/infraplan/kpis/:year",
                element: <InfraplanKpiPage />,
            },
            {
                path: "infraplan",
                element: <InfraplanPage />,
            },
            {
                path: "admin/haushalt-unmatched",
                element: <HaushaltsUnmatchedPage />,
            },
            {
                path: "finves",
                element: <FinvesRedirect />,
            },
            {
                path: "finanzen",
                element: <FinanzenLayout />,
                children: [
                    { path: "bedarfsplan", element: <FinveOverviewPage /> },
                    { path: "gvfg", element: <GvfgOverviewPage /> },
                ],
            },
            {
                path: "admin/finve-progress",
                element: <FinveProgressAdminPage />,
            },
            {
                path: "admin/planungsstand-konflikte",
                element: <ProgressConflictsAdminPage />,
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
            {
                path: "admin/anleitungen/infraplan",
                element: <InfraplanGuidePage />,
            },
        ]
    }
]);
