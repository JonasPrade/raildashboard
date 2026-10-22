import { useMemo, useState } from "react";
import {
    ActionIcon,
    Alert,
    Badge,
    Box,
    Button,
    Divider,
    FileInput,
    Group,
    Paper,
    ScrollArea,
    Stack,
    Switch,
    Text,
} from "@mantine/core";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { openConfirmModal } from "../../shared/ui/confirmModal";
import { notifications } from "@mantine/notifications";

import type { OperationalPointRef, Project, RoutePreviewFeature } from "../../shared/api/queries";
import {
    useConfirmRoute,
    useUpdateProjectGeojsonSource,
    useUpdateProjectGeometry,
} from "../../shared/api/queries";
import { computeGeojsonLengthKm } from "../../shared/geo/length";
import GeometryPreviewMap, { type DrawMode } from "./GeometryPreviewMap";
import { applyEditedParts, explodeEditable, parseFeatureList, type EditablePart } from "./editExisting";
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
    /**
     * Number of subprojects. Above 0 the project is a superior project and may choose
     * between its own geometry and one aggregated from its subprojects; the wizard
     * (where a project cannot have subprojects yet) leaves this at 0.
     */
    subProjectCount?: number;
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
    subProjectCount = 0,
}: Props) {
    const isMobile = useIsMobile();
    const projectId = project.id as number;

    const [deleteExisting, setDeleteExisting] = useState(false);
    const [previewFeature, setPreviewFeature] = useState<RoutePreviewFeature | null>(null);
    const [routeStations, setRouteStations] = useState<OperationalPointRef[]>([]);
    // Route waypoints only steer the routing; they become points only on explicit request.
    const [addRouteStations, setAddRouteStations] = useState(false);
    const [uploadedGeojson, setUploadedGeojson] = useState<string | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [routeError, setRouteError] = useState<string | null>(null);
    const [selectedPoints, setSelectedPoints] = useState<OperationalPointRef[]>([]);
    const [pointSelectKey, setPointSelectKey] = useState(0);
    // Selective feature deletion: when active, clicks on the map select existing features.
    const [selectionMode, setSelectionMode] = useState(false);
    const [selectedFeatureIndices, setSelectedFeatureIndices] = useState<Set<number>>(new Set());
    // Hand drawing: terra-draw owns the live geometry; we mirror its snapshot here.
    const [drawMode, setDrawMode] = useState<DrawMode>(null);
    const [drawnFeatures, setDrawnFeatures] = useState<GeoJSON.Feature[]>([]);
    // In-place editing of the saved geometry: `editableParts` is the snapshot loaded into
    // terra-draw (null = off), `editedParts` mirrors terra-draw's current state of it.
    const [editableParts, setEditableParts] = useState<EditablePart[] | null>(null);
    const [editedParts, setEditedParts] = useState<EditablePart[]>([]);

    const hasExisting = !!project.geojson_representation;
    const hasPoints = selectedPoints.length > 0;
    const hasDrawn = drawnFeatures.length > 0;
    const editExisting = editableParts !== null;
    const editedExisting = useMemo(
        () => editableParts
            ? applyEditedParts(parseFeatureList(project.geojson_representation), editableParts, editedParts)
            : null,
        [project.geojson_representation, editableParts, editedParts],
    );
    const hasEditedExisting = !!editedExisting?.changed;
    const drawnLengthKm = computeGeojsonLengthKm(
        hasDrawn ? JSON.stringify({ type: "FeatureCollection", features: drawnFeatures }) : null,
    );

    // A superior project either owns its geometry or has it aggregated from its
    // subprojects. While aggregated, editing is pointless — the next change anywhere in
    // the subtree would overwrite it — so the editor shows the toggle and nothing else.
    const isSuperiorProject = subProjectCount > 0;
    const isAggregated = isSuperiorProject && project.geojson_from_subprojects;

    const confirmRoute = useConfirmRoute(projectId);
    const updateGeometry = useUpdateProjectGeometry(projectId);
    const updateGeojsonSource = useUpdateProjectGeojsonSource(projectId);

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
        setAddRouteStations(false);
        setUploadedGeojson(null);
        setUploadError(null);
        setRouteError(null);
        setSelectedPoints([]);
        setPointSelectKey((k) => k + 1);
        setSelectionMode(false);
        setSelectedFeatureIndices(new Set());
        setDrawMode(null);
        setDrawnFeatures([]);
        setEditableParts(null);
        setEditedParts([]);
    }

    /** Load the saved lines/points into the map for vertex editing, or discard the edits. */
    function toggleEditExisting(on: boolean) {
        if (on) {
            const parts = explodeEditable(parseFeatureList(project.geojson_representation));
            setEditableParts(parts);
            setEditedParts(parts);
            setDrawMode("select");
        } else {
            setEditableParts(null);
            setEditedParts([]);
            setDrawMode(null);
        }
    }

    /** Persist the geometry source. Switching back to aggregated replaces the project's
     *  own geometry with the union of its subprojects — hence the confirmation. */
    function applyGeojsonSource(fromSubprojects: boolean) {
        updateGeojsonSource.mutate(fromSubprojects, {
            onSuccess: () => {
                resetInputs();
                notifications.show({
                    color: "green",
                    title: "Geometrie-Quelle geändert",
                    message: fromSubprojects
                        ? "Die Geometrie wird jetzt aus den Unterprojekten zusammengesetzt."
                        : "Die Geometrie dieses Projekts kann jetzt selbst gepflegt werden.",
                });
            },
            onError: () => {
                notifications.show({
                    color: "red",
                    title: "Fehler",
                    message: "Die Geometrie-Quelle konnte nicht geändert werden.",
                });
            },
        });
    }

    function handleGeojsonSourceChange(fromSubprojects: boolean) {
        if (!fromSubprojects) {
            applyGeojsonSource(false);
            return;
        }
        openConfirmModal({
            title: "Geometrie aus Unterprojekten zusammensetzen?",
            children: (
                <Text size="sm">
                    Die eigene Geometrie dieses Projekts wird durch die Geometrien seiner
                    Unterprojekte ersetzt und ab sofort bei jeder Änderung dort automatisch neu
                    berechnet.
                </Text>
            ),
            labels: { confirm: "Zusammensetzen", cancel: "Abbrechen" },
            onConfirm: () => applyGeojsonSource(true),
        });
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
     *     (route line, uploaded GeoJSON, manually picked operational points and — only
     *     when opted in — the route stations) are appended to the existing ones, so nothing is silently dropped.
     */
    function buildFinalGeometry(keepExisting: boolean): string | null {
        const features: object[] = [];

        if (keepExisting && editedExisting) {
            // Saved geometry with the in-place vertex edits applied.
            features.push(...editedExisting.features);
        } else if (keepExisting && project.geojson_representation) {
            features.push(...parseFeatures(project.geojson_representation));
        }

        if (previewFeature) {
            features.push({ type: "Feature", geometry: previewFeature.geometry, properties: {} });
        } else if (uploadedGeojson) {
            features.push(...parseFeatures(uploadedGeojson));
        }

        // Merge manually-added points and — only when explicitly requested — the route's
        // start/via/end stations, dedup by id. Route stations additionally require the
        // route to actually be saved (i.e. previewFeature is non-null).
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
        if (previewFeature && addRouteStations) routeStations.forEach(pushOnce);
        selectedPoints.forEach(pushOnce);

        // Hand-drawn lines/points, stripped of terra-draw's internal properties.
        drawnFeatures.forEach((f) => {
            if (f.geometry) features.push({ type: "Feature", geometry: f.geometry, properties: {} });
        });

        return features.length > 0
            ? JSON.stringify({ type: "FeatureCollection", features })
            : null;
    }

    async function handleAccept() {
        const hasNewGeometry = !!previewFeature || !!uploadedGeojson || hasPoints || hasDrawn || hasEditedExisting;

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
    const canAccept = !selectionMode && (!!previewFeature || !!uploadedGeojson || hasPoints || hasDrawn || hasEditedExisting || deleteExisting);
    const isDeleteOnly = deleteExisting && !previewFeature && !uploadedGeojson && !hasPoints && !hasDrawn && !hasEditedExisting;

    return (
        <Group
            align="stretch"
            gap={0}
            wrap="nowrap"
            // Side by side needs ~700px — on a phone the controls sit above the map.
            style={{ width: "100%", height, flexDirection: isMobile ? "column" : "row" }}
        >
            {/* ── Left panel (top on phones): controls ────────────────── */}
            <Box
                style={{
                    display: "flex",
                    flexDirection: "column",
                    ...(isMobile
                        ? {
                              width: "100%",
                              flex: "0 1 auto",
                              maxHeight: "50%",
                              borderBottom: "2px solid var(--border-frame)",
                          }
                        : {
                              width: 380,
                              minWidth: 320,
                              borderRight: "2px solid var(--border-frame)",
                          }),
                }}
            >
                <ScrollArea style={{ flex: 1 }} p="md">
                    <Stack gap="md">
                        {/* Current status */}
                        <div>
                            <Text className="idt-eyebrow" mb={6}>
                                Aktuelle Geometrie
                            </Text>
                            <Badge variant="outline" color="var(--text-strong)" tt="none">
                                {hasExisting ? "Geometrie vorhanden" : "Keine Geometrie"}
                            </Badge>
                        </div>

                        {isSuperiorProject && (
                            <Switch
                                label="Geometrie automatisch aus Unterprojekten zusammensetzen"
                                description={
                                    subProjectCount === 1
                                        ? "Aus der Geometrie des Unterprojekts zusammensetzen, statt sie hier selbst zu pflegen."
                                        : `Aus den Geometrien der ${subProjectCount} Unterprojekte zusammensetzen, statt sie hier selbst zu pflegen.`
                                }
                                checked={isAggregated}
                                onChange={(e) => handleGeojsonSourceChange(e.currentTarget.checked)}
                                disabled={updateGeojsonSource.isPending}
                            />
                        )}

                        {isAggregated ? (
                            <Alert color="blue" variant="light" title="Automatisch zusammengesetzt">
                                Die Karte zeigt die vereinigten Geometrien der Unterprojekte. Ändere
                                die Geometrie im jeweiligen Unterprojekt — oder schalte die
                                automatische Zusammensetzung ab, um für dieses Projekt eine eigene
                                Geometrie zu pflegen.
                            </Alert>
                        ) : (
                            <>
                                {hasExisting && (
                                    <Switch
                                        label="Bestehende Geometrie löschen"
                                        checked={deleteExisting}
                                        onChange={(e) => setDeleteExisting(e.currentTarget.checked)}
                                        color="red"
                                        disabled={selectionMode || drawMode !== null || editExisting}
                                    />
                                )}

                                {hasExisting && (
                                    <Stack gap="xs">
                                        <Switch
                                            label="Bestehende Geometrie bearbeiten"
                                            description="Stützpunkte gespeicherter Linien und Punkte verschieben, Zwischenpunkte einfügen oder löschen."
                                            checked={editExisting}
                                            onChange={(e) => toggleEditExisting(e.currentTarget.checked)}
                                            disabled={selectionMode || deleteExisting}
                                        />
                                        {editExisting && (
                                            <>
                                                <Text size="xs" c="dimmed">
                                                    Linie oder Punkt anklicken, um sie auszuwählen. Dann Stützpunkte
                                                    ziehen; einen der kleinen Punkte zwischen zwei Stützpunkten anklicken oder
                                                    ziehen, um einen Zwischenpunkt einzufügen; Rechtsklick auf einen Stützpunkt
                                                    löscht ihn. Gespeichert wird erst mit „{saveLabel}".
                                                </Text>
                                                <Group justify="space-between" align="center">
                                                    <Badge variant="outline" color="var(--text-strong)" tt="none">
                                                        {hasEditedExisting ? "Geändert" : "Unverändert"}
                                                    </Badge>
                                                    {hasEditedExisting && (
                                                        <Button
                                                            size="xs"
                                                            variant="subtle"
                                                            color="red"
                                                            onClick={() => toggleEditExisting(true)}
                                                        >
                                                            Änderungen verwerfen
                                                        </Button>
                                                    )}
                                                </Group>
                                            </>
                                        )}
                                    </Stack>
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
                                            disabled={deleteExisting || drawMode !== null || hasDrawn || editExisting}
                                        />
                                        {selectionMode && (
                                            <Stack gap="xs">
                                                <Text size="xs" c="dimmed">
                                                    Klicke auf der Karte einzelne Linien oder Punkte, um sie auszuwählen.
                                                    Ausgewählte Features erscheinen rot.
                                                </Text>
                                                <Group justify="space-between" align="center">
                                                    <Badge variant="outline" color="var(--text-strong)" tt="none">
                                                        {selectedFeatureIndices.size} ausgewählt
                                                    </Badge>
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

                                <Divider label="Zeichnen" labelPosition="left" />

                                <Stack gap="xs">
                                    <Text size="xs" c="dimmed">
                                        Zeichne Linien und Punkte direkt auf der Karte. „Linie zeichnen": Klick für Klick
                                        Stützpunkte setzen, Doppelklick beendet die Linie. „Bearbeiten": Stützpunkte
                                        verschieben, einfügen (Mittelpunkt) oder löschen.
                                    </Text>
                                    <Group gap="xs" wrap="wrap">
                                        <Button
                                            size="xs"
                                            variant={drawMode === "line" ? "filled" : "default"}
                                            onClick={() => setDrawMode(drawMode === "line" ? null : "line")}
                                            disabled={selectionMode || deleteExisting}
                                        >
                                            Linie zeichnen
                                        </Button>
                                        <Button
                                            size="xs"
                                            variant={drawMode === "point" ? "filled" : "default"}
                                            onClick={() => setDrawMode(drawMode === "point" ? null : "point")}
                                            disabled={selectionMode || deleteExisting}
                                        >
                                            Punkt setzen
                                        </Button>
                                        <Button
                                            size="xs"
                                            variant={drawMode === "select" ? "filled" : "default"}
                                            onClick={() => setDrawMode(drawMode === "select" ? null : "select")}
                                            disabled={selectionMode || deleteExisting || (!hasDrawn && !editExisting)}
                                        >
                                            Bearbeiten
                                        </Button>
                                        <Button
                                            size="xs"
                                            variant="default"
                                            onClick={() => setDrawMode(null)}
                                            disabled={drawMode === null}
                                        >
                                            Fertig
                                        </Button>
                                    </Group>
                                    <Group justify="space-between" align="center">
                                        <Badge variant="outline" color="var(--text-strong)" tt="none">
                                            {drawnFeatures.length} gezeichnet
                                            {drawnLengthKm != null ? ` · ${drawnLengthKm.toLocaleString("de-DE")} km` : ""}
                                        </Badge>
                                        {hasDrawn && (
                                            <Button
                                                size="xs"
                                                variant="subtle"
                                                color="red"
                                                onClick={() => { setDrawnFeatures([]); setDrawMode(null); }}
                                            >
                                                Zurücksetzen
                                            </Button>
                                        )}
                                    </Group>
                                </Stack>

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

                                {previewFeature && routeStations.length > 0 && (
                                    <Switch
                                        label="Start, Ziel und Zwischenhalte als Punkte übernehmen"
                                        description="Standardmäßig wird nur die Linie gespeichert."
                                        checked={addRouteStations}
                                        onChange={(e) => setAddRouteStations(e.currentTarget.checked)}
                                    />
                                )}

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
                                    <Paper withBorder p="var(--card-pad)">
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
                                    <Paper withBorder p="var(--card-pad)">
                                        <Text size="sm" fw={600}>GeoJSON geladen — bitte prüfen</Text>
                                    </Paper>
                                )}
                            </>
                        )}
                    </Stack>
                </ScrollArea>

                {/* Foot of the dialog: cancel framed on the left, confirm (or the red
                    delete) filled on the right — two actions at most. */}
                <Group
                    p="md"
                    justify="flex-end"
                    gap={10}
                    grow={isMobile}
                    style={{ borderTop: "2px solid var(--border-frame)" }}
                >
                    {showCancel && (
                        <Button variant="default" onClick={onCancel} disabled={isPending}>
                            {cancelLabel}
                        </Button>
                    )}
                    {!isAggregated && (
                        <Button
                            onClick={handleAccept}
                            loading={isPending}
                            disabled={!canAccept}
                            variant="filled"
                            color={isDeleteOnly ? "red" : undefined}
                        >
                            {isDeleteOnly ? "Geometrie löschen" : saveLabel}
                        </Button>
                    )}
                </Group>
            </Box>

            {/* ── Right panel (below on phones): map ──────────────────── */}
            <Box style={{ flex: 1, position: "relative", minWidth: 0, minHeight: isMobile ? 240 : undefined }}>
                <GeometryPreviewMap
                    existingGeojson={project.geojson_representation ?? null}
                    previewFeature={previewFeature ?? (uploadedGeojson ? buildUploadPreview(uploadedGeojson) : null)}
                    // While editing in place, terra-draw renders the saved geometry itself.
                    showExisting={!deleteExisting && !editExisting}
                    previewPoints={addRouteStations && previewFeature ? [...routeStations, ...selectedPoints] : selectedPoints}
                    selectionMode={selectionMode}
                    selectedIndices={selectedFeatureIndices}
                    onFeatureClick={toggleFeatureSelection}
                    drawMode={drawMode}
                    drawnFeatures={drawnFeatures}
                    onDrawnFeaturesChange={setDrawnFeatures}
                    editableParts={editableParts}
                    onEditedPartsChange={setEditedParts}
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
 * so the map can display it as a preview (dashed cyan). Only used for display.
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
