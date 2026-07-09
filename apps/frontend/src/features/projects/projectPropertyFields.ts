/**
 * Single source of truth for the toggle/number project properties.
 *
 * The edit form sections, the form-value type and the update payload are all
 * derived from PROPERTY_SECTIONS — adding a project property means one entry
 * here plus the backend schema field, nothing else.
 */

export const PROPERTY_SECTIONS = [
    {
        label: "Verkehrsarten",
        fields: [
            { kind: "switch", label: "Fernverkehr", key: "effects_passenger_long_rail" },
            { kind: "switch", label: "Nahverkehr", key: "effects_passenger_local_rail" },
            { kind: "switch", label: "Güterverkehr", key: "effects_cargo_rail" },
        ],
    },
    {
        label: "Streckenausbau",
        fields: [
            { kind: "switch", label: "Neubaustrecke (NBS)", key: "nbs" },
            { kind: "switch", label: "Ausbaustrecke (ABS)", key: "abs" },
            { kind: "switch", label: "Zweigleisiger Ausbau", key: "second_track" },
            { kind: "switch", label: "Dreigleisiger Ausbau", key: "third_track" },
            { kind: "switch", label: "Viergleisiger Ausbau", key: "fourth_track" },
            { kind: "switch", label: "Kurvenanhebung", key: "curve" },
            { kind: "switch", label: "Geschwindigkeitsanhebung", key: "increase_speed" },
            { kind: "number", label: "Neue Vmax (km/h)", key: "new_vmax", indent: true },
            { kind: "switch", label: "Tunnel Lichtraumprofil", key: "tunnel_structural_gauge" },
            { kind: "switch", label: "Neigetechnik", key: "tilting" },
        ],
    },
    {
        label: "Bahnhöfe & Infrastruktur",
        fields: [
            { kind: "switch", label: "Neuer Bahnhof", key: "new_station" },
            { kind: "switch", label: "Bahnsteig", key: "platform" },
            { kind: "switch", label: "Knotenbahnhof", key: "junction_station" },
            { kind: "number", label: "Anzahl Knotenbahnhöfe", key: "number_junction_station", indent: true },
            { kind: "switch", label: "Überholbahnhof", key: "overtaking_station" },
            { kind: "number", label: "Anzahl Überholbahnhöfe", key: "number_overtaking_station", indent: true },
            { kind: "switch", label: "Depot", key: "depot" },
            { kind: "switch", label: "Niveaufreier Bahnsteigzugang", key: "level_free_platform_entrance" },
            { kind: "switch", label: "Doppelbelegung", key: "double_occupancy" },
            { kind: "switch", label: "Gleichzeitige Einfahrten", key: "simultaneous_train_entries" },
            { kind: "switch", label: "Puffergleis", key: "buffer_track" },
            { kind: "switch", label: "Überführung", key: "overpass" },
            { kind: "switch", label: "Lärmschutzwand", key: "noise_barrier" },
            { kind: "switch", label: "Bahnübergang", key: "railroad_crossing" },
            { kind: "switch", label: "Gleiswechselbetrieb (GWB)", key: "gwb" },
        ],
    },
    {
        label: "Signaltechnik & Digitalisierung",
        fields: [
            { kind: "switch", label: "ETCS", key: "etcs" },
            { kind: "number", label: "ETCS-Level", key: "etcs_level", indent: true },
            { kind: "switch", label: "Neues ESTW", key: "new_estw" },
            { kind: "switch", label: "Neues DSTW", key: "new_dstw" },
            { kind: "switch", label: "Blockerhöhung", key: "block_increase" },
            { kind: "switch", label: "Bahnhofsweichen", key: "station_railroad_switches" },
            { kind: "switch", label: "Überwerfungsbauwerk", key: "flying_junction" },
        ],
    },
    {
        label: "Elektrifizierung & Energie",
        fields: [
            { kind: "switch", label: "Elektrifizierung", key: "elektrification" },
            { kind: "switch", label: "Optimierte Elektrifizierung", key: "optimised_electrification" },
            { kind: "switch", label: "Ladestation", key: "charging_station" },
            { kind: "switch", label: "Kleine Ladestation", key: "small_charging_station" },
            { kind: "switch", label: "Batterie", key: "battery" },
            { kind: "switch", label: "Wasserstoff (H₂)", key: "h2" },
            { kind: "switch", label: "E-Fuel", key: "efuel" },
            { kind: "switch", label: "Tankstellen E-Fuel", key: "filling_stations_efuel" },
            { kind: "switch", label: "Tankstellen H₂", key: "filling_stations_h2" },
            { kind: "switch", label: "Tankstellen Diesel", key: "filling_stations_diesel" },
            { kind: "number", label: "Anzahl Tankstellen", key: "filling_stations_count" },
        ],
    },
    {
        label: "Sonstiges",
        fields: [
            { kind: "switch", label: "SGV 740m", key: "sgv740m" },
            { kind: "switch", label: "Sanierung", key: "sanierung" },
            { kind: "switch", label: "Stilllegung", key: "closure" },
        ],
    },
] as const;

type Field = (typeof PROPERTY_SECTIONS)[number]["fields"][number];

/** Boolean property keys (switch fields), as a literal union. */
export type BoolKey = Extract<Field, { kind: "switch" }>["key"];
/** Numeric property keys (number fields), as a literal union. */
export type NumKey = Extract<Field, { kind: "number" }>["key"];

export type PropField =
    | { kind: "switch"; label: string; key: BoolKey }
    | { kind: "number"; label: string; key: NumKey; indent?: boolean };

const allFields: readonly Field[] = PROPERTY_SECTIONS.flatMap(
    (s) => s.fields as readonly Field[],
);

export const BOOL_KEYS = allFields
    .filter((f): f is Extract<Field, { kind: "switch" }> => f.kind === "switch")
    .map((f) => f.key) as readonly BoolKey[];

export const NUM_KEYS = allFields
    .filter((f): f is Extract<Field, { kind: "number" }> => f.kind === "number")
    .map((f) => f.key) as readonly NumKey[];
