/**
 * Where a stored line came from, and how a calculated route becomes stored lines.
 * Mirror of `services/routing_networks.py` in the backend (keep both in step):
 *
 * - routed lines: `geometry_source: "routing"` + `track_status` (existing / construction /
 *   proposed, from the OSM lifecycle tags GraphHopper knows) + `railway_class` (rail,
 *   light_rail, subway, tram, narrow_gauge, unknown),
 * - hand-drawn or hand-edited lines: `geometry_source: "manual"`,
 * - uploaded lines: `geometry_source: "upload"`,
 * - lines saved before origins were recorded: no `geometry_source` → "unknown".
 */
import type { RouteNetworks, RouteSection, TrackClass, TrackStatus } from "../../shared/api/queries";
import { computeGeojsonLengthKm } from "../../shared/geo/length";

export type GeometryOrigin =
    | "routing_existing"
    | "routing_construction"
    | "routing_proposed"
    | "manual"
    | "upload"
    | "unknown";

export const NO_EXTRA_NETWORKS: RouteNetworks = { construction: false, proposed: false, track_classes: ["rail"] };

export const TRACK_CLASS_LABEL: Record<TrackClass, string> = {
    rail: "Vollbahn",
    light_rail: "S-Bahn/Stadtbahn",
    subway: "U-Bahn",
    tram: "Straßenbahn",
    narrow_gauge: "Schmalspur",
    unknown: "Gleisart unbekannt",
};

const TRACK_CLASSES = Object.keys(TRACK_CLASS_LABEL) as TrackClass[];
/** Classes that are exclusive to rail (Vollbahn); unknown combines with anything. */
const URBAN_CLASSES: TrackClass[] = ["light_rail", "subway", "tram", "narrow_gauge"];

/**
 * Toggle a track class in the selection, keeping it valid (decision EK-2026-355):
 * ticking an urban class drops rail, ticking rail drops the urban classes. Unticking
 * the last main class falls back to rail.
 */
export function toggleTrackClass(current: TrackClass[], cls: TrackClass, on: boolean): TrackClass[] {
    let next = on ? [...new Set([...current, cls])] : current.filter((c) => c !== cls);
    if (on && URBAN_CLASSES.includes(cls)) next = next.filter((c) => c !== "rail");
    if (on && cls === "rail") next = next.filter((c) => !URBAN_CLASSES.includes(c));
    if (!next.some((c) => c !== "unknown")) next = [...next, "rail"];
    return TRACK_CLASSES.filter((c) => next.includes(c));
}

/** Track class of a stored line; "none" when not recorded (not assumed to be rail). */
export function featureClass(feature: { properties?: unknown } | null | undefined): TrackClass | "none" {
    const value = ((feature?.properties ?? {}) as Record<string, unknown>).railway_class;
    return typeof value === "string" && (TRACK_CLASSES as string[]).includes(value) ? (value as TrackClass) : "none";
}

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
    const runs: Array<Pick<RouteSection, "track_status" | "railway_class" | "from_index" | "to_index">> =
        sections && sections.length > 0
            ? sections
            : [{ track_status: "existing", railway_class: "rail", from_index: 0, to_index: coordinates.length - 1 }];
    return runs
        .map((s) => coordinates.slice(s.from_index, s.to_index + 1).map((c) => [...c]))
        .map((part, i) => ({ part, status: runs[i].track_status, cls: runs[i].railway_class ?? "rail" }))
        .filter(({ part }) => part.length >= 2)
        .map(({ part, status, cls }) => ({
            type: "Feature" as const,
            geometry: { type: "LineString" as const, coordinates: part },
            properties: { geometry_source: "routing", track_status: status, railway_class: cls },
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

/** Line length per track class of the stored lines ("none" = not recorded). */
export function lineKmByClass(features: GeoJSON.Feature[]): Array<{ cls: TrackClass | "none"; km: number }> {
    const totals = new Map<TrackClass | "none", number>();
    for (const f of features) {
        const type = f?.geometry?.type;
        if (type !== "LineString" && type !== "MultiLineString") continue;
        const km = computeGeojsonLengthKm(JSON.stringify(f.geometry)) ?? 0;
        const cls = featureClass(f);
        totals.set(cls, (totals.get(cls) ?? 0) + km);
    }
    return ([...TRACK_CLASSES, "none"] as Array<TrackClass | "none">)
        .filter((cls) => totals.has(cls))
        .map((cls) => ({ cls, km: Math.round((totals.get(cls) ?? 0) * 10) / 10 }));
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
