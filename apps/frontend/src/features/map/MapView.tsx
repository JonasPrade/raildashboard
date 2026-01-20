import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { useQueries } from "@tanstack/react-query";

import { getProjectRoutesQueryOptions } from "../../shared/api/queries";

const tileLayerUrl = import.meta.env.REACT_APP_TILE_LAYER_URL as string | undefined;
const tileAttribution =
    'Kartenhintergrund: <a href="https://www.bkg.bund.de" target="_blank" rel="noopener noreferrer">Bundesamt für Kartographie und Geodäsie</a>';

type MapViewProject = {
    id: number;
    name: string;
    groupColor?: string;
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

const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === "object" && value !== null;

const isFeatureCollection = (value: unknown): value is { type: "FeatureCollection"; features: unknown[] } =>
    isRecord(value) && value.type === "FeatureCollection" && Array.isArray(value.features);

const isFeature = (value: unknown): value is { type: "Feature"; geometry: unknown; properties?: unknown } =>
    isRecord(value) && value.type === "Feature" && "geometry" in value;

const isGeometry = (value: unknown): value is GeoJSONGeometry =>
    isRecord(value) && typeof value.type === "string" && "coordinates" in value;

const createFeaturesFromGeoJson = (
    geojson: unknown,
    baseProperties: Record<string, unknown>,
    idPrefix: string,
): GeoJSONFeature[] => {
    if (isFeatureCollection(geojson)) {
        return geojson.features
            .map((feature, index) => {
                if (!isFeature(feature)) return null;
                const properties = isRecord(feature.properties)
                    ? { ...feature.properties, ...baseProperties }
                    : baseProperties;
                return {
                    ...feature,
                    id: feature.id ?? `${idPrefix}-collection-${index}`,
                    type: "Feature",
                    geometry: isGeometry(feature.geometry) ? feature.geometry : null,
                    properties,
                };
            })
            .filter((feature): feature is GeoJSONFeature => Boolean(feature));
    }

    if (isFeature(geojson)) {
        return [
            {
                ...geojson,
                id: geojson.id ?? `${idPrefix}-feature`,
                type: "Feature",
                geometry: isGeometry(geojson.geometry) ? geojson.geometry : null,
                properties: isRecord(geojson.properties)
                    ? { ...geojson.properties, ...baseProperties }
                    : baseProperties,
            },
        ];
    }

    if (isGeometry(geojson)) {
        return [
            {
                id: `${idPrefix}-geometry`,
                type: "Feature",
                geometry: geojson,
                properties: baseProperties,
            },
        ];
    }

    return [];
};

type Props = {
    projects: MapViewProject[];
};

export default function MapView({ projects }: Props) {
    const mapContainerRef = useRef<HTMLDivElement | null>(null);
    const mapInstanceRef = useRef<maplibregl.Map | null>(null);
    const hoverFeatureIdRef = useRef<string | number | null>(null);
    const [isMapReady, setIsMapReady] = useState(false);

    const routeQueries = useQueries({
        queries: projects.map((project) => getProjectRoutesQueryOptions(project.id)),
    });

    const featureCollection = useMemo<GeoJSONFeatureCollection>(() => {
        const features = routeQueries.flatMap((query, index) => {
            const project = projects[index];
            if (!project || !query.data) return [];
            return query.data.flatMap((route, routeIndex) =>
                createFeaturesFromGeoJson(
                    route.geom_geojson,
                    {
                        projectId: project.id,
                        name: project.name,
                        groupColor: project.groupColor,
                        routeId: route.route_id,
                    },
                    `${project.id}-${route.route_id ?? routeIndex}`,
                ),
            );
        });

        return {
            type: "FeatureCollection",
            features,
        };
    }, [projects, routeQueries]);

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
                        data: {
                            type: "FeatureCollection",
                            features: [],
                        },
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
                        paint: {
                            "line-color": ["coalesce", ["get", "groupColor"], "#2563eb"],
                            "line-width": [
                                "case",
                                ["boolean", ["feature-state", "hover"], false],
                                6,
                                2,
                            ],
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

        mapInstance.on("mousemove", "project-routes-line", (event) => {
            const feature = event.features?.[0];
            if (!feature || feature.id === undefined || feature.id === null) {
                return;
            }

            mapInstance.getCanvas().style.cursor = "pointer";

            if (hoverFeatureIdRef.current !== null && hoverFeatureIdRef.current !== feature.id) {
                mapInstance.setFeatureState(
                    { source: "project-routes", id: hoverFeatureIdRef.current },
                    { hover: false },
                );
            }

            hoverFeatureIdRef.current = feature.id;
            mapInstance.setFeatureState(
                { source: "project-routes", id: feature.id },
                { hover: true },
            );
        });

        mapInstance.on("mouseleave", "project-routes-line", () => {
            mapInstance.getCanvas().style.cursor = "";
            if (hoverFeatureIdRef.current !== null) {
                mapInstance.setFeatureState(
                    { source: "project-routes", id: hoverFeatureIdRef.current },
                    { hover: false },
                );
                hoverFeatureIdRef.current = null;
            }
        });

        return () => {
            mapInstance.getCanvas().style.cursor = "";
            mapInstance.remove();
        };
    }, [tileLayerUrl]);

    useEffect(() => {
        if (!isMapReady) return;
        const mapInstance = mapInstanceRef.current;
        if (!mapInstance) return;
        const source = mapInstance.getSource("project-routes") as maplibregl.GeoJSONSource | undefined;
        if (!source) return;
        source.setData(featureCollection);
    }, [featureCollection, isMapReady]);

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

    return <div ref={mapContainerRef} style={{ height: "800px" }} />;
}
