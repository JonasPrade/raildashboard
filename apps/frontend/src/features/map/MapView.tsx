import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Paper, Stack, Text } from "@mantine/core";
import maplibregl from "maplibre-gl";
import { useNavigate } from "react-router-dom";

const tileLayerUrl = import.meta.env.REACT_APP_TILE_LAYER_URL as string | undefined;
const tileAttribution =
    'Kartenhintergrund: <a href="https://www.bkg.bund.de" target="_blank" rel="noopener noreferrer">Bundesamt für Kartographie und Geodäsie</a>';

type MapViewProject = {
    id: number;
    name: string;
    groupColor?: string;
    geojson_representation?: string | null;
};

type GeoJSONGeometry = {
    type: string;
    coordinates?: unknown;
    [key: string]: unknown;
};

type GeoJSONFeature = {
    id?: string | number;
    type: "Feature";
    geometry: GeoJSONGeometry | null;
    properties: Record<string, unknown>;
    [key: string]: unknown;
};

type GeoJSONFeatureCollection = {
    type: "FeatureCollection";
    features: GeoJSONFeature[];
};

// ── type guards ──────────────────────────────────────────────────────────────

const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === "object" && value !== null;

const isFeatureCollection = (value: unknown): value is { type: "FeatureCollection"; features: unknown[] } =>
    isRecord(value) && value.type === "FeatureCollection" && Array.isArray(value.features);

const isFeature = (value: unknown): value is { type: "Feature"; geometry: unknown; properties?: unknown } =>
    isRecord(value) && value.type === "Feature" && "geometry" in value;

const isGeometry = (value: unknown): value is GeoJSONGeometry =>
    isRecord(value) && typeof value.type === "string" && "coordinates" in value;

const isNumberArray = (v: unknown): v is number[] =>
    Array.isArray(v) && v.every((n) => typeof n === "number");

const isCoordArray = (v: unknown): v is number[][] =>
    Array.isArray(v) && v.every(isNumberArray);

const isCoordArrayArray = (v: unknown): v is number[][][] =>
    Array.isArray(v) && v.every(isCoordArray);

// ── geometry extractors ──────────────────────────────────────────────────────

/** Recursively collect all LineString coordinate arrays from any GeoJSON value. */
const extractLineCoordinates = (geojson: unknown): number[][][] => {
    if (isFeatureCollection(geojson)) {
        return geojson.features.flatMap((f) => (isFeature(f) ? extractLineCoordinates(f) : []));
    }
    if (isFeature(geojson)) {
        return extractLineCoordinates(geojson.geometry);
    }
    if (isGeometry(geojson)) {
        const coords = geojson.coordinates;
        if (geojson.type === "LineString" && isCoordArray(coords)) return [coords];
        if (geojson.type === "MultiLineString" && isCoordArrayArray(coords)) return coords;
    }
    return [];
};

/** Recursively collect all Point coordinates from any GeoJSON value. */
const extractPointCoordinates = (geojson: unknown): number[][] => {
    if (isFeatureCollection(geojson)) {
        return geojson.features.flatMap((f) => (isFeature(f) ? extractPointCoordinates(f) : []));
    }
    if (isFeature(geojson)) {
        return extractPointCoordinates(geojson.geometry);
    }
    if (isGeometry(geojson)) {
        const coords = geojson.coordinates;
        if (geojson.type === "Point" && isNumberArray(coords)) return [coords];
        if (geojson.type === "MultiPoint" && isCoordArray(coords)) return coords;
    }
    return [];
};

// ── GeoJSON parsing ──────────────────────────────────────────────────────────

const parseProjectGeojson = (geojsonRepresentation?: string | null) => {
    if (!geojsonRepresentation) return null;
    try {
        return JSON.parse(geojsonRepresentation) as unknown;
    } catch {
        return null;
    }
};

// ── feature builders (one feature per project) ───────────────────────────────

const BASE_PROJECT_PROPERTIES = (project: MapViewProject) => ({
    projectId: project.id,
    name: project.name,
    groupColor: project.groupColor,
});

const createProjectLineFeature = (project: MapViewProject): GeoJSONFeature | null => {
    const geojson = parseProjectGeojson(project.geojson_representation);
    if (!geojson) return null;
    const lines = extractLineCoordinates(geojson);
    if (lines.length === 0) return null;
    return {
        id: project.id,
        type: "Feature",
        geometry: { type: "MultiLineString", coordinates: lines },
        properties: BASE_PROJECT_PROPERTIES(project),
    };
};

const createProjectPointFeature = (project: MapViewProject): GeoJSONFeature | null => {
    const geojson = parseProjectGeojson(project.geojson_representation);
    if (!geojson) return null;
    const points = extractPointCoordinates(geojson);
    if (points.length === 0) return null;
    return {
        id: project.id,
        type: "Feature",
        geometry: { type: "MultiPoint", coordinates: points },
        properties: BASE_PROJECT_PROPERTIES(project),
    };
};

// ── component ────────────────────────────────────────────────────────────────

type Props = {
    projects: MapViewProject[];
    lineWidth?: number;
    pointSize?: number;
};

type SelectedProject = {
    id: number;
    name: string;
    x: number;
    y: number;
};

export default function MapView({ projects, lineWidth = 4, pointSize = 5 }: Props) {
    const mapContainerRef = useRef<HTMLDivElement | null>(null);
    const mapInstanceRef = useRef<maplibregl.Map | null>(null);
    const hoverFeatureIdRef = useRef<string | number | null>(null);
    const overlayRef = useRef<HTMLDivElement | null>(null);
    const ignoreOutsideClickRef = useRef(false);
    const [isMapReady, setIsMapReady] = useState(false);
    const [selectedProject, setSelectedProject] = useState<SelectedProject | null>(null);
    const navigate = useNavigate();

    // One MultiLineString feature per project
    const lineFeatureCollection = useMemo<GeoJSONFeatureCollection>(() => ({
        type: "FeatureCollection",
        features: projects
            .map(createProjectLineFeature)
            .filter((f): f is GeoJSONFeature => f !== null),
    }), [projects]);

    // One MultiPoint feature per project (only when the GeoJSON contains points)
    const pointFeatureCollection = useMemo<GeoJSONFeatureCollection>(() => ({
        type: "FeatureCollection",
        features: projects
            .map(createProjectPointFeature)
            .filter((f): f is GeoJSONFeature => f !== null),
    }), [projects]);

    useEffect(() => {
        if (!tileLayerUrl || !mapContainerRef.current) {
            return undefined;
        }

        const mapInstance = new maplibregl.Map({
            container: mapContainerRef.current,
            style: {
                version: 8,
                sources: {
                    basemap: {
                        type: "raster",
                        tiles: [tileLayerUrl],
                        tileSize: 256,
                        attribution: tileAttribution,
                    },
                    "project-routes": {
                        type: "geojson",
                        data: { type: "FeatureCollection", features: [] },
                    },
                    "project-points": {
                        type: "geojson",
                        data: { type: "FeatureCollection", features: [] },
                    },
                },
                layers: [
                    {
                        id: "basemap",
                        type: "raster",
                        source: "basemap",
                    },
                    {
                        id: "project-routes-line",
                        type: "line",
                        source: "project-routes",
                        layout: {
                            "line-cap": "round",
                            "line-join": "round",
                        },
                        paint: {
                            "line-color": ["coalesce", ["get", "groupColor"], "#2563eb"],
                            "line-width": [
                                "case",
                                ["boolean", ["feature-state", "hover"], false],
                                8,
                                4,
                            ],
                        },
                    },
                    {
                        id: "project-points-circle",
                        type: "circle",
                        source: "project-points",
                        paint: {
                            "circle-color": ["coalesce", ["get", "groupColor"], "#2563eb"],
                            "circle-radius": [
                                "case",
                                ["boolean", ["feature-state", "hover"], false],
                                8,
                                5,
                            ],
                            "circle-stroke-width": 1.5,
                            "circle-stroke-color": "#ffffff",
                        },
                    },
                ],
            },
            center: [10.0, 51.0],
            zoom: 5,
        });

        mapInstanceRef.current = mapInstance;

        mapInstance.on("load", () => {
            setIsMapReady(true);
        });

        // Single map-level mousemove: checks both project layers for smooth
        // transitions between lines and points of the same project.
        const handleMouseMove = (event: maplibregl.MapMouseEvent & maplibregl.EventData) => {
            const features = mapInstance.queryRenderedFeatures(event.point, {
                layers: ["project-routes-line", "project-points-circle"],
            });
            const feature = features[0];
            const newId = feature?.id !== undefined && feature?.id !== null ? feature.id : null;

            if (newId === null) {
                mapInstance.getCanvas().style.cursor = "";
                if (hoverFeatureIdRef.current !== null) {
                    mapInstance.setFeatureState(
                        { source: "project-routes", id: hoverFeatureIdRef.current },
                        { hover: false },
                    );
                    mapInstance.setFeatureState(
                        { source: "project-points", id: hoverFeatureIdRef.current },
                        { hover: false },
                    );
                    hoverFeatureIdRef.current = null;
                }
                return;
            }

            mapInstance.getCanvas().style.cursor = "pointer";

            if (hoverFeatureIdRef.current !== null && hoverFeatureIdRef.current !== newId) {
                mapInstance.setFeatureState(
                    { source: "project-routes", id: hoverFeatureIdRef.current },
                    { hover: false },
                );
                mapInstance.setFeatureState(
                    { source: "project-points", id: hoverFeatureIdRef.current },
                    { hover: false },
                );
            }

            if (hoverFeatureIdRef.current !== newId) {
                hoverFeatureIdRef.current = newId;
                mapInstance.setFeatureState({ source: "project-routes", id: newId }, { hover: true });
                mapInstance.setFeatureState({ source: "project-points", id: newId }, { hover: true });
            }
        };

        // Clear hover when mouse leaves the map canvas entirely
        const handleMouseLeaveCanvas = () => {
            mapInstance.getCanvas().style.cursor = "";
            if (hoverFeatureIdRef.current !== null) {
                mapInstance.setFeatureState(
                    { source: "project-routes", id: hoverFeatureIdRef.current },
                    { hover: false },
                );
                mapInstance.setFeatureState(
                    { source: "project-points", id: hoverFeatureIdRef.current },
                    { hover: false },
                );
                hoverFeatureIdRef.current = null;
            }
        };

        mapInstance.on("mousemove", handleMouseMove);
        mapInstance.getCanvas().addEventListener("mouseleave", handleMouseLeaveCanvas);

        const handleProjectClick = (
            event: maplibregl.MapMouseEvent & maplibregl.EventData,
        ) => {
            const feature = event.features?.[0];
            if (!feature || !isRecord(feature.properties)) return;

            const projectIdValue = feature.properties.projectId;
            const projectNameValue = feature.properties.name;
            const projectId =
                typeof projectIdValue === "number" ? projectIdValue : Number(projectIdValue);

            if (!Number.isFinite(projectId) || typeof projectNameValue !== "string") {
                return;
            }

            ignoreOutsideClickRef.current = true;
            setSelectedProject({
                id: projectId,
                name: projectNameValue,
                x: event.point.x,
                y: event.point.y,
            });
        };

        const handleMapClick = (event: maplibregl.MapMouseEvent & maplibregl.EventData) => {
            const features = mapInstance.queryRenderedFeatures(event.point, {
                layers: ["project-routes-line", "project-points-circle"],
            });
            if (features.length === 0) {
                setSelectedProject(null);
            }
        };

        mapInstance.on("click", "project-routes-line", handleProjectClick);
        mapInstance.on("click", "project-points-circle", handleProjectClick);
        mapInstance.on("click", handleMapClick);

        return () => {
            mapInstance.getCanvas().style.cursor = "";
            mapInstance.getCanvas().removeEventListener("mouseleave", handleMouseLeaveCanvas);
            mapInstance.off("mousemove", handleMouseMove);
            mapInstance.off("click", "project-routes-line", handleProjectClick);
            mapInstance.off("click", "project-points-circle", handleProjectClick);
            mapInstance.off("click", handleMapClick);
            mapInstance.remove();
        };
    }, [tileLayerUrl]);

    // Update both GeoJSON sources whenever project data changes
    useEffect(() => {
        if (!isMapReady) return;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        const lineSource = mapInstance.getSource("project-routes") as maplibregl.GeoJSONSource | undefined;
        const pointSource = mapInstance.getSource("project-points") as maplibregl.GeoJSONSource | undefined;
        if (lineSource) lineSource.setData(lineFeatureCollection);
        if (pointSource) pointSource.setData(pointFeatureCollection);
    }, [lineFeatureCollection, pointFeatureCollection, isMapReady]);

    // Update line-width expression when the slider changes
    useEffect(() => {
        if (!isMapReady) return;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        mapInstance.setPaintProperty("project-routes-line", "line-width", [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            lineWidth + 4,
            lineWidth,
        ]);
    }, [lineWidth, isMapReady]);

    // Update circle-radius expression when the point size slider changes
    useEffect(() => {
        if (!isMapReady) return;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        mapInstance.setPaintProperty("project-points-circle", "circle-radius", [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            pointSize + 3,
            pointSize,
        ]);
    }, [pointSize, isMapReady]);

    useEffect(() => {
        if (!selectedProject) return undefined;

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                setSelectedProject(null);
            }
        };

        const handleOutsideClick = (event: MouseEvent) => {
            if (ignoreOutsideClickRef.current) {
                ignoreOutsideClickRef.current = false;
                return;
            }
            const overlayNode = overlayRef.current;
            if (overlayNode && event.target instanceof Node && overlayNode.contains(event.target)) {
                return;
            }
            setSelectedProject(null);
        };

        window.addEventListener("keydown", handleKeyDown);
        document.addEventListener("mousedown", handleOutsideClick);

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            document.removeEventListener("mousedown", handleOutsideClick);
        };
    }, [selectedProject]);

    if (!tileLayerUrl) {
        return (
            <div
                style={{
                    height: "800px",
                    backgroundColor: "#f2f2f2",
                    borderRadius: "8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "24px",
                    textAlign: "center"
                }}
                role="alert"
            >
                <p>
                    Kartenkachel-URL fehlt. Bitte die Umgebungsvariable
                    <strong> REACT_APP_TILE_LAYER_URL</strong> setzen.
                </p>
            </div>
        );
    }

    return (
        <div style={{ height: "800px", position: "relative" }}>
            <div ref={mapContainerRef} style={{ height: "100%" }} />
            {selectedProject && (
                <Paper
                    ref={overlayRef}
                    shadow="md"
                    p="md"
                    radius="md"
                    style={{
                        position: "absolute",
                        left: selectedProject.x,
                        top: selectedProject.y,
                        transform: "translate(-50%, calc(-100% - 12px))",
                        minWidth: "220px",
                        zIndex: 10,
                    }}
                >
                    <Stack gap="xs">
                        <Text fw={600}>{selectedProject.name}</Text>
                        <Button
                            size="xs"
                            onClick={() => {
                                navigate(`/projects/${selectedProject.id}`);
                                setSelectedProject(null);
                            }}
                        >
                            Auswählen
                        </Button>
                    </Stack>
                </Paper>
            )}
        </div>
    );
}
