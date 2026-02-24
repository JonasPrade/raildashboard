import type { Project } from "../../shared/api/queries";

export type TrainCategoryLabel = { key: keyof Project; label: string; color: string };

export const trainCategoryLabels: TrainCategoryLabel[] = [
    { key: "effects_passenger_long_rail", label: "Fernverkehr", color: "blue" },
    { key: "effects_passenger_local_rail", label: "Nahverkehr", color: "teal" },
    { key: "effects_cargo_rail", label: "Güterverkehr", color: "orange" },
];

export type FeatureItem = { key: keyof Project; label: string };

export const featureGroups: Array<{ groupLabel: string; features: FeatureItem[] }> = [
    {
        groupLabel: "Streckenausbau",
        features: [
            { key: "nbs", label: "Neubaustrecke (NBS)" },
            { key: "abs", label: "Ausbaustrecke (ABS)" },
            { key: "second_track", label: "Zweigleisiger Ausbau" },
            { key: "third_track", label: "Dreigleisiger Ausbau" },
            { key: "fourth_track", label: "Viergleisiger Ausbau" },
            { key: "curve", label: "Kurvenanhebung" },
            { key: "increase_speed", label: "Geschwindigkeitsanhebung" },
            { key: "tunnel_structural_gauge", label: "Tunnel Lichtraumprofil" },
            { key: "tilting", label: "Neigetechnik" },
        ],
    },
    {
        groupLabel: "Bahnhöfe & Infrastruktur",
        features: [
            { key: "new_station", label: "Neuer Bahnhof" },
            { key: "platform", label: "Bahnsteig" },
            { key: "junction_station", label: "Knotenbahnhof" },
            { key: "overtaking_station", label: "Überholbahnhof" },
            { key: "depot", label: "Depot" },
            { key: "level_free_platform_entrance", label: "Niveaufreier Bahnsteigzugang" },
            { key: "double_occupancy", label: "Doppelbelegung" },
            { key: "simultaneous_train_entries", label: "Gleichzeitige Einfahrten" },
            { key: "buffer_track", label: "Puffergleis" },
            { key: "overpass", label: "Überführung" },
            { key: "noise_barrier", label: "Lärmschutzwand" },
            { key: "railroad_crossing", label: "Bahnübergang" },
            { key: "gwb", label: "Gleiswechselbetrieb (GWB)" },
        ],
    },
    {
        groupLabel: "Signaltechnik & Digitalisierung",
        features: [
            { key: "etcs", label: "ETCS" },
            { key: "new_estw", label: "Neues ESTW" },
            { key: "new_dstw", label: "Neues DSTW" },
            { key: "block_increase", label: "Blockerhöhung" },
            { key: "station_railroad_switches", label: "Bahnhofsweichen" },
            { key: "flying_junction", label: "Überwerfungsbauwerk" },
        ],
    },
    {
        groupLabel: "Elektrifizierung & Energie",
        features: [
            { key: "elektrification", label: "Elektrifizierung" },
            { key: "optimised_electrification", label: "Optimierte Elektrifizierung" },
            { key: "charging_station", label: "Ladestation" },
            { key: "small_charging_station", label: "Kleine Ladestation" },
            { key: "battery", label: "Batterie" },
            { key: "h2", label: "Wasserstoff (H₂)" },
            { key: "efuel", label: "E-Fuel" },
            { key: "filling_stations_efuel", label: "Tankstellen E-Fuel" },
            { key: "filling_stations_h2", label: "Tankstellen H₂" },
            { key: "filling_stations_diesel", label: "Tankstellen Diesel" },
        ],
    },
    {
        groupLabel: "Sonstiges",
        features: [
            { key: "sgv740m", label: "SGV 740m" },
            { key: "sanierung", label: "Sanierung" },
            { key: "closure", label: "Stilllegung" },
        ],
    },
];
