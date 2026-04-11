import { useEffect, useLayoutEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { RoutePreviewFeature } from "../../shared/api/queries";

const tileLayerUrl = import.meta.env.REACT_APP_TILE_LAYER_URL as string | undefined;

type Props = {
    /** Existing project geojson_representation (JSON string). Shown as solid blue line. */
    existingGeojson: string | null;
    /** Calculated route preview. Shown as dashed orange line. */
    previewFeature: RoutePreviewFeature | null;
    /** Whether to render the existing geometry (toggled off when user wants to delete it). */
    showExisting: boolean;
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

export default function GeometryPreviewMap({ existingGeojson, previewFeature, showExisting, height = 500 }: Props) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const mapRef = useRef<maplibregl.Map | null>(null);
    const [isReady, setIsReady] = useState(false);

    // Init map once
    useLayoutEffect(() => {
        if (!containerRef.current || !tileLayerUrl) return;

        const map = new maplibregl.Map({
            container: containerRef.current,
            style: {
                version: 8,
                sources: {
                    basemap: { type: "raster", tiles: [tileLayerUrl], tileSize: 256 },
                    existing: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
                    preview: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
                },
                layers: [
                    { id: "basemap", type: "raster", source: "basemap" },
                    {
                        id: "existing-line",
                        type: "line",
                        source: "existing",
                        layout: { "line-cap": "round", "line-join": "round" },
                        paint: { "line-color": "#2563eb", "line-width": 4 },
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
                ],
            },
            center: [10.0, 51.0],
            zoom: 5,
        });
        mapRef.current = map;
        map.on("load", () => { setIsReady(true); });

        return () => { map.remove(); mapRef.current = null; setIsReady(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Update existing layer + fit bounds
    useEffect(() => {
        const map = mapRef.current;
        if (!isReady || !map) return;

        const parsed = showExisting ? parseGeojson(existingGeojson) : null;
        const coords = extractLineCoords(parsed);
        (map.getSource("existing") as maplibregl.GeoJSONSource)?.setData(buildLineFeatureCollection(coords) as unknown as GeoJSON.FeatureCollection);

        const allCoords = [
            ...coords,
            ...(previewFeature ? extractLineCoords(previewFeature) : []),
        ].flat();
        if (allCoords.length > 0) {
            const lngs = allCoords.map(([lng]) => lng);
            const lats = allCoords.map(([, lat]) => lat);
            map.fitBounds(
                [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
                { padding: 60, maxZoom: 14 },
            );
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [existingGeojson, showExisting, isReady]);

    // Update preview layer
    useEffect(() => {
        const map = mapRef.current;
        if (!isReady || !map) return;

        const coords = previewFeature ? extractLineCoords(previewFeature) : [];
        (map.getSource("preview") as maplibregl.GeoJSONSource)?.setData(buildLineFeatureCollection(coords) as unknown as GeoJSON.FeatureCollection);

        if (coords.length > 0) {
            const allCoords = [
                ...extractLineCoords(showExisting ? parseGeojson(existingGeojson) : null),
                ...coords,
            ].flat();
            const lngs = allCoords.map(([lng]) => lng);
            const lats = allCoords.map(([, lat]) => lat);
            map.fitBounds(
                [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
                { padding: 60, maxZoom: 14 },
            );
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [previewFeature, isReady]);

    return <div ref={containerRef} style={{ width: "100%", height }} />;
}
