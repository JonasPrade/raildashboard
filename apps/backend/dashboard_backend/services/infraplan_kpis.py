"""KPI definitions of the Infraplan 2026 (8 Steuerungs-, 15 Informationskennzahlen;
the two charts with km and % are two KPIs each, so 10 Steuerungskennzahlen).

Created on first use (``crud.infraplan.ensure_default_kpis``) so the manual
form has something to fill; later years add KPIs through ``definitions`` with
a stable ``key`` (MCP ``set_infraplan_kpi_values`` or the admin form). Units
and categories are corrected the same way; existing rows are never
overwritten from here.
"""

from __future__ import annotations

_S = "STEUERUNG"
_I = "INFORMATION"

DEFAULT_KPIS: list[dict] = [
    # --- Steuerungskennzahlen (Kap. 3) ---
    {"key": "neu_gebaute_gleis_km", "name": "Neu gebaute Gleiskilometer", "unit": "km", "kind": _S, "category": "AUS_NEUBAU"},
    {"key": "umsetzung_kmm", "name": "Umsetzung Kleiner und Mittlerer Maßnahmen (KMM)", "unit": "Anzahl", "kind": _S, "category": "AUS_NEUBAU"},
    {"key": "elektrifizierungsgrad", "name": "Elektrifizierte Streckenkilometer", "unit": "km", "kind": _S, "category": "AUS_NEUBAU"},
    {"key": "korridorsanierungen_strecken_km", "name": "Streckenkilometer Korridorsanierungen", "unit": "km", "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "anlagenbedingte_verspaetungsminuten", "name": "Anlagenbedingte Verspätungsminuten", "unit": None, "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "laermsanierte_strecken_km", "name": "Lärmsanierte Streckenkilometer", "unit": "km", "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "bahnhoefe_zielbild", "name": "Bahnhöfe nach abgestimmtem Zielbild (Bau- und Ausstattungsstandards)", "unit": "Anzahl", "kind": _S, "category": "BESTANDSNETZ"},
    {"key": "etcs_strecken_km", "name": "ETCS-Streckenkilometer", "unit": "km", "kind": _S, "category": "UEBERGEORDNET"},
    # --- Informationskennzahlen (Anhang I) ---
    {"key": "betriebsleistung", "name": "Betriebsleistung", "unit": None, "kind": _I, "category": None},
    {"key": "kapazitaetsauslastung", "name": "Kapazitätsauslastung", "unit": None, "kind": _I, "category": None},
    {"key": "mittelherkunft_mitteleinsatz", "name": "Mittelherkunft und Mitteleinsatz", "unit": None, "kind": _I, "category": None},
    {"key": "bp_einreichung_pf_unterlagen", "name": "Bedarfsplan: Einreichung Planfeststellungsunterlagen", "unit": None, "kind": _I, "category": None},
    {"key": "bp_bundeshaushaltsmittel", "name": "Bedarfsplan: Bundeshaushaltsmittel", "unit": None, "kind": _I, "category": None},
    {"key": "serviceeinrichtungen", "name": "Aus- und Neubau von Serviceeinrichtungen", "unit": None, "kind": _I, "category": None},
    {"key": "elektrische_betriebsleistung", "name": "Elektrische Betriebsleistung", "unit": None, "kind": _I, "category": None},
    {"key": "einhaltung_sperrpausen", "name": "Einhaltung von Sperrpausen", "unit": None, "kind": _I, "category": None},
    {"key": "trassenstornierungen", "name": "Trassenstornierungen", "unit": None, "kind": _I, "category": None},
    {"key": "langsamfahrstellen", "name": "Langsamfahrstellen", "unit": None, "kind": _I, "category": None},
    {"key": "stellwerksbesetzungsquote", "name": "Stellwerksbesetzungsquote", "unit": None, "kind": _I, "category": None},
    {"key": "laermsanierung_entlastete_anwohner", "name": "Lärmsanierung: Entlastete Anwohner", "unit": None, "kind": _I, "category": None},
    {"key": "bahnhoefe_betriebliche_standards", "name": "Bahnhöfe (Betriebliche Standards)", "unit": None, "kind": _I, "category": None},
    {"key": "bahnhoefe_anschlussmobilitaet", "name": "Bahnhöfe (Anschlussmobilität und Vorplatz)", "unit": None, "kind": _I, "category": None},
    {"key": "barrierefreie_bahnsteige", "name": "Barrierefreie Bahnsteige", "unit": None, "kind": _I, "category": None},
    # Charts with km and % are two KPIs each; listed last so the order of the
    # others stays, ``sort_order`` puts them next to their km partner.
    {"key": "elektrifizierungsgrad_prozent", "name": "Elektrifizierungsgrad", "unit": "%", "kind": _S, "category": "AUS_NEUBAU", "sort_order": 25},
    {"key": "etcs_ausruestungsgrad", "name": "ETCS-Ausrüstungsgrad", "unit": "%", "kind": _S, "category": "UEBERGEORDNET", "sort_order": 75},
]
