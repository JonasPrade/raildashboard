import { Container } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import GroupFilterDrawer from "../projects/GroupFilterDrawer";
import MapControls from "./MapControls";
import MapView from "./MapView";

export default function MapPage() {
    const [opened, { open, close }] = useDisclosure(false);

    return (
        <>
            <Container size="xl" style={{ height: "100%", position: "relative" }}>
                <MapView />
                <MapControls onOpenFilters={open} />
            </Container>
            <GroupFilterDrawer opened={opened} onClose={close} />
        </>
    );
}
