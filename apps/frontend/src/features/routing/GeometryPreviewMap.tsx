import { useEffect, useLayoutEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import {
    TerraDraw,
    TerraDrawLineStringMode,
    TerraDrawPointMode,
    TerraDrawSelectMode,
} from "terra-draw";
import { TerraDrawMapLibreGLAdapter } from "terra-draw-maplibre-gl-adapter";
import type { OperationalPointRef, RoutePreviewFeature } from "../../shared/api/queries";

const tileLayerUrl = import.meta.env.REACT_APP_TILE_LAYER_URL as string | undefined;

/** Active hand-drawing mode (null = off, terra-draw sits in its neutral "static" mode). */
export type DrawMode = "line" | "point" | "select" | null;

/** Map our UI draw-mode names onto terra-draw's internal mode identifiers. */
const TERRA_MODE: Record<NonNullable<DrawMode>, string> = {
    line: "linestring",
    point: "point",
    select: "select",
};

type Props = {
    /** Existing project geojson_representation (JSON string). Shown as solid blue line/circles. */
    existingGeojson: string | null;
    /** Calculated route preview. Shown as dashed orange line. */
    previewFeature: RoutePreviewFeature | null;
    /** Whether to render the existing geometry (toggled off when user wants to delete it). */
    showExisting: boolean;
    /** Newly selected operational points to preview as orange circles. */
    previewPoints?: OperationalPointRef[];
    /**
     * Selection mode: when active, existing features become clickable and selected
     * ones are highlighted in red. Modal uses this for the "delete individual features" flow.
     */
    selectionMode?: boolean;
    /** Indices of currently selected existing features (matches `__idx` on each feature). */
    selectedIndices?: Set<number>;
    /** Fired with the clicked feature's __idx when selectionMode is on. */
    onFeatureClick?: (idx: number) => void;
    /**
     * Active hand-drawing mode. terra-draw owns its own layers/sources on top of the map;
     * `null` parks it in the neutral "static" mode so the existing selection-mode click
     * handlers keep working untouched.
     */
    drawMode?: DrawMode;
    /**
     * Controlled set of hand-drawn features (LineString/Point only). The parent mirrors
     * terra-draw's internal store via `onDrawnFeaturesChange`; setting it back to `[]`
     * (after a save or "reset") clears the terra-draw store.
     */
    drawnFeatures?: GeoJSON.Feature[];
    /** Fired on every terra-draw snapshot change with the current hand-drawn line/point features. */
    onDrawnFeaturesChange?: (features: GeoJSON.Feature[]) => void;
    height?: number;
};

function parseGeojson(raw: string | null): unknown {
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
}

function extractLineCoords(geojson: unknown): number[][][] {
    if (!geojson || typeof geojson !== "object") return [];
    const g = geojson as Record<string, unknown>;
    if (g.type === "FeatureCollection" && Array.isArray(g.features)) {
        return (g.features as unknown[]).flatMap(extractLineCoords);
    }
    if (g.type === "Feature") return extractLineCoords(g.geometry);
    if (g.type === "LineString" && Array.isArray(g.coordinates)) return [g.coordinates as number[][]];
    if (g.type === "MultiLineString" && Array.isArray(g.coordinates)) return g.coordinates as number[][][];
    return [];
}

function buildLineFeatureCollection(coords: number[][][]) {
    return {
        type: "FeatureCollection" as const,
        features: coords.map((c) => ({
            type: "Feature" as const,
            geometry: { type: "LineString" as const, coordinates: c },
            properties: {} as Record<string, never>,
        })),
    };
}

function extractPointCoords(geojson: unknown): Array<[number, number]> {
    if (!geojson || typeof geojson !== "object") return [];
    const g = geojson as Record<string, unknown>;
    if (g.type === "FeatureCollection" && Array.isArray(g.features)) {
        return (g.features as unknown[]).flatMap(extractPointCoords);
    }
    if (g.type === "Feature") return extractPointCoords(g.geometry);
    if (g.type === "Point" && Array.isArray(g.coordinates)) return [g.coordinates as [number, number]];
    return [];
}

function buildPointFeatureCollection(coords: Array<[number, number]>) {
    return {
        type: "FeatureCollection" as const,
        features: coords.map(([lon, lat]) => ({
            type: "Feature" as const,
            geometry: { type: "Point" as const, coordinates: [lon, lat] },
            properties: {} as Record<string, never>,
        })),
    };
}

/**
 * Parse the existing geojson_representation and split into a line FC and a point FC,
 * each feature stamped with `__idx` (matching the index in the original FeatureCollection)
 * and `__selected` (looked up from `selectedIndices`). Used in selection mode so the map
 * can fire click events that identify a single feature for deletion.
 *
 * Indexing follows the order features appear in the parent FeatureCollection. If the input
 * is a bare Feature or Geometry it's treated as index 0.
 */
function splitIndexedFC(raw: string | null, selected: Set<number>) {
    const emptyFC = { type: "FeatureCollection" as const, features: [] as GeoJSON.Feature[] };
    if (!raw) return { lines: emptyFC, points: emptyFC };

    let parsed: unknown;
    try { parsed = JSON.parse(raw); } catch { return { lines: emptyFC, points: emptyFC }; }

    const rawFeatures: GeoJSON.Feature[] = [];
    const root = parsed as Record<string, unknown> | null;
    if (root && root.type === "FeatureCollection" && Array.isArray(root.features)) {
        rawFeatures.push(...(root.features as GeoJSON.Feature[]));
    } else if (root && root.type === "Feature") {
        rawFeatures.push(root as unknown as GeoJSON.Feature);
    } else if (root && typeof root.type === "string") {
        rawFeatures.push({ type: "Feature", geometry: root as unknown as GeoJSON.Geometry, properties: {} });
    }

    const lines: GeoJSON.Feature[] = [];
    const points: GeoJSON.Feature[] = [];
    rawFeatures.forEach((f, idx) => {
        const stamped: GeoJSON.Feature = {
            ...f,
            properties: {
                ...(f.properties ?? {}),
                __idx: idx,
                __selected: selected.has(idx),
            },
        };
        const gtype = f.geometry?.type;
        if (gtype === "LineString" || gtype === "MultiLineString") lines.push(stamped);
        else if (gtype === "Point" || gtype === "MultiPoint") points.push(stamped);
    });

    return {
        lines: { type: "FeatureCollection" as const, features: lines },
        points: { type: "FeatureCollection" as const, features: points },
    };
}

export default function GeometryPreviewMap({ existingGeojson, previewFeature, showExisting, previewPoints = [], selectionMode = false, selectedIndices, onFeatureClick, drawMode = null, drawnFeatures = [], onDrawnFeaturesChange, height = 500 }: Props) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const mapRef = useRef<maplibregl.Map | null>(null);
    const drawRef = useRef<TerraDraw | null>(null);
    const [isReady, setIsReady] = useState(false);
    // Refs so the click handler (registered once on load) always sees the latest values.
    const selectionModeRef = useRef(selectionMode);
    const onFeatureClickRef = useRef(onFeatureClick);
    const onDrawnFeaturesChangeRef = useRef(onDrawnFeaturesChange);
    selectionModeRef.current = selectionMode;
    onFeatureClickRef.current = onFeatureClick;
    onDrawnFeaturesChangeRef.current = onDrawnFeaturesChange;

    // Init map once
    useLayoutEffect(() => {
        if (!containerRef.current || !tileLayerUrl) return;

        // In selection mode, existing features colour by feature property `__selected`.
        // The expression resolves to blue/red statically when not in mode (no __selected
        // property → false branch → blue), so it's safe to use always.
        const selectionLineColor: maplibregl.ExpressionSpecification = ["case", ["==", ["get", "__selected"], true], "#dc2626", "#2563eb"];
        const selectionCircleColor: maplibregl.ExpressionSpecification = ["case", ["==", ["get", "__selected"], true], "#dc2626", "#2563eb"];

        const map = new maplibregl.Map({
            container: containerRef.current,
            style: {
                version: 8,
                sources: {
                    basemap: { type: "raster", tiles: [tileLayerUrl], tileSize: 256 },
                    existing: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
                    preview: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
                    "existing-points": { type: "geojson", data: { type: "FeatureCollection", features: [] } },
                    "preview-points": { type: "geojson", data: { type: "FeatureCollection", features: [] } },
                },
                layers: [
                    { id: "basemap", type: "raster", source: "basemap" },
                    {
                        id: "existing-line",
                        type: "line",
                        source: "existing",
                        layout: { "line-cap": "round", "line-join": "round" },
                        paint: { "line-color": selectionLineColor, "line-width": 4 },
                    },
                    {
                        id: "preview-line",
                        type: "line",
                        source: "preview",
                        layout: { "line-cap": "round", "line-join": "round" },
                        paint: {
                            "line-color": "#ea580c",
                            "line-width": 4,
                            "line-dasharray": [6, 3],
                        },
                    },
                    {
                        id: "existing-points-circle",
                        type: "circle",
                        source: "existing-points",
                        paint: { "circle-color": selectionCircleColor, "circle-radius": 7, "circle-stroke-width": 2, "circle-stroke-color": "#fff" },
                    },
                    {
                        id: "preview-points-circle",
                        type: "circle",
                        source: "preview-points",
                        paint: { "circle-color": "#ea580c", "circle-radius": 7, "circle-stroke-width": 2, "circle-stroke-color": "#fff" },
                    },
                ],
            },
            center: [10.0, 51.0],
            zoom: 5,
        });
        mapRef.current = map;
        map.on("load", () => {
            // terra-draw manages its own sources/layers on top of the existing ones.
            // Created after load so the style is ready; parked in "static" until a draw
            // mode is selected, which keeps the selection-mode click handlers below intact.
            const draw = new TerraDraw({
                adapter: new TerraDrawMapLibreGLAdapter({ map }),
                modes: [
                    new TerraDrawLineStringMode(),
                    new TerraDrawPointMode(),
                    new TerraDrawSelectMode({
                        flags: {
                            linestring: {
                                feature: {
                                    draggable: true,
                                    coordinates: { midpoints: true, draggable: true, deletable: true },
                                },
                            },
                            point: { feature: { draggable: true } },
                        },
                    }),
                ],
            });
            const emitDrawn = () => {
                const drawn = draw
                    .getSnapshot()
                    .filter((f) => f.properties?.mode === "linestring" || f.properties?.mode === "point")
                    .map((f) => ({ type: "Feature" as const, geometry: f.geometry, properties: {} }));
                onDrawnFeaturesChangeRef.current?.(drawn as GeoJSON.Feature[]);
            };
            draw.start();
            draw.setMode("static");
            draw.on("change", emitDrawn);
            draw.on("finish", emitDrawn);
            drawRef.current = draw;
            setIsReady(true);
        });

        // Click handler — only acts when parent is in selection mode and a __idx is present.
        const handleClick = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
            if (!selectionModeRef.current || !onFeatureClickRef.current) return;
            const f = e.features?.[0];
            const idx = f?.properties?.__idx;
            if (typeof idx === "number") onFeatureClickRef.current(idx);
        };
        map.on("click", "existing-line", handleClick);
        map.on("click", "existing-points-circle", handleClick);

        // Pointer cursor on hover when in selection mode.
        const enterCursor = () => { if (selectionModeRef.current) map.getCanvas().style.cursor = "pointer"; };
        const leaveCursor = () => { if (selectionModeRef.current) map.getCanvas().style.cursor = ""; };
        map.on("mouseenter", "existing-line", enterCursor);
        map.on("mouseleave", "existing-line", leaveCursor);
        map.on("mouseenter", "existing-points-circle", enterCursor);
        map.on("mouseleave", "existing-points-circle", leaveCursor);

        return () => {
            // Tear terra-draw down before the map so its adapter still has a live map.
            if (drawRef.current) {
                try { drawRef.current.stop(); } catch { /* map may already be torn down */ }
                drawRef.current = null;
            }
            map.remove();
            mapRef.current = null;
            setIsReady(false);
        };
    }, []);

    // Switch terra-draw mode when the parent changes drawMode (null → neutral "static").
    useEffect(() => {
        const draw = drawRef.current;
        if (!isReady || !draw) return;
        draw.setMode(drawMode === null ? "static" : TERRA_MODE[drawMode]);
    }, [drawMode, isReady]);

    // Controlled reset: when the parent clears drawnFeatures (after save / "Zurücksetzen"),
    // flush terra-draw's internal store. Guarded so we only clear when something is there.
    useEffect(() => {
        const draw = drawRef.current;
        if (!isReady || !draw) return;
        if (drawnFeatures.length === 0) {
            const hasDrawn = draw
                .getSnapshot()
                .some((f) => f.properties?.mode === "linestring" || f.properties?.mode === "point");
            if (hasDrawn) draw.clear();
        }
    }, [drawnFeatures, isReady]);

    // Update existing layer + fit bounds
    useEffect(() => {
        const map = mapRef.current;
        if (!isReady || !map) return;

        let lineFC: GeoJSON.FeatureCollection;
        let pointFC: GeoJSON.FeatureCollection;
        let lineCoordsForFit: number[][][];
        let pointCoordsForFit: Array<[number, number]>;

        if (!showExisting) {
            lineFC = { type: "FeatureCollection", features: [] };
            pointFC = { type: "FeatureCollection", features: [] };
            lineCoordsForFit = [];
            pointCoordsForFit = [];
        } else if (selectionMode) {
            // Preserve original features with __idx + __selected so clicks and highlighting work.
            const split = splitIndexedFC(existingGeojson, selectedIndices ?? new Set());
            lineFC = split.lines as GeoJSON.FeatureCollection;
            pointFC = split.points as GeoJSON.FeatureCollection;
            lineCoordsForFit = extractLineCoords(JSON.parse(existingGeojson ?? "null"));
            pointCoordsForFit = extractPointCoords(JSON.parse(existingGeojson ?? "null"));
        } else {
            const parsed = parseGeojson(existingGeojson);
            lineCoordsForFit = extractLineCoords(parsed);
            pointCoordsForFit = extractPointCoords(parsed);
            lineFC = buildLineFeatureCollection(lineCoordsForFit) as unknown as GeoJSON.FeatureCollection;
            pointFC = buildPointFeatureCollection(pointCoordsForFit) as unknown as GeoJSON.FeatureCollection;
        }

        (map.getSource("existing") as maplibregl.GeoJSONSource)?.setData(lineFC);
        (map.getSource("existing-points") as maplibregl.GeoJSONSource)?.setData(pointFC);

        const allLineCoords = [
            ...lineCoordsForFit,
            ...(previewFeature ? extractLineCoords(previewFeature) : []),
        ].flat();
        const allPointCoords = [...pointCoordsForFit, ...previewPoints.filter(op => op.latitude != null && op.longitude != null).map(op => [op.longitude!, op.latitude!] as [number, number])];
        const allCoords = [...allLineCoords, ...allPointCoords];
        if (allCoords.length > 0) {
            const lngs = allCoords.map(([lng]) => lng);
            const lats = allCoords.map(([, lat]) => lat);
            map.fitBounds(
                [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
                { padding: 60, maxZoom: 14 },
            );
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [existingGeojson, showExisting, isReady, selectionMode, selectedIndices]);

    // Update preview line + point layers
    useEffect(() => {
        const map = mapRef.current;
        if (!isReady || !map) return;

        const lineCoords = previewFeature ? extractLineCoords(previewFeature) : [];
        const pointCoords = previewPoints
            .filter((op) => op.latitude != null && op.longitude != null)
            .map((op) => [op.longitude!, op.latitude!] as [number, number]);

        (map.getSource("preview") as maplibregl.GeoJSONSource)?.setData(buildLineFeatureCollection(lineCoords) as unknown as GeoJSON.FeatureCollection);
        (map.getSource("preview-points") as maplibregl.GeoJSONSource)?.setData(buildPointFeatureCollection(pointCoords) as unknown as GeoJSON.FeatureCollection);

        const allLineCoords = [
            ...extractLineCoords(showExisting ? parseGeojson(existingGeojson) : null),
            ...lineCoords,
        ].flat();
        const allCoords = [...allLineCoords, ...pointCoords];
        if (allCoords.length > 0) {
            const lngs = allCoords.map(([lng]) => lng);
            const lats = allCoords.map(([, lat]) => lat);
            map.fitBounds(
                [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
                { padding: 60, maxZoom: 14 },
            );
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [previewFeature, previewPoints, isReady]);

    return <div ref={containerRef} style={{ width: "100%", height: height ?? "100%" }} />;
}
