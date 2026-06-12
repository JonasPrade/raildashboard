import { useState } from "react";
import {
    ActionIcon,
    Alert,
    Box,
    Button,
    Divider,
    FileInput,
    Group,
    Modal,
    ScrollArea,
    Stack,
    Switch,
    Text,
} from "@mantine/core";
import { ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
import { notifications } from "@mantine/notifications";

import type { OperationalPointRef, Project, RoutePreviewFeature } from "../../shared/api/queries";
import { useConfirmRoute, useUpdateProjectGeometry } from "../../shared/api/queries";
import GeometryPreviewMap from "./GeometryPreviewMap";
import RouteCalculatorForm from "./RouteCalculatorForm";
import StationSelect from "./StationSelect";

type Props = {
    project: Project;
    opened: boolean;
    onClose: () => void;
};

export default function GeometryManagementModal({ project, opened, onClose }: Props) {
    const projectId = project.id as number;

    const [deleteExisting, setDeleteExisting] = useState(false);
    const [previewFeature, setPreviewFeature] = useState<RoutePreviewFeature | null>(null);
    const [routeStations, setRouteStations] = useState<OperationalPointRef[]>([]);
    const [uploadedGeojson, setUploadedGeojson] = useState<string | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [routeError, setRouteError] = useState<string | null>(null);
    const [selectedPoints, setSelectedPoints] = useState<OperationalPointRef[]>([]);
    const [pointSelectKey, setPointSelectKey] = useState(0);
    // Selective feature deletion: when active, clicks on the map select existing features.
    const [selectionMode, setSelectionMode] = useState(false);
    const [selectedFeatureIndices, setSelectedFeatureIndices] = useState<Set<number>>(new Set());

    const hasExisting = !!project.geojson_representation;
    const hasPoints = selectedPoints.length > 0;

    const confirmRoute = useConfirmRoute(projectId);
    const updateGeometry = useUpdateProjectGeometry(projectId);

    const isPending = confirmRoute.isPending || updateGeometry.isPending;

    function resetState() {
        setDeleteExisting(false);
        setPreviewFeature(null);
        setRouteStations([]);
        setUploadedGeojson(null);
        setUploadError(null);
        setRouteError(null);
        setSelectedPoints([]);
        setPointSelectKey(0);
        setSelectionMode(false);
        setSelectedFeatureIndices(new Set());
    }

    function toggleFeatureSelection(idx: number) {
        setSelectedFeatureIndices((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx); else next.add(idx);
            return next;
        });
    }

    async function handleDeleteSelectedFeatures() {
        if (!project.geojson_representation || selectedFeatureIndices.size === 0) return;

        let parsed: unknown;
        try { parsed = JSON.parse(project.geojson_representation); } catch { return; }

        // Normalize to a flat list of features so we can filter by their original index.
        const root = parsed as Record<string, unknown> | null;
        let features: unknown[] = [];
        if (root && root.type === "FeatureCollection" && Array.isArray(root.features)) {
            features = root.features as unknown[];
        } else if (root && root.type === "Feature") {
            features = [root];
        } else if (root && typeof root.type === "string") {
            features = [{ type: "Feature", geometry: root, properties: {} }];
        }

        const remaining = features.filter((_, idx) => !selectedFeatureIndices.has(idx));
        const newGeojson = remaining.length > 0
            ? JSON.stringify({ type: "FeatureCollection", features: remaining })
            : null;

        try {
            await updateGeometry.mutateAsync(newGeojson);
            notifications.show({
                color: "green",
                title: "Features gelöscht",
                message: `${selectedFeatureIndices.size} Feature(s) entfernt.`,
            });
            handleClose();
        } catch {
            notifications.show({
                color: "red",
                title: "Fehler",
                message: "Die ausgewählten Features konnten nicht gelöscht werden.",
            });
        }
    }

    function handleClose() {
        resetState();
        onClose();
    }

    function buildNewGeometry(): string | null {
        // Upload-only (no route, no points): return as-is
        if (!previewFeature && !hasPoints && !routeStations.length && uploadedGeojson) {
            return uploadedGeojson;
        }

        const features: object[] = [];

        if (previewFeature) {
            features.push({ type: "Feature", geometry: previewFeature.geometry, properties: {} });
        } else if (uploadedGeojson) {
            try {
                const p = JSON.parse(uploadedGeojson);
                if (p.type === "FeatureCollection") features.push(...(p.features ?? []));
                else if (p.type === "Feature") features.push(p);
                else features.push({ type: "Feature", geometry: p, properties: {} });
            } catch { /* ignore */ }
        }

        // Merge route start/via/end stations + manually-added points, dedup by id.
        // Route stations are only included when the route is actually about to be saved
        // (i.e. previewFeature is non-null).
        const pointsToInclude: OperationalPointRef[] = [];
        const seen = new Set<number>();
        const pushOnce = (op: OperationalPointRef) => {
            if (!seen.has(op.id) && op.latitude != null && op.longitude != null) {
                seen.add(op.id);
                pointsToInclude.push(op);
            }
        };
        if (previewFeature) routeStations.forEach(pushOnce);
        selectedPoints.forEach(pushOnce);

        for (const op of pointsToInclude) {
            features.push({
                type: "Feature",
                geometry: { type: "Point", coordinates: [op.longitude, op.latitude] },
                properties: { name: op.name ?? null, op_id: op.op_id ?? null, feature_type: "operational_point" },
            });
        }

        return features.length > 0
            ? JSON.stringify({ type: "FeatureCollection", features })
            : null;
    }

    async function handleAccept() {
        const hasNewGeometry = !!previewFeature || !!uploadedGeojson || hasPoints;

        if (!hasNewGeometry && !deleteExisting) {
            handleClose();
            return;
        }

        try {
            if (previewFeature) {
                await confirmRoute.mutateAsync(previewFeature);
            }

            if (hasNewGeometry && (!hasExisting || deleteExisting)) {
                await updateGeometry.mutateAsync(buildNewGeometry());
            } else if (hasNewGeometry && hasExisting && !deleteExisting && !previewFeature && !hasPoints) {
                // Upload-only with existing geometry and no toggle: apply anyway (legacy behaviour)
                await updateGeometry.mutateAsync(uploadedGeojson);
            } else if (!hasNewGeometry && deleteExisting) {
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

    // In selectionMode, the "Übernehmen" button is suppressed — users delete features via
    // the dedicated "Auswahl löschen" button instead.
    const canAccept = !selectionMode && (!!previewFeature || !!uploadedGeojson || hasPoints || deleteExisting);

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
                                <ChronicleDataChip>
                                    {hasExisting ? "Geometrie vorhanden" : "Keine Geometrie"}
                                </ChronicleDataChip>
                            </div>

                            {hasExisting && (
                                <Switch
                                    label="Bestehende Geometrie löschen"
                                    checked={deleteExisting}
                                    onChange={(e) => setDeleteExisting(e.currentTarget.checked)}
                                    color="red"
                                    disabled={selectionMode}
                                />
                            )}

                            {hasExisting && (
                                <>
                                    <Switch
                                        label="Einzelne Features auswählen & löschen"
                                        checked={selectionMode}
                                        onChange={(e) => {
                                            setSelectionMode(e.currentTarget.checked);
                                            if (!e.currentTarget.checked) setSelectedFeatureIndices(new Set());
                                        }}
                                        color="red"
                                        disabled={deleteExisting}
                                    />
                                    {selectionMode && (
                                        <Stack gap="xs">
                                            <Text size="xs" c="dimmed">
                                                Klicke auf der Karte einzelne Linien oder Punkte, um sie auszuwählen.
                                                Ausgewählte Features erscheinen rot.
                                            </Text>
                                            <Group justify="space-between" align="center">
                                                <ChronicleDataChip>
                                                    {selectedFeatureIndices.size} ausgewählt
                                                </ChronicleDataChip>
                                                {selectedFeatureIndices.size > 0 && (
                                                    <Button
                                                        size="xs"
                                                        variant="subtle"
                                                        onClick={() => setSelectedFeatureIndices(new Set())}
                                                    >
                                                        Zurücksetzen
                                                    </Button>
                                                )}
                                            </Group>
                                            <Button
                                                color="red"
                                                size="sm"
                                                disabled={selectedFeatureIndices.size === 0 || updateGeometry.isPending}
                                                loading={updateGeometry.isPending}
                                                onClick={handleDeleteSelectedFeatures}
                                            >
                                                Auswahl löschen ({selectedFeatureIndices.size})
                                            </Button>
                                        </Stack>
                                    )}
                                </>
                            )}

                            <Divider label="Route berechnen" labelPosition="left" />

                            {routeError && (
                                <Alert color="red" variant="light" onClose={() => setRouteError(null)} withCloseButton>
                                    {routeError}
                                </Alert>
                            )}

                            <RouteCalculatorForm
                                onResult={(feature, stations) => {
                                    setRouteError(null);
                                    setUploadedGeojson(null);
                                    setPreviewFeature(feature);
                                    setRouteStations(stations);
                                }}
                                onError={setRouteError}
                            />

                            <Divider label="Betriebsstellen hinzufügen" labelPosition="left" />

                            <StationSelect
                                key={pointSelectKey}
                                label="Betriebsstelle suchen"
                                value={null}
                                onChange={(op) => {
                                    if (op && !selectedPoints.some((p) => p.id === op.id)) {
                                        setSelectedPoints((prev) => [...prev, op]);
                                    }
                                    setPointSelectKey((k) => k + 1);
                                }}
                            />

                            {selectedPoints.map((op) => (
                                <Group key={op.id} justify="space-between" align="center" gap="xs">
                                    <div>
                                        <Text size="sm" fw={500}>● {op.name ?? op.op_id}</Text>
                                        {op.op_id && op.name && (
                                            <Text size="xs" c="dimmed">{op.op_id}</Text>
                                        )}
                                    </div>
                                    <ActionIcon
                                        variant="subtle"
                                        color="red"
                                        size="sm"
                                        onClick={() => setSelectedPoints((prev) => prev.filter((p) => p.id !== op.id))}
                                        aria-label="Entfernen"
                                    >
                                        ×
                                    </ActionIcon>
                                </Group>
                            ))}

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
                                <ChronicleCard>
                                    <Stack gap={4}>
                                        <Text size="sm" fw={600}>Berechnete Route</Text>
                                        <Text size="sm" c="dimmed">
                                            Distanz: {(previewFeature.properties.distance_m / 1000).toFixed(1)} km
                                        </Text>
                                        <Text size="sm" c="dimmed">
                                            Dauer: {Math.round(previewFeature.properties.duration_ms / 60_000)} min
                                        </Text>
                                    </Stack>
                                </ChronicleCard>
                            )}

                            {uploadedGeojson && !previewFeature && (
                                <ChronicleCard>
                                    <Text size="sm" fw={600} c="green">GeoJSON geladen — bitte prüfen</Text>
                                </ChronicleCard>
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
                                color={deleteExisting && !previewFeature && !uploadedGeojson && !hasPoints ? "red" : undefined}
                            >
                                {deleteExisting && !previewFeature && !uploadedGeojson && !hasPoints
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
                        previewPoints={selectedPoints}
                        selectionMode={selectionMode}
                        selectedIndices={selectedFeatureIndices}
                        onFeatureClick={toggleFeatureSelection}
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
