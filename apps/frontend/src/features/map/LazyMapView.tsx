import { Suspense, type ComponentProps } from "react";
import { Loader, Stack, Text } from "@mantine/core";

import { lazyWithRetry } from "../../lib/lazyWithRetry";
import type MapViewComponent from "./MapView";

export type { MapViewProject } from "./MapView";

// maplibre-gl is by far the largest dependency (~250 kB gzipped). Loading it
// through its own chunk keeps it out of the entry bundle, so the header, the
// list view and non-map pages render without waiting for it, and on the map
// page the download runs in parallel with the project-group request.
const MapView = lazyWithRetry(() => import("./MapView"));

type MapViewProps = ComponentProps<typeof MapViewComponent>;

export default function LazyMapView(props: MapViewProps) {
    const height = props.height ?? 800;
    return (
        <Suspense
            fallback={
                <Stack
                    align="center"
                    justify="center"
                    gap="xs"
                    style={{ height, background: "var(--bg2, #f2f2f2)" }}
                    role="status"
                >
                    <Loader />
                    <Text size="sm" c="dimmed">Karte wird geladen…</Text>
                </Stack>
            }
        >
            <MapView {...props} />
        </Suspense>
    );
}
