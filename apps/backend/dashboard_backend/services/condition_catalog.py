"""Fixed vocabulary of the InfraGO-Zustandsbericht: domains, scopes, metrics,
Länder and the asset classes seeded on first use.

See docs/features/feature-zustandsbericht.md ("Datenmodell").
"""

from __future__ import annotations

DOMAINS = ("FAHRWEG", "PERSONENBAHNHOF")

# GESAMT = whole network / whole station portfolio; HLN/FLN/SE only for the
# Fahrweg; LAND with ``region``.
SCOPES = ("GESAMT", "HLN", "FLN", "SE", "LAND")
FAHRWEG_ONLY_SCOPES = ("HLN", "FLN", "SE")

SCOPE_LABELS = {
    "GESAMT": "Gesamtnetz",
    "HLN": "Hochleistungsnetz",
    "FLN": "Flächennetz",
    "SE": "Serviceeinrichtungen",
    "LAND": "Bundesland",
}

# metric → (unit, needs grade)
METRICS: dict[str, tuple[str, bool]] = {
    "WBW": ("Mrd. €", False),
    "WBW_BEWERTET": ("Mrd. €", False),
    "WBW_ANTEIL": ("%", False),
    "NOTE": ("Note", False),
    "VERTEILUNG_WBW": ("%", True),
    "VERTEILUNG_MENGE": ("Menge", True),
    "MENGE_BEWERTET": ("Menge", False),
    "MENGE_GESAMT": ("Menge", False),
    "ERNEUERUNGSBEDARF_MENGE": ("Menge", False),
    "ERNEUERUNGSBEDARF_MRD": ("Mrd. €", False),
    "NACHHOLBEDARF_MRD": ("Mrd. €", False),
}

GRADES = (1, 2, 3, 4, 5, 6)
GRADE_LABELS = {
    1: "Neuwertig",
    2: "Gut",
    3: "Mittelmäßig",
    4: "Schlecht",
    5: "Mangelhaft",
    6: "Einschränkend",
}

LAENDER = {
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}

# key, domain, trade, name, unit — in the order of the report's tables.
DEFAULT_CLASSES: tuple[tuple[str, str, str | None, str, str], ...] = (
    ("fw_bruecken", "FAHRWEG", "KIB", "Brücken", "Stk."),
    ("fw_tunnel", "FAHRWEG", "KIB", "Tunnel", "Stk."),
    ("fw_stuetzbauwerke", "FAHRWEG", "KIB", "Stützbauwerke", "km"),
    ("fw_durchlaesse", "FAHRWEG", "KIB", "Durchlässe", "Stk."),
    ("fw_laermschutzbauwerke", "FAHRWEG", "KIB", "Lärmschutzbauwerke", "km"),
    ("fw_gleise", "FAHRWEG", "OB", "Gleise", "km"),
    ("fw_weichen", "FAHRWEG", "OB", "Weichen", "Stk."),
    ("fw_bahnuebergaenge", "FAHRWEG", "LST", "Bahnübergänge", "Stk."),
    ("fw_stellwerke", "FAHRWEG", "LST", "Stellwerke", "Stk."),
    ("fw_oberleitung", "FAHRWEG", "ET", "Oberleitung", "km"),
    ("fw_weichenheizanlagen", "FAHRWEG", "ET", "Weichenheizanlagen", "Stk."),
    ("pb_bahnsteige", "PERSONENBAHNHOF", None, "Bahnsteige", "Stk."),
    ("pb_personenunterfuehrungen", "PERSONENBAHNHOF", None, "Personenunterführungen", "Stk."),
    (
        "pb_unterirdische_personenverkehrsanlagen",
        "PERSONENBAHNHOF",
        None,
        "Unterirdische Personenverkehrsanlagen",
        "Stk.",
    ),
    ("pb_treppen_rampen", "PERSONENBAHNHOF", None, "Treppen, Rampen, Wetterschutz etc.", "Stk."),
    ("pb_bahnsteigdaecher", "PERSONENBAHNHOF", None, "Bahnsteigdächer", "Stk."),
    ("pb_bahnsteighallen", "PERSONENBAHNHOF", None, "Bahnsteighallen", "Stk."),
    ("pb_personenaufzuege", "PERSONENBAHNHOF", None, "Personenaufzüge", "Stk."),
    ("pb_itk_anlagen", "PERSONENBAHNHOF", None, "ITK-Anlagen", "Stk."),
    ("pb_fahrtreppen", "PERSONENBAHNHOF", None, "Fahrtreppen", "Stk."),
    # Not in Tab. 7 (excluded from its WBW), but its grade is a headline figure.
    ("pb_empfangsgebaeude", "PERSONENBAHNHOF", None, "Empfangsgebäude", "Stk."),
)

TRADE_LABELS = {
    "KIB": "Ingenieurbauwerke",
    "OB": "Oberbau",
    "LST": "Leit- und Sicherungstechnik",
    "ET": "Elektrotechnik",
}
