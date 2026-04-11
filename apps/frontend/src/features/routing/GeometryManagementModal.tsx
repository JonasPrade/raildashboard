import { useState } from "react";
import {
    Alert,
    Badge,
    Box,
    Button,
    Divider,
    FileInput,
    Group,
    Modal,
    Paper,
    ScrollArea,
    Stack,
    Switch,
    Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import type { Project, RoutePreviewFeature } from "../../shared/api/queries";
import { useConfirmRoute, useUpdateProjectGeometry } from "../../shared/api/queries";
import GeometryPreviewMap from "./GeometryPreviewMap";
import RouteCalculatorForm from "./RouteCalculatorForm";

type Props = {
    project: Project;
    opened: boolean;
    onClose: () => void;
};

export default function GeometryManagementModal({ project, opened, onClose }: Props) {
    const projectId = project.id as number;

    const [deleteExisting, setDeleteExisting] = useState(false);
    const [previewFeature, setPreviewFeature] = useState<RoutePreviewFeature | null>(null);
    const [uploadedGeojson, setUploadedGeojson] = useState<string | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [routeError, setRouteError] = useState<string | null>(null);

    const hasExisting = !!project.geojson_representation;

    // Active new geometry: route preview takes precedence over upload
    const activeNewGeojson: string | null =
        previewFeature
            ? JSON.stringify(previewFeature)
            : uploadedGeojson;

    const confirmRoute = useConfirmRoute(projectId);
    const updateGeometry = useUpdateProjectGeometry(projectId);

    const isPending = confirmRoute.isPending || updateGeometry.isPending;

    function resetState() {
        setDeleteExisting(false);
        setPreviewFeature(null);
        setUploadedGeojson(null);
        setUploadError(null);
        setRouteError(null);
    }

    function handleClose() {
        resetState();
        onClose();
    }

    async function handleAccept() {
        if (!activeNewGeojson && !deleteExisting) {
            // Nothing to do
            handleClose();
            return;
        }

        try {
            if (previewFeature) {
                // 1. Confirm route in DB
                await confirmRoute.mutateAsync(previewFeature);
                // 2. Update project geometry to the route's LineString
                await updateGeometry.mutateAsync(JSON.stringify(previewFeature.geometry));
            } else if (uploadedGeojson) {
                await updateGeometry.mutateAsync(uploadedGeojson);
            } else if (deleteExisting) {
                await updateGeometry.mutateAsync(null);
            }

            notifications.show({
                color: "green",
                title: "Geometrie aktualisiert",
                message: "Die Projektgeometrie wurde erfolgreich gespeichert.",
            });
            handleClose();
        } catch {
            notifications.show({
                color: "red",
                title: "Fehler",
                message: "Die Geometrie konnte nicht gespeichert werden.",
            });
        }
    }

    function handleFileUpload(file: File | null) {
        setUploadError(null);
        setUploadedGeojson(null);
        setPreviewFeature(null);

        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target?.result as string;
            try {
                const parsed = JSON.parse(text);
                // Basic validation: must be a GeoJSON object
                if (!parsed || typeof parsed !== "object" || !parsed.type) {
                    setUploadError("Ungültiges GeoJSON-Format.");
                    return;
                }
                setUploadedGeojson(text);
            } catch {
                setUploadError("Die Datei konnte nicht als GeoJSON gelesen werden.");
            }
        };
        reader.readAsText(file);
    }

    const canAccept = activeNewGeojson !== null || deleteExisting;

    return (
        <Modal
            opened={opened}
            onClose={handleClose}
            fullScreen
            title="Geometrie verwalten"
            styles={{ body: { padding: 0, height: "calc(100% - 60px)", display: "flex" } }}
        >
            <Group align="stretch" gap={0} style={{ width: "100%", height: "100%" }}>
                {/* ── Left panel: controls ────────────────────────────────── */}
                <Box
                    style={{
                        width: 380,
                        minWidth: 320,
                        borderRight: "1px solid var(--mantine-color-default-border)",
                        display: "flex",
                        flexDirection: "column",
                    }}
                >
                    <ScrollArea style={{ flex: 1 }} p="md">
                        <Stack gap="md">
                            {/* Current status */}
                            <div>
                                <Text size="xs" fw={600} c="dimmed" tt="uppercase" mb={6}>
                                    Aktuelle Geometrie
                                </Text>
                                <Badge
                                    color={hasExisting ? "green" : "gray"}
                                    variant="light"
                                >
                                    {hasExisting ? "Geometrie vorhanden" : "Keine Geometrie"}
                                </Badge>
                            </div>

                            {hasExisting && (
                                <Switch
                                    label="Bestehende Geometrie löschen"
                                    checked={deleteExisting}
                                    onChange={(e) => setDeleteExisting(e.currentTarget.checked)}
                                    color="red"
                                />
                            )}

                            <Divider label="Route berechnen" labelPosition="left" />

                            {routeError && (
                                <Alert color="red" variant="light" onClose={() => setRouteError(null)} withCloseButton>
                                    {routeError}
                                </Alert>
                            )}

                            <RouteCalculatorForm
                                onResult={(feature) => {
                                    setRouteError(null);
                                    setUploadedGeojson(null);
                                    setPreviewFeature(feature);
                                }}
                                onError={setRouteError}
                            />

                            <Divider label="Oder: GeoJSON hochladen" labelPosition="left" />

                            {uploadError && (
                                <Alert color="red" variant="light" onClose={() => setUploadError(null)} withCloseButton>
                                    {uploadError}
                                </Alert>
                            )}

                            <FileInput
                                label="GeoJSON-Datei"
                                placeholder="Datei auswählen…"
                                accept=".geojson,.json"
                                onChange={handleFileUpload}
                            />

                            {/* Preview info */}
                            {previewFeature && (
                                <Paper withBorder p="sm" radius="md">
                                    <Stack gap={4}>
                                        <Text size="sm" fw={600}>Berechnete Route</Text>
                                        <Text size="sm" c="dimmed">
                                            Distanz: {(previewFeature.properties.distance_m / 1000).toFixed(1)} km
                                        </Text>
                                        <Text size="sm" c="dimmed">
                                            Dauer: {Math.round(previewFeature.properties.duration_ms / 60_000)} min
                                        </Text>
                                    </Stack>
                                </Paper>
                            )}

                            {uploadedGeojson && !previewFeature && (
                                <Paper withBorder p="sm" radius="md">
                                    <Text size="sm" fw={600} c="green">GeoJSON geladen — bitte prüfen</Text>
                                </Paper>
                            )}
                        </Stack>
                    </ScrollArea>

                    {/* Footer buttons */}
                    <Box p="md" style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}>
                        <Stack gap="xs">
                            <Button
                                onClick={handleAccept}
                                loading={isPending}
                                disabled={!canAccept}
                                color={deleteExisting && !activeNewGeojson ? "red" : undefined}
                            >
                                {deleteExisting && !activeNewGeojson
                                    ? "Geometrie löschen"
                                    : "Übernehmen"}
                            </Button>
                            <Button variant="default" onClick={handleClose} disabled={isPending}>
                                Abbrechen
                            </Button>
                        </Stack>
                    </Box>
                </Box>

                {/* ── Right panel: map ────────────────────────────────────── */}
                <Box style={{ flex: 1, position: "relative" }}>
                    <GeometryPreviewMap
                        existingGeojson={project.geojson_representation ?? null}
                        previewFeature={previewFeature ?? (uploadedGeojson ? buildUploadPreview(uploadedGeojson) : null)}
                        showExisting={!deleteExisting}
                        height={undefined}
                    />
                </Box>
            </Group>
        </Modal>
    );
}

/**
 * Wrap an uploaded GeoJSON string into a minimal RoutePreviewFeature-like object
 * so the map can display it as a preview (dashed orange). Only used for display.
 */
function buildUploadPreview(geojsonStr: string): RoutePreviewFeature | null {
    try {
        const parsed = JSON.parse(geojsonStr);
        // Normalise to a LineString geometry for preview rendering
        let coords: number[][] | null = null;
        if (parsed.type === "LineString") {
            coords = parsed.coordinates;
        } else if (parsed.type === "Feature" && parsed.geometry?.type === "LineString") {
            coords = parsed.geometry.coordinates;
        } else if (parsed.type === "FeatureCollection") {
            for (const f of parsed.features ?? []) {
                if (f.geometry?.type === "LineString") {
                    coords = f.geometry.coordinates;
                    break;
                }
            }
        }
        if (!coords) return null;
        return {
            type: "Feature",
            geometry: { type: "LineString", coordinates: coords },
            properties: {
                distance_m: 0,
                duration_ms: 0,
                profile: "upload",
                graph_version: "",
                bbox: [],
                details: {},
                cache_key: "",
            },
        };
    } catch {
        return null;
    }
}
