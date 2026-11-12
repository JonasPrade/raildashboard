/**
 * Where a stored line came from, and how a calculated route becomes stored lines.
 * Mirror of `services/routing_networks.py` in the backend (keep both in step):
 *
 * - routed lines: `geometry_source: "routing"` + `track_status` (existing / construction /
 *   proposed, from the OSM lifecycle tags GraphHopper knows),
 * - hand-drawn or hand-edited lines: `geometry_source: "manual"`,
 * - uploaded lines: `geometry_source: "upload"`,
 * - lines saved before origins were recorded: no `geometry_source` → "unknown".
 */
import type { RouteNetworks, RouteSection, TrackStatus } from "../../shared/api/queries";
import { computeGeojsonLengthKm } from "../../shared/geo/length";

export type GeometryOrigin =
    | "routing_existing"
    | "routing_construction"
    | "routing_proposed"
    | "manual"
    | "upload"
    | "unknown";

export const NO_EXTRA_NETWORKS: RouteNetworks = { construction: false, proposed: false };

export const TRACK_STATUS_LABEL: Record<TrackStatus, string> = {
    existing: "Bestandsnetz",
    construction: "OSM: im Bau",
    proposed: "OSM: geplant",
};

export const ORIGIN_LABEL: Record<GeometryOrigin, string> = {
    routing_existing: "Geroutet: Bestandsnetz",
    routing_construction: "Geroutet: OSM im Bau",
    routing_proposed: "Geroutet: OSM geplant",
    manual: "Von Hand",
    upload: "GeoJSON-Upload",
    unknown: "Ohne Herkunftsangabe",
};

const STATUSES: TrackStatus[] = ["existing", "construction", "proposed"];

function isTrackStatus(value: unknown): value is TrackStatus {
    return typeof value === "string" && (STATUSES as string[]).includes(value);
}

export function featureOrigin(feature: { properties?: unknown } | null | undefined): GeometryOrigin {
    const props = (feature?.properties ?? {}) as Record<string, unknown>;
    if (props.geometry_source === "routing") {
        return `routing_${isTrackStatus(props.track_status) ? props.track_status : "existing"}`;
    }
    if (props.geometry_source === "manual" || props.geometry_source === "upload") {
        return props.geometry_source;
    }
    return "unknown";
}

/**
 * The calculated route as stored features: one LineString per section, tagged with its
 * origin. A route entirely on existing track stays one feature. Without sections (older
 * backend) the whole line counts as existing track.
 */
export function routeLineFeatures(
    coordinates: number[][],
    sections: RouteSection[] | undefined,
): GeoJSON.Feature<GeoJSON.LineString>[] {
    const runs: Array<Pick<RouteSection, "track_status" | "from_index" | "to_index">> =
        sections && sections.length > 0
            ? sections
            : [{ track_status: "existing", from_index: 0, to_index: coordinates.length - 1 }];
    return runs
        .map((s) => coordinates.slice(s.from_index, s.to_index + 1).map((c) => [...c]))
        .map((part, i) => ({ part, status: runs[i].track_status }))
        .filter(({ part }) => part.length >= 2)
        .map(({ part, status }) => ({
            type: "Feature" as const,
            geometry: { type: "LineString" as const, coordinates: part },
            properties: { geometry_source: "routing", track_status: status },
        }));
}

/** Line length per origin, for the "Herkunft" summary of a project geometry. */
export function lineKmByOrigin(features: GeoJSON.Feature[]): Array<{ origin: GeometryOrigin; km: number }> {
    const totals = new Map<GeometryOrigin, number>();
    for (const f of features) {
        const type = f?.geometry?.type;
        if (type !== "LineString" && type !== "MultiLineString") continue;
        const km = computeGeojsonLengthKm(JSON.stringify(f.geometry)) ?? 0;
        const origin = featureOrigin(f);
        totals.set(origin, (totals.get(origin) ?? 0) + km);
    }
    return (Object.keys(ORIGIN_LABEL) as GeometryOrigin[])
        .filter((origin) => totals.has(origin))
        .map((origin) => ({ origin, km: Math.round((totals.get(origin) ?? 0) * 10) / 10 }));
}

/** Mark lines without an origin; used for uploads and hand drawing. */
export function withOrigin<T extends GeoJSON.Feature | object>(feature: T, source: "manual" | "upload"): T {
    const f = feature as GeoJSON.Feature;
    const type = f?.geometry?.type;
    if (type !== "LineString" && type !== "MultiLineString") return feature;
    const props = (f.properties ?? {}) as Record<string, unknown>;
    if (props.geometry_source) return feature;
    return { ...f, properties: { ...props, geometry_source: source } } as T;
}
