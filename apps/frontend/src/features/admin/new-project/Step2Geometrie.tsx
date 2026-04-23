import {
    ActionIcon,
    Alert,
    Button,
    Divider,
    FileInput,
    Group,
    Stack,
    Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import type { OperationalPointRef, RoutePreviewFeature } from "../../../shared/api/queries";
import { useConfirmRoute, useUpdateProjectGeometry } from "../../../shared/api/queries";
import RouteCalculatorForm from "../../routing/RouteCalculatorForm";
import StationSelect from "../../routing/StationSelect";

type Props = {
    projectId: number;
    onDone: () => void;
};

export default function Step2Geometrie({ projectId, onDone }: Props) {
    const [previewFeature, setPreviewFeature] = useState<RoutePreviewFeature | null>(null);
    const [uploadedGeojson, setUploadedGeojson] = useState<string | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [routeError, setRouteError] = useState<string | null>(null);
    const [selectedPoints, setSelectedPoints] = useState<OperationalPointRef[]>([]);
    const [pointSelectKey, setPointSelectKey] = useState(0);

    const confirmRoute = useConfirmRoute(projectId);
    const updateGeometry = useUpdateProjectGeometry(projectId);
    const isPending = confirmRoute.isPending || updateGeometry.isPending;

    const hasPoints = selectedPoints.length > 0;
    const canSave = !!previewFeature || !!uploadedGeojson || hasPoints;

    function buildNewGeometry(): string | null {
        if (!previewFeature && !hasPoints && uploadedGeojson) return uploadedGeojson;

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
        for (const op of selectedPoints) {
            if (op.latitude != null && op.longitude != null) {
                features.push({
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [op.longitude, op.latitude] },
                    properties: { name: op.name ?? null, op_id: op.op_id ?? null, feature_type: "operational_point" },
                });
            }
        }
        return features.length > 0
            ? JSON.stringify({ type: "FeatureCollection", features })
            : null;
    }

    async function handleSave() {
        if (!canSave) {
            onDone();
            return;
        }
        try {
            if (previewFeature) {
                await confirmRoute.mutateAsync(previewFeature);
            }
            const geometry = buildNewGeometry();
            if (geometry) {
                await updateGeometry.mutateAsync(geometry);
            }
            notifications.show({
                color: "green",
                title: "Geometrie gespeichert",
                message: "Die Projektgeometrie wurde angelegt.",
            });
            onDone();
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

    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">
                Lege eine Geometrie für dieses Projekt an (optional): Route zwischen Betriebsstellen
                berechnen, einzelne Betriebsstellen hinzufügen oder eine GeoJSON-Datei hochladen.
            </Text>

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

            {previewFeature && (
                <Alert color="blue" variant="light">
                    <Text size="sm" fw={600}>Berechnete Route</Text>
                    <Text size="sm" c="dimmed">
                        Distanz: {(previewFeature.properties.distance_m / 1000).toFixed(1)} km
                        {" · "}
                        Dauer: {Math.round(previewFeature.properties.duration_ms / 60_000)} min
                    </Text>
                </Alert>
            )}
            {uploadedGeojson && !previewFeature && (
                <Alert color="green" variant="light">
                    <Text size="sm" fw={600}>GeoJSON geladen — bitte prüfen</Text>
                </Alert>
            )}

            <Group justify="flex-end">
                <Button variant="subtle" onClick={onDone} disabled={isPending}>
                    Überspringen
                </Button>
                <Button onClick={handleSave} disabled={!canSave} loading={isPending}>
                    Speichern & Weiter
                </Button>
            </Group>
        </Stack>
    );
}
