"""KPI definitions of the Infraplan 2026 (8 Steuerungs-, 15 Informationskennzahlen,
plus the two percentage KPIs that belong to a km KPI: the ETCS equipment rate is
drawn into the ETCS km chart, the electrification share gets a chart of its own
next to the km chart, because the km are an annual figure and the share a
cumulative stock).

Created on first use (``crud.infraplan.ensure_default_kpis``) so the manual
form has something to fill; later years add KPIs through ``definitions`` with
a stable ``key`` (MCP ``set_infraplan_kpi_values`` or the admin form). Units
and categories are corrected the same way; existing rows are never
overwritten from here.
"""

from __future__ import annotations

_S = "STEUERUNG"
_I = "INFORMATION"

# Infraplan 2026, Anhang I ("Informationskennzahl: Kapazitätsauslastung").
KAPAZITAETSAUSLASTUNG_DESCRIPTION = (
    "Anteil der gefahrenen Trassenkilometer in überausgelasteten Netzabschnitten "
    "(Auslastung über 125 %, Auslastungsstufen 5 und 6 der DB InfraGO) an allen "
    "Trassenkilometern, jährlich in Prozent."
)

DEFAULT_KPIS: list[dict] = [
    # --- Steuerungskennzahlen (Kap. 3) ---
    {"key": "neu_gebaute_gleis_km", "name": "Neu gebaute Gleiskilometer", "unit": "km", "kind": _S, "category": "AUS_NEUBAU"},
    {"key": "umsetzung_kmm", "name": "Umsetzung Kleiner und Mittlerer Maßnahmen (KMM)", "unit": "Anzahl", "kind": _S, "category": "AUS_NEUBAU"},
    {"key": "elektrifizierungsgrad", "name": "Elektrifizierungsgrad (elektrifizierte Strecken-km)", "unit": "km", "kind": _S, "category": "AUS_NEUBAU",
     "description": "Je Jahr neu elektrifizierte Strecken-km"},
    {"key": "elektrifizierungsgrad_prozent", "name": "Elektrifizierungsgrad (Anteil am Gesamtnetz)", "unit": "%", "kind": _S, "category": "AUS_NEUBAU",
     "description": "Anteil der elektrifizierten Strecken am Gesamtnetz, kumulierter Stand je Jahr"},
    {"key": "korridorsanierungen_strecken_km", "name": "Streckenkilometer Korridorsanierungen", "unit": "km", "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "anlagenbedingte_verspaetungsminuten", "name": "Anlagenbedingte Verspätungsminuten", "unit": "Tsd. cVmin/Tag", "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "laermsanierte_strecken_km", "name": "Lärmsanierte Streckenkilometer", "unit": "km", "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "bahnhoefe_zielbild", "name": "Bahnhöfe nach abgestimmtem Zielbild (Bau- und Ausstattungsstandards)", "unit": "Anzahl", "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "etcs_strecken_km", "name": "ETCS-Streckenkilometer und -Ausrüstungsgrad", "unit": "km", "kind": _S, "category": "UEBERGEORDNET",
     "total_series": "Gesamtnetz", "companion_key": "etcs_ausruestungsgrad", "companion_label": "Ausrüstungsgrad"},
    # --- Informationskennzahlen (Anhang I) ---
    {"key": "betriebsleistung", "name": "Betriebsleistung", "unit": "Mio. Trkm", "kind": _I, "category": None},
    {"key": "kapazitaetsauslastung", "name": "Kapazitätsauslastung", "unit": "%", "kind": _I, "category": None,
     "description": KAPAZITAETSAUSLASTUNG_DESCRIPTION},
    {"key": "mittelherkunft_mitteleinsatz", "name": "Mittelherkunft und Mitteleinsatz", "unit": "Mrd. €", "kind": _I, "category": None, "chart_layout": "flow"},
    {"key": "bp_einreichung_pf_unterlagen", "name": "Bedarfsplan: Einreichung Planfeststellungsunterlagen", "unit": "Anzahl", "kind": _I, "category": None, "chart_layout": "grouped"},
    {"key": "bp_bundeshaushaltsmittel", "name": "Bedarfsplan: Bundeshaushaltsmittel", "unit": "Mrd. €", "kind": _I, "category": None},
    {"key": "serviceeinrichtungen", "name": "Aus- und Neubau von Serviceeinrichtungen", "unit": "Anzahl", "kind": _I, "category": None},
    {"key": "elektrische_betriebsleistung", "name": "Elektrische Betriebsleistung", "unit": "%", "kind": _I, "category": None},
    {"key": "einhaltung_sperrpausen", "name": "Einhaltung von Sperrpausen", "unit": None, "kind": _I, "category": None},
    {"key": "trassenstornierungen", "name": "Trassenstornierungen", "unit": "Tsd.", "kind": _I, "category": None},
    {"key": "langsamfahrstellen", "name": "Langsamfahrstellen", "unit": "Anzahl", "kind": _I, "category": None},
    {"key": "stellwerksbesetzungsquote", "name": "Stellwerksbesetzungsquote", "unit": "%", "kind": _I, "category": None, "zoomed_axis": True},
    {"key": "laermsanierung_entlastete_anwohner", "name": "Lärmsanierung: Entlastete Anwohner", "unit": "Tsd.", "kind": _I, "category": None},
    {"key": "bahnhoefe_betriebliche_standards", "name": "Bahnhöfe (Betriebliche Standards)", "unit": "Anzahl", "kind": _I, "category": None},
    {"key": "bahnhoefe_anschlussmobilitaet", "name": "Bahnhöfe (Anschlussmobilität und Vorplatz)", "unit": "Anzahl", "kind": _I, "category": None},
    {"key": "barrierefreie_bahnsteige", "name": "Barrierefreie Bahnsteige", "unit": "%", "kind": _I, "category": None, "chart_layout": "split"},
    # --- Second statement drawn into another KPI's chart (companion_key) ---
    {"key": "etcs_ausruestungsgrad", "name": "ETCS-Ausrüstungsgrad", "unit": "%", "kind": _S, "category": "UEBERGEORDNET"},
]
