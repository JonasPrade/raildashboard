import { createBrowserRouter, Outlet } from "react-router-dom";
import { AppShell } from "@mantine/core";
import { Header } from "./components/Header";
import MapPage from "./features/map/MapPage";
import DocumentationPage from "./features/documentation/DocumentationPage";
import ProjectGroupsPage from "./features/projects/ProjectGroupsPage";

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
            { path: "projects", element: <ProjectGroupsPage /> }
        ]
    }
]);
