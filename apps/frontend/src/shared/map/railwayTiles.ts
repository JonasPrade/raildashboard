import type maplibregl from "maplibre-gl";

/**
 * Railway network as a raster overlay behind the project geometries.
 *
 * Source: OpenRailwayMap (OpenStreetMap data). The public tiles are meant for
 * moderate use — a deployment with heavy traffic points
 * REACT_APP_RAILWAY_TILE_LAYER_URL at its own tile server instead. Setting that
 * variable to "off" removes the layer entirely, for deployments that must not
 * call an external tile source.
 */

export const RAILWAY_SOURCE_ID = "railway";
export const RAILWAY_LAYER_ID = "railway-raster";

export const RAILWAY_ATTRIBUTION =
    'Strecken: <a href="https://www.openrailwaymap.org/" target="_blank" rel="noopener noreferrer">OpenRailwayMap</a>, ' +
    'Daten © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap-Mitwirkende</a> (ODbL)';

const DEFAULT_RAILWAY_TILE_URLS = [
    "https://a.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
    "https://b.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
    "https://c.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
];

/** Opt-out value: Docker/CI turn an unset build arg into an empty string, so
 * "empty" cannot mean "disabled" — that needs a word of its own. */
const RAILWAY_TILES_OFF = "off";

/**
 * Tile URLs for the railway overlay.
 *
 * Unset or empty falls back to the OpenRailwayMap subdomains, the literal "off"
 * disables the layer, anything else is used as the tile URL template.
 */
export const resolveRailwayTileUrls = (configured: string | undefined): string[] => {
    const trimmed = configured?.trim() ?? "";
    if (trimmed.length === 0) return DEFAULT_RAILWAY_TILE_URLS;
    if (trimmed.toLowerCase() === RAILWAY_TILES_OFF) return [];
    return [trimmed];
};

export const railwayTileUrls = resolveRailwayTileUrls(
    import.meta.env.REACT_APP_RAILWAY_TILE_LAYER_URL as string | undefined,
);

/** False when the deployment disabled the overlay — layer and switch are then omitted. */
export const hasRailwayTiles = railwayTileUrls.length > 0;

export const railwaySourceSpec = (): maplibregl.RasterSourceSpecification => ({
    type: "raster",
    tiles: railwayTileUrls,
    tileSize: 256,
    attribution: RAILWAY_ATTRIBUTION,
});

export const railwayLayerSpec = (visible: boolean): maplibregl.RasterLayerSpecification => ({
    id: RAILWAY_LAYER_ID,
    type: "raster",
    source: RAILWAY_SOURCE_ID,
    layout: { visibility: visible ? "visible" : "none" },
    // Slightly muted so the network reads as context and the project colors stay dominant.
    paint: { "raster-opacity": 0.85 },
});

/**
 * Sources and layers to merge into a style definition. Empty when the overlay
 * is disabled, so both callers can spread the result unconditionally.
 */
export const railwayStyleParts = (
    visible: boolean,
): {
    sources: Record<string, maplibregl.RasterSourceSpecification>;
    layers: maplibregl.RasterLayerSpecification[];
} =>
    hasRailwayTiles
        ? {
              sources: { [RAILWAY_SOURCE_ID]: railwaySourceSpec() },
              layers: [railwayLayerSpec(visible)],
          }
        : { sources: {}, layers: [] };

/** Toggle the overlay. No-op when the layer is disabled or not on the map (yet). */
export const setRailwayVisibility = (map: maplibregl.Map, visible: boolean): void => {
    if (!hasRailwayTiles) return;
    if (!map.getLayer(RAILWAY_LAYER_ID)) return;
    map.setLayoutProperty(RAILWAY_LAYER_ID, "visibility", visible ? "visible" : "none");
};
