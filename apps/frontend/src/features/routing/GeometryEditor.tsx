import { useState } from "react";
import {
    ActionIcon,
    Alert,
    Box,
    Button,
    Divider,
    FileInput,
    Group,
    ScrollArea,
    Stack,
    Switch,
    Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
import type { OperationalPointRef, Project, RoutePreviewFeature } from "../../shared/api/queries";
import { useConfirmRoute, useUpdateProjectGeometry } from "../../shared/api/queries";
import GeometryPreviewMap from "./GeometryPreviewMap";
import RouteCalculatorForm from "./RouteCalculatorForm";
import StationSelect from "./StationSelect";

type Props = {
    /** Project whose geometry is being edited. Existing geometry is read from `geojson_representation`. */
    project: Project;
    /** Called after a successful save, with the updated project (the wizard uses it to refresh its state). */
    onSaved: (updatedProject: Project) => void;
    /** Called when the user cancels / skips. */
    onCancel: () => void;
    /** Label for the primary save button (default "Übernehmen"). */
    saveLabel?: string;
    /** Label for the secondary cancel/skip button (default "Abbrechen"). */
    cancelLabel?: string;
    /**
     * Whether to render the secondary cancel/skip button (default true).
     * The creation wizard hides it because navigation is handled by the wizard footer;
     * the editor then stays open after saving so further geometry can be added.
     */
    showCancel?: boolean;
    /**
     * Height of the editor container. The map fills the right panel.
     * The modal uses "100%" (fills the fullscreen body), the wizard a fixed px value.
     */
    height?: number | string;
};

/**
 * Shared geometry editor: a left control panel (route calculation, operational-point
 * selection, GeoJSON upload, optional delete controls) and a right MapLibre preview
 * that always shows existing + new geometry. Used both when creating a project (wizard
 * step) and when editing an existing project's geometry (fullscreen modal).
 */
export default function GeometryEditor({
    project,
    onSaved,
    onCancel,
    saveLabel = "Übernehmen",
    cancelLabel = "Abbrechen",
    showCancel = true,
    height = "100%",
}: Props) {
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

    /**
     * Clear all transient inputs after a save. The editor stays mounted (the wizard keeps
     * it open so users can add further geometry), and the just-saved geometry becomes the
     * new "existing" geometry once the parent passes the updated project back in.
     */
    function resetInputs() {
        setDeleteExisting(false);
        setPreviewFeature(null);
        setRouteStations([]);
        setUploadedGeojson(null);
        setUploadError(null);
        setRouteError(null);
        setSelectedPoints([]);
        setPointSelectKey((k) => k + 1);
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
            const updated = await updateGeometry.mutateAsync(newGeojson);
            notifications.show({
                color: "green",
                title: "Features gelöscht",
                message: `${selectedFeatureIndices.size} Feature(s) entfernt.`,
            });
            resetInputs();
            onSaved(updated);
        } catch {
            notifications.show({
                color: "red",
                title: "Fehler",
                message: "Die ausgewählten Features konnten nicht gelöscht werden.",
            });
        }
    }

    /**
     * Build the geometry to persist as a flat FeatureCollection.
     *
     * `keepExisting` controls the core mental model of the editor:
     *   - false → replace (used when there is no existing geometry, or the user toggled
     *     "Bestehende Geometrie löschen"): only the newly added features are written.
     *   - true  → merge (the default when existing geometry is present): the new features
     *     (route line, uploaded GeoJSON, route stations + manually picked operational
     *     points) are appended to the existing ones, so nothing is silently dropped.
     */
    function buildFinalGeometry(keepExisting: boolean): string | null {
        const features: object[] = [];

        if (keepExisting && project.geojson_representation) {
            features.push(...parseFeatures(project.geojson_representation));
        }

        if (previewFeature) {
            features.push({ type: "Feature", geometry: previewFeature.geometry, properties: {} });
        } else if (uploadedGeojson) {
            features.push(...parseFeatures(uploadedGeojson));
        }

        // Merge route start/via/end stations + manually-added points, dedup by id.
        // Route stations are only included when the route is actually about to be saved
        // (i.e. previewFeature is non-null).
        const seen = new Set<number>();
        const pushOnce = (op: OperationalPointRef) => {
            if (!seen.has(op.id) && op.latitude != null && op.longitude != null) {
                seen.add(op.id);
                features.push({
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [op.longitude, op.latitude] },
                    properties: { name: op.name ?? null, op_id: op.op_id ?? null, feature_type: "operational_point" },
                });
            }
        };
        if (previewFeature) routeStations.forEach(pushOnce);
        selectedPoints.forEach(pushOnce);

        return features.length > 0
            ? JSON.stringify({ type: "FeatureCollection", features })
            : null;
    }

    async function handleAccept() {
        const hasNewGeometry = !!previewFeature || !!uploadedGeojson || hasPoints;

        if (!hasNewGeometry && !deleteExisting) {
            onCancel();
            return;
        }

        try {
            if (previewFeature) {
                await confirmRoute.mutateAsync(previewFeature);
            }

            let updated: Project | null = null;
            if (hasNewGeometry) {
                // Merge into existing unless the user explicitly chose to replace it
                // (deleteExisting), or there is nothing to keep.
                const keepExisting = hasExisting && !deleteExisting;
                updated = await updateGeometry.mutateAsync(buildFinalGeometry(keepExisting));
            } else if (deleteExisting) {
                updated = await updateGeometry.mutateAsync(null);
            }

            notifications.show({
                color: "green",
                title: "Geometrie aktualisiert",
                message: "Die Projektgeometrie wurde erfolgreich gespeichert.",
            });
            resetInputs();
            onSaved(updated ?? project);
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

    // In selectionMode, the primary save button is suppressed — users delete features via
    // the dedicated "Auswahl löschen" button instead.
    const canAccept = !selectionMode && (!!previewFeature || !!uploadedGeojson || hasPoints || deleteExisting);
    const isDeleteOnly = deleteExisting && !previewFeature && !uploadedGeojson && !hasPoints;

    return (
        <Group align="stretch" gap={0} wrap="nowrap" style={{ width: "100%", height }}>
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
                            color={isDeleteOnly ? "red" : undefined}
                        >
                            {isDeleteOnly ? "Geometrie löschen" : saveLabel}
                        </Button>
                        {showCancel && (
                            <Button variant="default" onClick={onCancel} disabled={isPending}>
                                {cancelLabel}
                            </Button>
                        )}
                    </Stack>
                </Box>
            </Box>

            {/* ── Right panel: map ────────────────────────────────────── */}
            <Box style={{ flex: 1, position: "relative", minWidth: 0 }}>
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
    );
}

/**
 * Parse a GeoJSON string into a flat list of Features. Accepts a FeatureCollection,
 * a bare Feature, or a bare Geometry (wrapped into a Feature). Returns [] on parse error.
 */
function parseFeatures(raw: string): object[] {
    try {
        const p = JSON.parse(raw);
        if (p && p.type === "FeatureCollection") return (p.features ?? []) as object[];
        if (p && p.type === "Feature") return [p];
        if (p && typeof p.type === "string") return [{ type: "Feature", geometry: p, properties: {} }];
    } catch { /* ignore */ }
    return [];
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
