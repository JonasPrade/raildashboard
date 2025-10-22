import { createBrowserRouter } from "react-router-dom";
import { AppShell, Container } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {Header} from "./components/Header";
import GroupFilterDrawer from "./features/projects/GroupFilterDrawer";
import MapView from "./features/map/MapView";
import MapControls from "./features/map/MapControls";

function Layout() {
    const [opened, { open, close }] = useDisclosure(false);
    return (
        <>
            <AppShell header={{ height: 52 }}>
                <AppShell.Header><Header/></AppShell.Header>
                <AppShell.Main style={{ position: "relative", height: "100vh", width: "100%" }}>
                    <Container size="xl" style={{ height: "100%", position: "relative" }}>
                        <MapView />
                        <MapControls onOpenFilters={open} />
                    </Container>
                </AppShell.Main>
            </AppShell>
            <GroupFilterDrawer opened={opened} onClose={close} />
        </>
    );
}

export const router = createBrowserRouter([{ path: "/", element: <Layout /> }]);