import { useComputedColorScheme } from "@mantine/core";
import type maplibregl from "maplibre-gl";

/** Light raster tile URL (build-time). Without it the maps show a placeholder. */
export const LIGHT_TILE_URL = (import.meta.env.REACT_APP_TILE_LAYER_URL as string | undefined) || undefined;
/** Optional dark raster tile URL (build-time); falls back to the light one. */
export const DARK_TILE_URL = (import.meta.env.REACT_APP_TILE_LAYER_URL_DARK as string | undefined) || undefined;

/** Pick the tile URL for a colour scheme; the dark one only if configured. */
export function selectTileUrl(
    scheme: "light" | "dark",
    light: string | undefined = LIGHT_TILE_URL,
    dark: string | undefined = DARK_TILE_URL,
): string | undefined {
    if (!light) return undefined;
    return scheme === "dark" && dark ? dark : light;
}

/** Tile URL matching the current colour scheme. */
export function useTileUrl(): string | undefined {
    const scheme = useComputedColorScheme("light");
    return selectTileUrl(scheme);
}

/** Swap the tiles of the raster source in place; layers and state stay intact. */
export function swapRasterTiles(map: maplibregl.Map, sourceId: string, url: string): void {
    const source = map.getSource(sourceId) as maplibregl.RasterTileSource | undefined;
    source?.setTiles([url]);
}
