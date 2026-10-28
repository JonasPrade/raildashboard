import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Button, Stack } from "@mantine/core";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { ConstituencyFeatureCollection, ProjectOverview } from "../../shared/api/queries";
import { usePrefetchProjectPage } from "../projects/usePrefetchProjectPage";
import ProjectSummaryCard from "../projects/ProjectSummaryCard";
import MapOverlapList from "./MapOverlapList";
import { type LaneInfo, assignVisibleLanes, laneOffset, lineOffsetExpression } from "./mapLanes";
import { counterTextColor, groupSharedPoints } from "./mapPoints";
import {
    PROJECT_LAYERS,
    hitBox,
    hitTolerancePx,
    isCoarsePointer,
    projectIdsFromFeatures,
    sortProjectsByName,
} from "./mapHits";
import { featureBounds } from "./featureBounds";
import { LIGHT_TILE_URL as tileLayerUrl, swapRasterTiles, useTileUrl } from "../../shared/geo/useTileUrl";
import { MAP_COLOR } from "../../shared/theme/semanticColors";

const tileAttribution =
    'Kartenhintergrund: <a href="https://www.bkg.bund.de" target="_blank" rel="noopener noreferrer">Bundesamt für Kartographie und Geodäsie</a>';

export type MapViewProject = ProjectOverview & {
    id: number;
    groupColor?: string;
    /**
     * Already-parsed GeoJSON (the overview map's simplified geometry). Takes
     * precedence over `geojson_representation`, the exact stored text that
     * full `Project`s (detail page) carry.
     */
    geometry?: unknown;
    /** Stored lane and overlap partners from the geometries endpoint; the map
     *  draws projects that share a track side by side (B1). */
    mapLane?: LaneInfo | null;
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

// Only store the minimal properties needed for map styling in GeoJSON.
// Full project data is looked up from projectsRef on click.
const BASE_PROJECT_PROPERTIES = (project: MapViewProject) => ({
    projectId: project.id,
    groupColor: project.groupColor,
});

type ProjectFeatures = {
    line: GeoJSONFeature | null;
    point: GeoJSONFeature | null;
};

/** Parse a project's GeoJSON once and build both map features from it. */
const createProjectFeatures = (project: MapViewProject): ProjectFeatures => {
    const geojson = project.geometry ?? parseProjectGeojson(project.geojson_representation);
    if (!geojson) return { line: null, point: null };
    const lines = extractLineCoordinates(geojson);
    const points = extractPointCoordinates(geojson);
    const properties = BASE_PROJECT_PROPERTIES(project);
    return {
        line: lines.length
            ? {
                  id: project.id,
                  type: "Feature",
                  geometry: { type: "MultiLineString", coordinates: lines },
                  properties,
              }
            : null,
        point: points.length
            ? {
                  id: project.id,
                  type: "Feature",
                  geometry: { type: "MultiPoint", coordinates: points },
                  properties,
              }
            : null,
    };
};

type FeatureCacheEntry = ProjectFeatures & {
    geojson: string | null | undefined;
    geometry: unknown;
    groupColor: string | undefined;
};

// ── component ────────────────────────────────────────────────────────────────

type Props = {
    projects: MapViewProject[];
    lineWidth?: number;
    pointSize?: number;
    /**
     * Any CSS length. Defaults to the `--map-height` token, which shrinks to
     * the visible viewport on phones (docs/features/feature-mobile-usability.md).
     */
    height?: number | string;
    /** Klick-Interaktion (Popup + Navigation) aktivieren. Standard: true */
    clickable?: boolean;
    /**
     * Zoom to the projects' geometry once it has loaded (detail page). Without it,
     * or without any geometry, the map starts on the whole of Germany.
     */
    fitToProjects?: boolean;
    /** Constituency outlines as a switchable background layer (© GeoBasis-DE / BKG). */
    constituencies?: ConstituencyFeatureCollection | null;
    /** Called with the clicked constituency id, or null when the click missed. */
    onConstituencySelect?: (constituencyId: number | null) => void;
    /** Highlighted constituency, driven by the selection panel. */
    selectedConstituencyId?: number | null;
};

/** The click popup: every project hit at the clicked spot, and the one whose
 *  summary is open (null = the list of all hits). */
type Popup = {
    projects: MapViewProject[];
    selectedId: number | null;
    x: number;
    y: number;
};

/** Station counters (D): which projects a counter stands for, and back. */
type ClusterLookup = {
    projectsOf: Map<number, number[]>;
    clustersOf: Map<number, number[]>;
};

const EMPTY_CLUSTERS: ClusterLookup = { projectsOf: new Map(), clustersOf: new Map() };

/** Project ids under *point*, each once (docs/features/feature-map-overlapping-geometries.md → A). */
const queryProjectIds = (
    mapInstance: maplibregl.Map,
    point: { x: number; y: number },
    clusters: ClusterLookup,
): number[] =>
    projectIdsFromFeatures(
        mapInstance.queryRenderedFeatures(hitBox(point, hitTolerancePx(isCoarsePointer())), {
            layers: PROJECT_LAYERS,
        }),
        clusters.projectsOf,
    );

const clustersOfProjects = (ids: Iterable<number>, clusters: ClusterLookup): Set<number> => {
    const result = new Set<number>();
    for (const id of ids) for (const clusterId of clusters.clustersOf.get(id) ?? []) result.add(clusterId);
    return result;
};

/** Move the `hover` feature-state from the projects in *previous* to *next*,
 *  including the station counters they take part in. */
const applyHover = (
    mapInstance: maplibregl.Map,
    previous: Set<number>,
    next: number[],
    clusters: ClusterLookup,
): Set<number> => {
    const nextSet = new Set(next);
    for (const id of previous) {
        if (nextSet.has(id)) continue;
        mapInstance.setFeatureState({ source: "project-routes", id }, { hover: false });
        mapInstance.setFeatureState({ source: "project-points", id }, { hover: false });
    }
    for (const id of nextSet) {
        if (previous.has(id)) continue;
        mapInstance.setFeatureState({ source: "project-routes", id }, { hover: true });
        mapInstance.setFeatureState({ source: "project-points", id }, { hover: true });
    }
    const previousClusters = clustersOfProjects(previous, clusters);
    const nextClusters = clustersOfProjects(nextSet, clusters);
    for (const id of previousClusters) {
        if (!nextClusters.has(id)) mapInstance.setFeatureState({ source: "project-point-clusters", id }, { hover: false });
    }
    for (const id of nextClusters) {
        if (!previousClusters.has(id)) mapInstance.setFeatureState({ source: "project-point-clusters", id }, { hover: true });
    }
    return nextSet;
};

export default function MapView({
    projects,
    lineWidth = 4,
    pointSize = 5,
    height = "var(--map-height, 800px)",
    clickable = true,
    fitToProjects = false,
    constituencies = null,
    onConstituencySelect,
    selectedConstituencyId = null,
}: Props) {
    const mapContainerRef = useRef<HTMLDivElement | null>(null);
    const mapInstanceRef = useRef<maplibregl.Map | null>(null);
    const hoverIdsRef = useRef<Set<number>>(new Set());
    const clustersRef = useRef<ClusterLookup>(EMPTY_CLUSTERS);
    const overlayRef = useRef<HTMLDivElement | null>(null);
    const ignoreOutsideClickRef = useRef(false);
    // Keep a ref so the click handler (inside the init useEffect) always sees
    // the current project list without needing it as a dependency.
    const projectsRef = useRef<MapViewProject[]>(projects);
    const [isMapReady, setIsMapReady] = useState(false);
    const hasFittedRef = useRef(false);
    const [popup, setPopup] = useState<Popup | null>(null);
    const prefetchProjectPage = usePrefetchProjectPage();
    const selectedProject =
        popup?.selectedId != null ? popup.projects.find((p) => p.id === popup.selectedId) ?? null : null;

    // The popup's "Auswählen" is the next likely click: load the detail page
    // (chunk + data) while the user is still reading the summary.
    useEffect(() => {
        if (popup?.selectedId != null) prefetchProjectPage(popup.selectedId);
    }, [popup?.selectedId, prefetchProjectPage]);

    const setHover = (ids: number[]) => {
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        hoverIdsRef.current = applyHover(mapInstance, hoverIdsRef.current, ids, clustersRef.current);
    };
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    useEffect(() => {
        projectsRef.current = projects;
    }, [projects]);

    // Features are built once per project and cached by id — filtering (e.g.
    // typing in the search field) only reassembles the collections from
    // prebuilt features instead of re-parsing every geojson_representation.
    // A changed geometry or group color invalidates that project's entry.
    const featureCacheRef = useRef(new Map<number, FeatureCacheEntry>());
    const { lineFeatureCollection, pointFeatureCollection, clusterFeatureCollection, clusterLookup } = useMemo(() => {
        const cache = featureCacheRef.current;
        // Lanes depend on which projects are shown, so they are applied on top
        // of the cached features instead of being cached with them.
        const lanes = assignVisibleLanes(projects);
        const lines: GeoJSONFeature[] = [];
        const pointEntries: { project: MapViewProject; feature: GeoJSONFeature }[] = [];
        for (const project of projects) {
            const cached = cache.get(project.id);
            let entry: FeatureCacheEntry;
            if (
                cached &&
                cached.geojson === project.geojson_representation &&
                cached.geometry === project.geometry &&
                cached.groupColor === project.groupColor
            ) {
                entry = cached;
            } else {
                entry = {
                    geojson: project.geojson_representation,
                    geometry: project.geometry,
                    groupColor: project.groupColor,
                    ...createProjectFeatures(project),
                };
                cache.set(project.id, entry);
            }
            if (entry.line) {
                const offset = laneOffset(lanes.get(project.id) ?? 0);
                lines.push(
                    offset === 0
                        ? entry.line
                        : { ...entry.line, properties: { ...entry.line.properties, laneOffset: offset } },
                );
            }
            if (entry.point) pointEntries.push({ project, feature: entry.point });
        }

        // Station counters (D): a spot shared by several projects becomes one
        // counter; each project keeps a point feature only for its own spots.
        const grouped = groupSharedPoints(
            pointEntries.map(({ project, feature }) => ({
                id: project.id,
                groupColor: project.groupColor,
                points: (feature.geometry?.coordinates ?? []) as number[][],
            })),
        );
        const points: GeoJSONFeature[] = [];
        for (const { project, feature } of pointEntries) {
            const own = grouped.singles.get(project.id);
            if (!own) continue;
            const all = (feature.geometry?.coordinates ?? []) as number[][];
            points.push(
                own.length === all.length
                    ? feature
                    : { ...feature, geometry: { type: "MultiPoint", coordinates: own } },
            );
        }
        const lookup: ClusterLookup = { projectsOf: new Map(), clustersOf: new Map() };
        const clusterFeatures: GeoJSONFeature[] = grouped.clusters.map((cluster) => {
            lookup.projectsOf.set(cluster.id, cluster.projectIds);
            for (const projectId of cluster.projectIds) {
                lookup.clustersOf.set(projectId, [...(lookup.clustersOf.get(projectId) ?? []), cluster.id]);
            }
            return {
                id: cluster.id,
                type: "Feature",
                geometry: { type: "Point", coordinates: cluster.coordinate },
                properties: {
                    clusterId: cluster.id,
                    count: cluster.projectIds.length,
                    groupColor: cluster.color,
                    textColor: counterTextColor(cluster.color),
                },
            };
        });

        return {
            clusterFeatureCollection: {
                type: "FeatureCollection",
                features: clusterFeatures,
            } as GeoJSONFeatureCollection,
            clusterLookup: lookup,
            lineFeatureCollection: {
                type: "FeatureCollection",
                features: lines,
            } as GeoJSONFeatureCollection,
            pointFeatureCollection: {
                type: "FeatureCollection",
                features: points,
            } as GeoJSONFeatureCollection,
        };
    }, [projects]);

    const activeTileUrl = useTileUrl();
    const activeTileUrlRef = useRef(activeTileUrl);
    activeTileUrlRef.current = activeTileUrl;

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
                        tiles: [activeTileUrlRef.current ?? tileLayerUrl],
                        tileSize: 256,
                        attribution: tileAttribution,
                    },
                    constituencies: {
                        type: "geojson",
                        data: { type: "FeatureCollection", features: [] },
                    },
                    "project-routes": {
                        type: "geojson",
                        data: { type: "FeatureCollection", features: [] },
                    },
                    "project-points": {
                        type: "geojson",
                        data: { type: "FeatureCollection", features: [] },
                    },
                    "project-point-clusters": {
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
                    // Below the project layers on purpose: the outlines are
                    // context, the projects are the subject.
                    {
                        id: "constituencies-fill",
                        type: "fill",
                        source: "constituencies",
                        paint: {
                            "fill-color": MAP_COLOR.constituency,
                            "fill-opacity": [
                                "case",
                                ["boolean", ["feature-state", "selected"], false],
                                0.22,
                                0.08,
                            ],
                        },
                    },
                    {
                        id: "constituencies-outline",
                        type: "line",
                        source: "constituencies",
                        paint: {
                            "line-color": MAP_COLOR.constituency,
                            "line-width": [
                                "case",
                                ["boolean", ["feature-state", "selected"], false],
                                2.5,
                                1,
                            ],
                            "line-opacity": 0.6,
                        },
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
                            "line-color": ["coalesce", ["get", "groupColor"], MAP_COLOR.default],
                            "line-width": [
                                "case",
                                ["boolean", ["feature-state", "hover"], false],
                                8,
                                4,
                            ],
                            // Projects sharing a track fan out from zoom 8 to 12 (B1).
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            "line-offset": lineOffsetExpression(4) as any,
                        },
                    },
                    {
                        id: "project-points-circle",
                        type: "circle",
                        source: "project-points",
                        paint: {
                            "circle-color": ["coalesce", ["get", "groupColor"], MAP_COLOR.default],
                            "circle-radius": [
                                "case",
                                ["boolean", ["feature-state", "hover"], false],
                                8,
                                5,
                            ],
                            "circle-stroke-width": 1.5,
                            "circle-stroke-color": MAP_COLOR.stroke,
                        },
                    },
                    // Station counters (D): several projects at one spot. The
                    // count is an HTML marker on top, in the design-system font.
                    {
                        id: "project-point-clusters-circle",
                        type: "circle",
                        source: "project-point-clusters",
                        paint: {
                            "circle-color": ["coalesce", ["get", "groupColor"], MAP_COLOR.default],
                            "circle-radius": [
                                "case",
                                ["boolean", ["feature-state", "hover"], false],
                                13,
                                10,
                            ],
                            "circle-stroke-width": 2,
                            "circle-stroke-color": MAP_COLOR.counterRim,
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

        // Single map-level mousemove over both project layers: every project
        // under the pointer is highlighted, not only the topmost one.
        const handleMouseMove = (event: maplibregl.MapMouseEvent) => {
            const ids = queryProjectIds(mapInstance, event.point, clustersRef.current);
            mapInstance.getCanvas().style.cursor = ids.length > 0 ? "pointer" : "";
            hoverIdsRef.current = applyHover(mapInstance, hoverIdsRef.current, ids, clustersRef.current);
        };

        // Clear hover when mouse leaves the map canvas entirely. Not when it
        // moves onto the popup: React fires the list entry's mouseenter before
        // this native mouseleave, and clearing here would drop that highlight.
        const handleMouseLeaveCanvas = (event: MouseEvent) => {
            mapInstance.getCanvas().style.cursor = "";
            const target = event.relatedTarget;
            if (target instanceof Node && overlayRef.current?.contains(target)) return;
            hoverIdsRef.current = applyHover(mapInstance, hoverIdsRef.current, [], clustersRef.current);
        };

        mapInstance.on("mousemove", handleMouseMove);
        mapInstance.getCanvas().addEventListener("mouseleave", handleMouseLeaveCanvas);

        return () => {
            mapInstance.getCanvas().style.cursor = "";
            mapInstance.getCanvas().removeEventListener("mouseleave", handleMouseLeaveCanvas);
            mapInstance.off("mousemove", handleMouseMove);
            mapInstance.remove();
        };
    }, [tileLayerUrl]);

    // Colour scheme changed: swap the basemap tiles in place (layers/state stay).
    useEffect(() => {
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance || !activeTileUrl) return;
        swapRasterTiles(mapInstance, "basemap", activeTileUrl);
    }, [activeTileUrl]);

    // Register click handlers separately so they re-run when `clickable` changes.
    // This is needed because `clickable` may start as false (data not yet loaded)
    // and become true later once sub-projects are available.
    useEffect(() => {
        if (!isMapReady) return undefined;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return undefined;
        if (!clickable) return undefined;

        // One handler for lines and points: a click collects every project at
        // the spot. One hit opens its summary, several open the list.
        const handleMapClick = (event: maplibregl.MapMouseEvent) => {
            const projects = queryProjectIds(mapInstance, event.point, clustersRef.current)
                .map((id) => projectsRef.current.find((p) => p.id === id))
                .filter((p): p is MapViewProject => p !== undefined);
            if (projects.length === 0) {
                setPopup(null);
                return;
            }
            const sorted = sortProjectsByName(projects);
            ignoreOutsideClickRef.current = true;
            setPopup({
                projects: sorted,
                selectedId: sorted.length === 1 ? sorted[0].id : null,
                x: event.point.x,
                y: event.point.y,
            });
        };

        mapInstance.on("click", handleMapClick);

        return () => {
            mapInstance.off("click", handleMapClick);
        };
    }, [isMapReady, clickable]);

    // Update the GeoJSON sources whenever project data changes
    useEffect(() => {
        if (!isMapReady) return;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        const lineSource = mapInstance.getSource("project-routes") as maplibregl.GeoJSONSource | undefined;
        const pointSource = mapInstance.getSource("project-points") as maplibregl.GeoJSONSource | undefined;
        const clusterSource = mapInstance.getSource("project-point-clusters") as
            | maplibregl.GeoJSONSource
            | undefined;
        // Counter ids are only valid for one grouping: drop the hover before
        // they change meaning; the next pointer move sets it again.
        hoverIdsRef.current = applyHover(mapInstance, hoverIdsRef.current, [], clustersRef.current);
        clustersRef.current = clusterLookup;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (lineSource) lineSource.setData(lineFeatureCollection as any);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (pointSource) pointSource.setData(pointFeatureCollection as any);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (clusterSource) clusterSource.setData(clusterFeatureCollection as any);

        // Fit once, on the first data that has coordinates; later updates (e.g. a
        // refetch) must not yank the view away from where the user has panned.
        if (fitToProjects && !hasFittedRef.current) {
            const bounds = featureBounds([lineFeatureCollection, pointFeatureCollection, clusterFeatureCollection]);
            if (bounds) {
                mapInstance.fitBounds(bounds, { padding: 40, maxZoom: 13, duration: 0 });
                hasFittedRef.current = true;
            }
        }
    }, [lineFeatureCollection, pointFeatureCollection, clusterFeatureCollection, clusterLookup, isMapReady, fitToProjects]);

    // The count of each station counter as an HTML marker: map text would need
    // glyph files, a marker uses the design-system font. Clicks and hover pass
    // through to the circle underneath.
    useEffect(() => {
        if (!isMapReady) return undefined;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return undefined;
        const markers = clusterFeatureCollection.features.map((feature) => {
            const element = document.createElement("span");
            element.className = "idt-map-counter";
            element.textContent = String(feature.properties.count);
            element.style.color = String(feature.properties.textColor);
            return new maplibregl.Marker({ element, anchor: "center" })
                .setLngLat(feature.geometry?.coordinates as [number, number])
                .addTo(mapInstance);
        });
        return () => {
            for (const marker of markers) marker.remove();
        };
    }, [clusterFeatureCollection, isMapReady]);

    // Constituency layer: data, visibility and the selected outline.
    useEffect(() => {
        if (!isMapReady) return;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        const source = mapInstance.getSource("constituencies") as
            | maplibregl.GeoJSONSource
            | undefined;
        const data = constituencies ?? { type: "FeatureCollection" as const, features: [] };
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (source) source.setData(data as any);
        const visibility = constituencies ? "visible" : "none";
        for (const layer of ["constituencies-fill", "constituencies-outline"]) {
            mapInstance.setLayoutProperty(layer, "visibility", visibility);
        }
    }, [constituencies, isMapReady]);

    const previousConstituencyRef = useRef<number | null>(null);
    useEffect(() => {
        if (!isMapReady) return;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        if (previousConstituencyRef.current !== null) {
            mapInstance.setFeatureState(
                { source: "constituencies", id: previousConstituencyRef.current },
                { selected: false },
            );
        }
        if (selectedConstituencyId !== null) {
            mapInstance.setFeatureState(
                { source: "constituencies", id: selectedConstituencyId },
                { selected: true },
            );
        }
        previousConstituencyRef.current = selectedConstituencyId;
    }, [selectedConstituencyId, isMapReady, constituencies]);

    // Clicking an outline selects the constituency — the third entry point.
    useEffect(() => {
        if (!isMapReady || !onConstituencySelect) return undefined;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return undefined;

        const handleClick = (event: maplibregl.MapMouseEvent) => {
            // A project click wins: the outline is context, not the subject.
            if (queryProjectIds(mapInstance, event.point, clustersRef.current).length > 0) return;

            const hits = mapInstance.queryRenderedFeatures(event.point, {
                layers: ["constituencies-fill"],
            });
            const properties = hits[0]?.properties;
            if (!isRecord(properties)) {
                onConstituencySelect(null);
                return;
            }
            const value = Number(properties.constituency_id);
            onConstituencySelect(Number.isFinite(value) ? value : null);
        };

        mapInstance.on("click", handleClick);
        return () => {
            mapInstance.off("click", handleClick);
        };
    }, [isMapReady, onConstituencySelect]);

    // Update line-width and the lane offset (it scales with the width) when the
    // slider changes
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
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        mapInstance.setPaintProperty("project-routes-line", "line-offset", lineOffsetExpression(lineWidth) as any);
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
        mapInstance.setPaintProperty("project-point-clusters-circle", "circle-radius", [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            pointSize + 8,
            pointSize + 5,
        ]);
    }, [pointSize, isMapReady]);

    // A closed popup leaves no list highlight behind.
    useEffect(() => {
        if (popup === null) setHover([]);
    }, [popup]);

    useEffect(() => {
        if (!popup) return undefined;

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                setPopup(null);
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
            setPopup(null);
        };

        window.addEventListener("keydown", handleKeyDown);
        document.addEventListener("mousedown", handleOutsideClick);

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            document.removeEventListener("mousedown", handleOutsideClick);
        };
    }, [popup]);

    // Clamp popup within the map container so it's never cut off at the edges.
    // useLayoutEffect runs synchronously after DOM layout but before browser paint,
    // so there's no visible flash.
    useLayoutEffect(() => {
        if (!popup || !overlayRef.current || !mapContainerRef.current) return;

        const overlay = overlayRef.current;
        const container = mapContainerRef.current;

        // Reset to default (above the click point, centered) so getBoundingClientRect
        // reflects the natural position we're correcting from.
        overlay.style.transform = "translate(-50%, calc(-100% - 12px))";

        const overlayRect = overlay.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const padding = 8;

        // Horizontal correction: shift left/right if the popup overflows the container.
        let dx = 0;
        if (overlayRect.right > containerRect.right - padding) {
            dx = containerRect.right - padding - overlayRect.right;
        } else if (overlayRect.left < containerRect.left + padding) {
            dx = containerRect.left + padding - overlayRect.left;
        }

        // Vertical correction: if the popup overflows the top, flip it below the click point.
        const flipBelow = overlayRect.top < containerRect.top + padding;

        overlay.style.transform = flipBelow
            ? `translate(calc(-50% + ${dx}px), 12px)`
            : `translate(calc(-50% + ${dx}px), calc(-100% - 12px))`;
    }, [popup]);

    if (!tileLayerUrl) {
        return (
            <div
                style={{
                    height: typeof height === "number" ? `${height}px` : height,
                    backgroundColor: "var(--surface-sunken)",
                    color: "var(--text-body)",
                    border: "2px solid var(--border-frame)",
                    borderRadius: 0,
                    boxSizing: "border-box",
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
        <div
            style={{
                height: typeof height === "number" ? `${height}px` : height,
                position: "relative",
                // The map sits "im Rahmen" (feature-idt-design.md → Karte).
                border: "2px solid var(--border-frame)",
                boxSizing: "border-box",
            }}
        >
            <div ref={mapContainerRef} style={{ height: "100%" }} />
            {popup && (
                <div
                    ref={overlayRef}
                    style={{
                        position: "absolute",
                        left: popup.x,
                        top: popup.y,
                        transform: "translate(-50%, calc(-100% - 12px))",
                        // Never wider than the screen it has to fit on.
                        minWidth: "min(260px, calc(100vw - 32px))",
                        maxWidth: "min(340px, calc(100vw - 32px))",
                        zIndex: 10,
                        background: "var(--surface)",
                        color: "var(--text-body)",
                        border: "2px solid var(--border-frame)",
                        borderRadius: 0,
                        padding: "16px",
                    }}
                >
                    {selectedProject ? (
                        <Stack gap="sm">
                            {popup.projects.length > 1 && (
                                <Button
                                    variant="subtle"
                                    size="compact-sm"
                                    style={{ alignSelf: "flex-start" }}
                                    onClick={() => {
                                        setHover([]);
                                        setPopup({ ...popup, selectedId: null });
                                    }}
                                >
                                    ← Alle {popup.projects.length} Projekte
                                </Button>
                            )}
                            <ProjectSummaryCard project={selectedProject} />
                            <Button
                                onClick={() => {
                                    const groupParam = searchParams.get("group");
                                    navigate(`/projects/${selectedProject.id}${groupParam ? `?group=${groupParam}` : ""}`);
                                    setPopup(null);
                                }}
                                fullWidth
                            >
                                Auswählen
                            </Button>
                        </Stack>
                    ) : (
                        <MapOverlapList
                            projects={popup.projects}
                            onHighlight={(projectId) => setHover(projectId === null ? [] : [projectId])}
                            onSelect={(projectId) => {
                                setHover([projectId]);
                                setPopup({ ...popup, selectedId: projectId });
                            }}
                        />
                    )}
                </div>
            )}
        </div>
    );
}
