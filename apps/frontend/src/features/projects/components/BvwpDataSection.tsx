import {
    Group,
    Loader,
    SimpleGrid,
    Stack,
    Table,
    Tabs,
    Text,
    Title,
} from "@mantine/core";
import { type BvwpProjectData, useProjectBvwp } from "../../../shared/api/queries";
import { ChronicleCard, ChronicleDataChip } from "../../../components/chronicle";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtFloat(val: number | null | undefined): string | null {
    if (val === null || val === undefined) return null;
    return val.toLocaleString("de-DE", { maximumFractionDigits: 2 });
}

function fmtMio(val: number | null | undefined): string | null {
    if (val === null || val === undefined) return null;
    return val.toLocaleString("de-DE", { maximumFractionDigits: 1 }) + " Mio. €";
}

type FieldDef = {
    label: string;
    format: (d: BvwpProjectData) => string | null;
};

// ---------------------------------------------------------------------------
// Field group definitions
// ---------------------------------------------------------------------------

const GRUNDDATEN_FIELDS: FieldDef[] = [
    { label: "Bedarfsplan-Nr.", format: (d) => d.bedarfsplan_nr != null ? String(d.bedarfsplan_nr) : null },
    { label: "Priorität", format: (d) => d.priority ?? null },
    { label: "Begründung Priorität", format: (d) => d.reason_priority ?? null },
    { label: "Engpassbeseitigung", format: (d) => d.bottleneck_elimination != null ? (d.bottleneck_elimination ? "Ja" : "Nein") : null },
    { label: "Alternativen", format: (d) => d.bvwp_alternatives ?? null },
];

const KOSTEN_FIELDS: FieldDef[] = [
    { label: "Geplante Gesamtkosten", format: (d) => fmtMio(d.planned_total_cost) },
    { label: "Tatsächliche Kosten", format: (d) => d.actual_cost != null ? d.actual_cost.toLocaleString("de-DE") + " T€" : null },
    { label: "Instandhaltungskosten", format: (d) => fmtMio(d.maintenance_cost) },
    { label: "Investitionskosten", format: (d) => fmtMio(d.investment_cost) },
    { label: "Planungskosten", format: (d) => fmtMio(d.planning_cost) },
    { label: "Kapitaldienst", format: (d) => fmtMio(d.capital_service_cost) },
    { label: "BVWP Planungskosten (gesamt)", format: (d) => fmtMio(d.bvwp_planned_cost) },
    { label: "BVWP Instandhaltungskosten (geplant)", format: (d) => fmtMio(d.bvwp_planned_maintenance_cost) },
    { label: "BVWP Planungskosten (geplant)", format: (d) => fmtMio(d.bvwp_planned_planning_cost) },
    { label: "BVWP Planungskosten (angefallen)", format: (d) => fmtMio(d.bvwp_planned_planning_cost_incurred) },
    { label: "Haushaltsrelevante Kosten", format: (d) => fmtMio(d.bvwp_total_budget_relevant_cost) },
    { label: "Haushaltsrelevante Kosten (angefallen)", format: (d) => fmtMio(d.bvwp_total_budget_relevant_cost_incurred) },
    { label: "Bewertungsrelevante Kosten", format: (d) => fmtMio(d.bvwp_valuation_relevant_cost) },
    { label: "Bewertungsrelevante Kosten (Preisstand 2012)", format: (d) => fmtMio(d.bvwp_valuation_relevant_cost_pricelevel_2012) },
    { label: "davon Planungskosten (Preisstand 2012)", format: (d) => fmtMio(d.bvwp_valuation_relevant_cost_pricelevel_2012_planning_cost) },
    { label: "davon Infrastrukturkosten (Preisstand 2012)", format: (d) => fmtMio(d.bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos) },
    { label: "Barwert Investitionskosten (Preisstand 2012)", format: (d) => fmtMio(d.bvwp_valuation_relevant_cost_pricelevel_2012_present_value) },
];

const PROGNOSE_PV_FIELDS: FieldDef[] = [
    { label: "Verlagerung Pkw → Schiene (Mio. Pkm/a)", format: (d) => fmtFloat(d.relocation_car_to_rail) },
    { label: "Verlagerung Schiene → Pkw (Mio. Pkm/a)", format: (d) => fmtFloat(d.relocation_rail_to_car) },
    { label: "Verlagerung Luft → Schiene (Mio. Pkm/a)", format: (d) => fmtFloat(d.relocation_air_to_rail) },
    { label: "Induzierter Verkehr (Mio. Pkm/a)", format: (d) => fmtFloat(d.induced_traffic) },
    { label: "Δ Pkw-km (Mio. Fzkm/a)", format: (d) => fmtFloat(d.delta_car_km) },
    { label: "Δ Schienenverkehr gesamt (Mio. Pkm/a)", format: (d) => fmtFloat(d.delta_km_rail) },
    { label: "Δ Fahrtzeit Schiene (Mio. Pmin/a)", format: (d) => fmtFloat(d.delta_rail_running_time) },
    { label: "Δ Schienen-km (Schiene)", format: (d) => fmtFloat(d.delta_rail_km_rail) },
    { label: "Δ Schienen-km (Pkw→S)", format: (d) => fmtFloat(d.delta_rail_km_car_to_rail) },
    { label: "Δ Schienen-km (S→Pkw)", format: (d) => fmtFloat(d.delta_rail_km_rail_to_car) },
    { label: "Δ Schienen-km (Luft→S)", format: (d) => fmtFloat(d.delta_rail_km_air_to_rail) },
    { label: "Δ Schienen-km (induziert)", format: (d) => fmtFloat(d.delta_rail_km_induced) },
    { label: "Δ Reisezeit Schiene (Mio. Pmin/a)", format: (d) => fmtFloat(d.delta_travel_time_rail) },
    { label: "Δ Reisezeit Pkw→S (Mio. Pmin/a)", format: (d) => fmtFloat(d.delta_travel_time_car_to_rail) },
    { label: "Δ Reisezeit S→Pkw (Mio. Pmin/a)", format: (d) => fmtFloat(d.delta_travel_time_rail_to_car) },
    { label: "Δ Reisezeit Luft→S (Mio. Pmin/a)", format: (d) => fmtFloat(d.delta_travel_time_air_to_rail) },
    { label: "Δ Reisezeit induziert (Mio. Pmin/a)", format: (d) => fmtFloat(d.delta_travel_time_induced) },
];

const PROGNOSE_GV_FIELDS: FieldDef[] = [
    { label: "Verlagerung Lkw → Schiene (Mio. tkm/a)", format: (d) => fmtFloat(d.relocation_truck_to_rail) },
    { label: "Verlagerung Schiff → Schiene (Mio. tkm/a)", format: (d) => fmtFloat(d.relocation_ship_to_rail) },
    { label: "Δ Lkw-km (Mio. Fzkm/a)", format: (d) => fmtFloat(d.delta_truck_km) },
    { label: "Δ Lkw-Fahrten (Mio./a)", format: (d) => fmtFloat(d.delta_truck_count) },
    { label: "Δ Güterfahrten Schiene (Mio./a)", format: (d) => fmtFloat(d.delta_rail_cargo_count) },
    { label: "Δ Fahrtzeit Güter Schiene (Mio. Fzmin/a)", format: (d) => fmtFloat(d.delta_rail_cargo_running_time) },
    { label: "Δ Güter-km Lkw→S (Mio. tkm/a)", format: (d) => fmtFloat(d.delta_rail_cargo_km_lkw_to_rail) },
    { label: "Δ Güter-km Schiff→S (Mio. tkm/a)", format: (d) => fmtFloat(d.delta_rail_cargo_km_ship_to_rail) },
    { label: "Δ Fahrtzeit Güter S (Mio. Fzmin/a)", format: (d) => fmtFloat(d.delta_rail_cargo_time_rail) },
    { label: "Δ Fahrtzeit Lkw→S (Mio. Fzmin/a)", format: (d) => fmtFloat(d.delta_rail_cargo_time_lkw_to_rail) },
    { label: "Δ Fahrtzeit Schiff→S (Mio. Fzmin/a)", format: (d) => fmtFloat(d.delta_rail_cargo_time_ship_to_rail) },
];

const NUTZEN_PV_FIELDS: FieldDef[] = [
    { label: "Betriebskosten Pkw (jährl.)", format: (d) => fmtMio(d.use_change_operation_cost_car_yearly) },
    { label: "Betriebskosten Schiene (jährl.)", format: (d) => fmtMio(d.use_change_operating_cost_rail_yearly) },
    { label: "Betriebskosten Luft (jährl.)", format: (d) => fmtMio(d.use_change_operating_cost_air_yearly) },
    { label: "Emissionen Pkw (jährl.)", format: (d) => fmtMio(d.use_change_pollution_car_yearly) },
    { label: "Emissionen Schiene (jährl.)", format: (d) => fmtMio(d.use_change_pollution_rail_yearly) },
    { label: "Emissionen Luft (jährl.)", format: (d) => fmtMio(d.use_change_pollution_air_yearly) },
    { label: "Unfallkosten Pkw (jährl.)", format: (d) => fmtMio(d.use_change_safety_car_yearly) },
    { label: "Unfallkosten Schiene (jährl.)", format: (d) => fmtMio(d.use_change_safety_rail_yearly) },
    { label: "Reisezeitkosten Schiene (jährl.)", format: (d) => fmtMio(d.use_change_travel_time_rail_yearly) },
    { label: "Reisezeitkosten induziert (jährl.)", format: (d) => fmtMio(d.use_change_travel_time_induced_yearly) },
    { label: "Reisezeitkosten Pkw (jährl.)", format: (d) => fmtMio(d.use_change_travel_time_pkw_yearly) },
    { label: "Reisezeitkosten Luft (jährl.)", format: (d) => fmtMio(d.use_change_travel_time_air_yearly) },
    { label: "Reisezeitkosten <2 Min. (jährl.)", format: (d) => fmtMio(d.use_change_travel_time_less_2min_yearly) },
    { label: "Impliziter Nutzen induziert (jährl.)", format: (d) => fmtMio(d.use_change_implicit_benefit_induced_yearly) },
    { label: "Impliziter Nutzen Pkw (jährl.)", format: (d) => fmtMio(d.use_change_implicit_benefit_pkw_yearly) },
    { label: "Impliziter Nutzen Luft (jährl.)", format: (d) => fmtMio(d.use_change_implicit_benefit_air_yearly) },
    { label: "Summe Nutzen PV (jährl.)", format: (d) => fmtMio(d.use_sum_passenger_yearly) },
    { label: "Betriebskosten Pkw (Barwert)", format: (d) => fmtMio(d.use_change_operation_cost_car_present_value) },
    { label: "Betriebskosten Schiene (Barwert)", format: (d) => fmtMio(d.use_change_operating_cost_rail_present_value) },
    { label: "Betriebskosten Luft (Barwert)", format: (d) => fmtMio(d.use_change_operating_cost_air_present_value) },
    { label: "Emissionen Pkw (Barwert)", format: (d) => fmtMio(d.use_change_pollution_car_present_value) },
    { label: "Emissionen Schiene (Barwert)", format: (d) => fmtMio(d.use_change_pollution_rail_present_value) },
    { label: "Emissionen Luft (Barwert)", format: (d) => fmtMio(d.use_change_pollution_air_present_value) },
    { label: "Unfallkosten Pkw (Barwert)", format: (d) => fmtMio(d.use_change_safety_car_present_value) },
    { label: "Unfallkosten Schiene (Barwert)", format: (d) => fmtMio(d.use_change_safety_rail_present_value) },
    { label: "Reisezeitkosten Schiene (Barwert)", format: (d) => fmtMio(d.use_change_travel_time_rail_present_value) },
    { label: "Reisezeitkosten induziert (Barwert)", format: (d) => fmtMio(d.use_change_travel_time_induced_present_value) },
    { label: "Reisezeitkosten Pkw (Barwert)", format: (d) => fmtMio(d.use_change_travel_time_pkw_present_value) },
    { label: "Reisezeitkosten Luft (Barwert)", format: (d) => fmtMio(d.use_change_travel_time_air_present_value) },
    { label: "Reisezeitkosten <2 Min. (Barwert)", format: (d) => fmtMio(d.use_change_travel_time_less_2min_present_value) },
    { label: "Impliziter Nutzen induziert (Barwert)", format: (d) => fmtMio(d.use_change_implicit_benefit_induced_present_value) },
    { label: "Impliziter Nutzen Pkw (Barwert)", format: (d) => fmtMio(d.use_change_implicit_benefit_pkw_present_value) },
    { label: "Impliziter Nutzen Luft (Barwert)", format: (d) => fmtMio(d.use_change_implicit_benefit_air_present_value) },
    { label: "Summe Nutzen PV (Barwert)", format: (d) => fmtMio(d.use_sum_passenger_present_value) },
];

const NUTZEN_GV_FIELDS: FieldDef[] = [
    { label: "Betriebskosten Lkw (jährl.)", format: (d) => fmtMio(d.use_change_operating_cost_truck_yearly) },
    { label: "Betriebskosten Güter-S (jährl.)", format: (d) => fmtMio(d.use_change_operating_cost_rail_cargo_yearly) },
    { label: "Betriebskosten Schiff (jährl.)", format: (d) => fmtMio(d.use_change_operating_cost_ship_yearly) },
    { label: "Emissionen Lkw (jährl.)", format: (d) => fmtMio(d.use_change_pollution_truck_yearly) },
    { label: "Emissionen Güter-S (jährl.)", format: (d) => fmtMio(d.use_change_pollution_rail_cargo_yearly) },
    { label: "Emissionen Schiff (jährl.)", format: (d) => fmtMio(d.use_change_pollution_ship_yearly) },
    { label: "Unfallkosten Lkw (jährl.)", format: (d) => fmtMio(d.use_change_safety_truck_yearly) },
    { label: "Unfallkosten Güter-S (jährl.)", format: (d) => fmtMio(d.use_change_safety_rail_cargo_yearly) },
    { label: "Unfallkosten Schiff (jährl.)", format: (d) => fmtMio(d.use_change_safety_ship_yearly) },
    { label: "Laufzeitkosten Schiene (jährl.)", format: (d) => fmtMio(d.use_change_running_time_rail_yearly) },
    { label: "Laufzeitkosten Lkw (jährl.)", format: (d) => fmtMio(d.use_change_running_time_lkw_yearly) },
    { label: "Laufzeitkosten Schiff (jährl.)", format: (d) => fmtMio(d.use_change_running_time_ship_yearly) },
    { label: "Impliziter Nutzen Lkw (jährl.)", format: (d) => fmtMio(d.use_change_implicit_benefit_truck_yearly) },
    { label: "Impliziter Nutzen Schiff (jährl.)", format: (d) => fmtMio(d.use_change_implicit_benefit_ship_yearly) },
    { label: "Zuverlässigkeit (jährl.)", format: (d) => fmtMio(d.use_change_reliability_yearly) },
    { label: "Summe Nutzen GV (jährl.)", format: (d) => fmtMio(d.use_sum_cargo_yearly) },
    { label: "Betriebskosten Lkw (Barwert)", format: (d) => fmtMio(d.use_change_operating_cost_truck_present_value) },
    { label: "Betriebskosten Güter-S (Barwert)", format: (d) => fmtMio(d.use_change_operating_cost_rail_cargo_present_value) },
    { label: "Betriebskosten Schiff (Barwert)", format: (d) => fmtMio(d.use_change_operating_cost_ship_present_value) },
    { label: "Emissionen Lkw (Barwert)", format: (d) => fmtMio(d.use_change_pollution_truck_present_value) },
    { label: "Emissionen Güter-S (Barwert)", format: (d) => fmtMio(d.use_change_pollution_rail_cargo_present_value) },
    { label: "Emissionen Schiff (Barwert)", format: (d) => fmtMio(d.use_change_pollution_ship_present_value) },
    { label: "Unfallkosten Lkw (Barwert)", format: (d) => fmtMio(d.use_change_safety_truck_present_value) },
    { label: "Unfallkosten Güter-S (Barwert)", format: (d) => fmtMio(d.use_change_safety_rail_cargo_present_value) },
    { label: "Unfallkosten Schiff (Barwert)", format: (d) => fmtMio(d.use_change_safety_ship_present_value) },
    { label: "Laufzeitkosten Schiene (Barwert)", format: (d) => fmtMio(d.use_change_running_time_rail_present_value) },
    { label: "Laufzeitkosten Lkw (Barwert)", format: (d) => fmtMio(d.use_change_running_time_lkw_present_value) },
    { label: "Laufzeitkosten Schiff (Barwert)", format: (d) => fmtMio(d.use_change_running_time_ship_present_value) },
    { label: "Impliziter Nutzen Lkw (Barwert)", format: (d) => fmtMio(d.use_change_implicit_benefit_truck_present_value) },
    { label: "Impliziter Nutzen Schiff (Barwert)", format: (d) => fmtMio(d.use_change_implicit_benefit_ship_present_value) },
    { label: "Zuverlässigkeit (Barwert)", format: (d) => fmtMio(d.use_change_reliability_present_value) },
    { label: "Summe Nutzen GV (Barwert)", format: (d) => fmtMio(d.use_sum_cargo_present_value) },
];

const WEITERE_NUTZENWIRKUNGEN_FIELDS: FieldDef[] = [
    { label: "Erhaltungskosten (jährl.)", format: (d) => fmtMio(d.use_change_maintenance_cost_yearly) },
    { label: "LCC Infrastruktur (jährl.)", format: (d) => fmtMio(d.use_change_lcc_infrastructure_yearly) },
    { label: "Lärm Innenorts (jährl.)", format: (d) => fmtMio(d.use_change_noise_intown_yearly) },
    { label: "Lärm Außerorts (jährl.)", format: (d) => fmtMio(d.use_change_noise_outtown_yearly) },
    { label: "Summe weitere Nutzenwirkungen (jährl.)", format: (d) => fmtMio(d.sum_use_change_yearly) },
    { label: "Erhaltungskosten (Barwert)", format: (d) => fmtMio(d.use_change_maintenance_cost_present_value) },
    { label: "LCC Infrastruktur (Barwert)", format: (d) => fmtMio(d.use_change_lcc_infrastructure_present_value) },
    { label: "Lärm Innenorts (Barwert)", format: (d) => fmtMio(d.use_change_noise_intown_present_value) },
    { label: "Lärm Außerorts (Barwert)", format: (d) => fmtMio(d.use_change_noise_outtown_present_value) },
    { label: "Summe weitere Nutzenwirkungen (Barwert)", format: (d) => fmtMio(d.sum_use_change_present_value) },
];

const UMWELT_FIELDS: FieldDef[] = [
    { label: "Umweltbetroffenheit (Bewertung)", format: (d) => d.bvwp_environmental_impact ?? null },
    { label: "Δ NOx (t/a)", format: (d) => fmtFloat(d.delta_nox) },
    { label: "Δ CO (t/a)", format: (d) => fmtFloat(d.delta_co) },
    { label: "Δ CO₂ (kt/a)", format: (d) => fmtFloat(d.delta_co2) },
    { label: "Δ HC (t/a)", format: (d) => fmtFloat(d.delta_hc) },
    { label: "Δ PM (t/a)", format: (d) => fmtFloat(d.delta_pm) },
    { label: "Δ SO₂ (t/a)", format: (d) => fmtFloat(d.delta_so2) },
    { label: "Summe Nutzen Umwelt", format: (d) => fmtMio(d.bvwp_sum_use_environment) },
    { label: "Umweltbetroffenheit Gesamtergebnis", format: (d) => d.bvwp_sum_environmental_affectedness ?? null },
    { label: "Umweltbetroffenheit (Text)", format: (d) => d.bvwp_sum_environmental_affectedness_text ?? null },
    { label: "Lärm: neu Betroffene", format: (d) => fmtFloat(d.noise_new_affected) },
    { label: "Lärm: Entlastete", format: (d) => fmtFloat(d.noise_relieved) },
    { label: "Δ Lärm Außerorts", format: (d) => fmtFloat(d.change_noise_outtown) },
    { label: "Fläche Natur hoher Bedeutung (ha)", format: (d) => fmtFloat(d.area_nature_high_importance) },
    { label: "Fläche Natur hoher Bedeutung (ha/km)", format: (d) => fmtFloat(d.area_nature_high_importance_per_km) },
    { label: "Fläche Natur hoher Bedeutung (Bewertung)", format: (d) => d.area_nature_high_importance_rating ?? null },
    { label: "Natura 2000 (Bewertung)", format: (d) => d.natura2000_rating ?? null },
    { label: "Natura 2000 nicht ausgeschlossen", format: (d) => fmtFloat(d.natura2000_not_excluded) },
    { label: "Natura 2000 wahrscheinlich", format: (d) => fmtFloat(d.natura2000_probably) },
    { label: "UFR 250 (ha)", format: (d) => fmtFloat(d.ufr_250) },
    { label: "UFR 250 (ha/km)", format: (d) => fmtFloat(d.ufr_250_per_km) },
    { label: "UFRA 250 (Bewertung)", format: (d) => d.ufra_250_rating ?? null },
    { label: "BfN-Bewertung", format: (d) => d.bfn_rating ?? null },
    { label: "UFR 1000 Unzerschnittene Großflächen (ha)", format: (d) => fmtFloat(d.ufr_1000_undissacted_large_area) },
    { label: "UFR 1000 Großflächen (ha/km)", format: (d) => fmtFloat(d.ufr_1000_undissacted_large_area_per_km) },
    { label: "UFR 1000 Großsäuger (ha)", format: (d) => fmtFloat(d.ufr_1000_undissacted_large_mammals) },
    { label: "UFR 1000 Großsäuger (ha/km)", format: (d) => fmtFloat(d.ufr_1000_undissacted_large_mammals_per_km) },
    { label: "Anzahl unzerschnittener Räume", format: (d) => fmtFloat(d.count_undissacted_area) },
    { label: "Anzahl wiedervernetzter Räume", format: (d) => fmtFloat(d.count_reconnect_area) },
    { label: "Flächenverbrauch (ha)", format: (d) => fmtFloat(d.land_consumption) },
    { label: "Überschwemmungsgebiet (ha)", format: (d) => fmtFloat(d.flooding_area) },
    { label: "Überschwemmungsgebiet (ha/km)", format: (d) => fmtFloat(d.flooding_area_per_km) },
    { label: "Überschwemmungsgebiet (Bewertung)", format: (d) => d.flooding_area_rating ?? null },
    { label: "Wasserschutzgebiet (ha)", format: (d) => fmtFloat(d.water_protection_area) },
    { label: "Wasserschutzgebiet (ha/km)", format: (d) => fmtFloat(d.water_protection_area_per_km) },
    { label: "Wasserschutzgebiet (Bewertung)", format: (d) => d.water_protection_area_rating ?? null },
    { label: "UZVR (ha)", format: (d) => fmtFloat(d.uzvr) },
    { label: "UVZR (Bewertung)", format: (d) => d.uvzr_rating ?? null },
    { label: "Vorranggebiet Landschaftsschutz (ha)", format: (d) => fmtFloat(d.priortiy_area_landscape_protection) },
    { label: "Vorranggebiet Landschaftsschutz (ha/km)", format: (d) => fmtFloat(d.priority_area_landscape_protection_per_km) },
    { label: "Vorranggebiet Landschaftsschutz (Bewertung)", format: (d) => d.priority_area_landscape_protection_rating ?? null },
    { label: "Zusätzliche Umweltinformationen", format: (d) => d.environmental_additional_informations ?? null },
];

const RAUMORDNUNG_FIELDS: FieldDef[] = [
    { label: "Regionalwirtschaftliche Bedeutung", format: (d) => d.bvwp_regional_significance ?? null },
    { label: "Raumordnung Gesamtergebnis", format: (d) => d.spatial_significance_overall_result ?? null },
    { label: "Raumordnung Begründung", format: (d) => d.spatial_significance_reasons ?? null },
    { label: "Straßennetz", format: (d) => d.spatial_significance_street ?? null },
    { label: "Erschließungsdefizite", format: (d) => d.spatial_significance_accessibility_deficits ?? null },
    { label: "Fazit", format: (d) => d.spatial_significance_conclusion ?? null },
];

const SONSTIGES_FIELDS: FieldDef[] = [
    { label: "Reisezeitverkürzung (min)", format: (d) => fmtFloat(d.traveltime_reduction) },
    { label: "Reisezeitbeispiele", format: (d) => d.bvwp_traveltime_examples ?? null },
    { label: "Planungsdauer ausstehend (Jahre)", format: (d) => fmtFloat(d.bvwp_duration_of_outstanding_planning) },
    { label: "Baudauer (Jahre)", format: (d) => fmtFloat(d.bvwp_duration_of_build) },
    { label: "Betriebsdauer (Jahre)", format: (d) => fmtFloat(d.bvwp_duration_operating) },
    { label: "Zusätzliche Informationen", format: (d) => d.bvwp_additional_informations ?? null },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

type FieldGridProps = { fields: FieldDef[]; data: BvwpProjectData };

function FieldGrid({ fields, data }: FieldGridProps) {
    const visible = fields
        .map((f) => ({ label: f.label, value: f.format(data) }))
        .filter((f) => f.value !== null) as { label: string; value: string }[];

    if (visible.length === 0) {
        return <Text size="sm" c="dimmed">Keine Daten vorhanden.</Text>;
    }

    return (
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
            {visible.map(({ label, value }) => (
                <Group key={label} gap="xs" align="flex-start" wrap="nowrap">
                    <Text size="sm" fw={500} style={{ minWidth: 220, flexShrink: 0 }}>{label}</Text>
                    <Text size="sm" c="dimmed">{value}</Text>
                </Group>
            ))}
        </SimpleGrid>
    );
}

const TIME_PERIODS = [
    { label: "06–09 Uhr", key: "6to9" as const },
    { label: "09–16 Uhr", key: "9to16" as const },
    { label: "16–19 Uhr", key: "16to19" as const },
    { label: "19–22 Uhr", key: "19to22" as const },
    { label: "22–06 Uhr", key: "22to6" as const },
    { label: "Tagesgang", key: "day" as const },
];

type TimePeriodKey = typeof TIME_PERIODS[number]["key"];

function congestionRef(d: BvwpProjectData, period: TimePeriodKey) {
    const km = d[`bvwp_congested_rail_reference_${period}_km` as keyof BvwpProjectData] as number | null | undefined;
    const perc = d[`bvwp_congested_rail_reference_${period}_perc` as keyof BvwpProjectData] as number | null | undefined;
    return { km, perc };
}

function congestionPlan(d: BvwpProjectData, period: TimePeriodKey) {
    const km = d[`bvwp_congested_rail_plancase_${period}_km` as keyof BvwpProjectData] as number | null | undefined;
    const perc = d[`bvwp_congested_rail_plancase_${period}_perc` as keyof BvwpProjectData] as number | null | undefined;
    return { km, perc };
}

function KapazitaetTab({ data }: { data: BvwpProjectData }) {
    const hasTable = TIME_PERIODS.some((p) => {
        const r = congestionRef(data, p.key);
        const pl = congestionPlan(data, p.key);
        return r.km != null || r.perc != null || pl.km != null || pl.perc != null;
    });

    return (
        <Stack gap="md">
            {hasTable && (
                <Stack gap="xs">
                    <Text size="sm" fw={600} c="dimmed" tt="uppercase" lts={0.5}>Streckenauslastung (überlastet)</Text>
                    <Table withTableBorder withColumnBorders fz="sm">
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Zeitraum</Table.Th>
                                <Table.Th>Ref.-fall km</Table.Th>
                                <Table.Th>Ref.-fall %</Table.Th>
                                <Table.Th>Planfall km</Table.Th>
                                <Table.Th>Planfall %</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {TIME_PERIODS.map((p) => {
                                const r = congestionRef(data, p.key);
                                const pl = congestionPlan(data, p.key);
                                return (
                                    <Table.Tr key={p.key}>
                                        <Table.Td>{p.label}</Table.Td>
                                        <Table.Td>{fmtFloat(r.km) ?? "–"}</Table.Td>
                                        <Table.Td>{fmtFloat(r.perc) ?? "–"}</Table.Td>
                                        <Table.Td>{fmtFloat(pl.km) ?? "–"}</Table.Td>
                                        <Table.Td>{fmtFloat(pl.perc) ?? "–"}</Table.Td>
                                    </Table.Tr>
                                );
                            })}
                        </Table.Tbody>
                    </Table>
                </Stack>
            )}
            <FieldGrid
                data={data}
                fields={[
                    { label: "Ungeplante Wartezeit Referenzfall (min)", format: (d) => fmtFloat(d.bvwp_unscheduled_waiting_period_reference) },
                    { label: "Ungeplante Wartezeit Planfall (min)", format: (d) => fmtFloat(d.bvwp_unscheduled_waiting_period_plancase) },
                    { label: "Pünktlichkeit Güter Referenzfall (%)", format: (d) => fmtFloat(d.bvwp_punctuality_cargo_reference) },
                    { label: "Δ Pünktlichkeit relativ (%)", format: (d) => fmtFloat(d.bvwp_delta_punctuality_relativ) },
                    { label: "Δ Pünktlichkeit absolut (min)", format: (d) => fmtFloat(d.bvwp_delta_punctuality_absolut) },
                ]}
            />
        </Stack>
    );
}

// ---------------------------------------------------------------------------
// Priority badge
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Tab definition
// ---------------------------------------------------------------------------

type TabDef = {
    value: string;
    label: string;
    hasData: (d: BvwpProjectData) => boolean;
    render: (d: BvwpProjectData) => React.ReactNode;
};

const TABS: TabDef[] = [
    {
        value: "grunddaten",
        label: "Grunddaten",
        hasData: (d) => GRUNDDATEN_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={GRUNDDATEN_FIELDS} />,
    },
    {
        value: "kosten",
        label: "Kosten",
        hasData: (d) => KOSTEN_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={KOSTEN_FIELDS} />,
    },
    {
        value: "prognose-pv",
        label: "Prognose PV",
        hasData: (d) => PROGNOSE_PV_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={PROGNOSE_PV_FIELDS} />,
    },
    {
        value: "prognose-gv",
        label: "Prognose GV",
        hasData: (d) => PROGNOSE_GV_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={PROGNOSE_GV_FIELDS} />,
    },
    {
        value: "nutzen-pv",
        label: "Nutzen PV",
        hasData: (d) => NUTZEN_PV_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={NUTZEN_PV_FIELDS} />,
    },
    {
        value: "nutzen-gv",
        label: "Nutzen GV",
        hasData: (d) => NUTZEN_GV_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={NUTZEN_GV_FIELDS} />,
    },
    {
        value: "weitere-nutzenwirkungen",
        label: "Weitere Nutzenwirkungen",
        hasData: (d) => WEITERE_NUTZENWIRKUNGEN_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={WEITERE_NUTZENWIRKUNGEN_FIELDS} />,
    },
    {
        value: "umwelt",
        label: "Umwelt",
        hasData: (d) => UMWELT_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={UMWELT_FIELDS} />,
    },
    {
        value: "raumordnung",
        label: "Raumordnung",
        hasData: (d) => RAUMORDNUNG_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={RAUMORDNUNG_FIELDS} />,
    },
    {
        value: "kapazitaet",
        label: "Kapazität",
        hasData: (d) =>
            TIME_PERIODS.some((p) => {
                const r = congestionRef(d, p.key);
                const pl = congestionPlan(d, p.key);
                return r.km != null || r.perc != null || pl.km != null || pl.perc != null;
            }) ||
            d.bvwp_unscheduled_waiting_period_reference != null ||
            d.bvwp_unscheduled_waiting_period_plancase != null ||
            d.bvwp_punctuality_cargo_reference != null,
        render: (d) => <KapazitaetTab data={d} />,
    },
    {
        value: "sonstiges",
        label: "Sonstiges",
        hasData: (d) => SONSTIGES_FIELDS.some((f) => f.format(d) !== null),
        render: (d) => <FieldGrid data={d} fields={SONSTIGES_FIELDS} />,
    },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

type Props = { projectId: number };

export default function BvwpDataSection({ projectId }: Props) {
    const { data, isLoading } = useProjectBvwp(projectId);

    if (isLoading) {
        return (
            <ChronicleCard>
                <Group>
                    <Loader size="sm" />
                    <Text size="sm" c="dimmed">BVWP-Daten werden geladen …</Text>
                </Group>
            </ChronicleCard>
        );
    }

    // null means 404 — no BVWP data for this project
    if (!data) return null;

    const visibleTabs = TABS.filter((t) => t.hasData(data));

    return (
        <ChronicleCard>
            <Stack gap="md">
                <Group gap="md" align="center">
                    <Title order={4}>BVWP-Bewertung</Title>
                    {data.nkv != null && (
                        <ChronicleDataChip>NKV {fmtFloat(data.nkv)}</ChronicleDataChip>
                    )}
                    {data.priority && (
                        <ChronicleDataChip>{data.priority}</ChronicleDataChip>
                    )}
                </Group>

                {visibleTabs.length === 0 ? (
                    <Text size="sm" c="dimmed">Keine BVWP-Daten vorhanden.</Text>
                ) : (
                    <Tabs defaultValue={visibleTabs[0].value}>
                        <Tabs.List>
                            {visibleTabs.map((t) => (
                                <Tabs.Tab key={t.value} value={t.value}>
                                    {t.label}
                                </Tabs.Tab>
                            ))}
                        </Tabs.List>
                        {visibleTabs.map((t) => (
                            <Tabs.Panel key={t.value} value={t.value} pt="md">
                                {t.render(data)}
                            </Tabs.Panel>
                        ))}
                    </Tabs>
                )}
            </Stack>
        </ChronicleCard>
    );
}
