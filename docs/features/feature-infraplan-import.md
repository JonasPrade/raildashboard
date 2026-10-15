# Feature: Infraplan-Import

> **Status: geplant, mit dem Nutzer abgestimmt (2026-10-15).** Grundlage ist der
> Infraplan 2026 (BMV, 6. Oktober 2026). Ein Prototyp-Parser (pdfplumber, ohne LLM)
> hat daraus die Maßnahmentabellen gelesen; die Zahlen unten stammen aus diesem Lauf.
> Das PDF liegt vorübergehend unter `docs/261002_Infraplan_2026_1.pdf` und wird
> gelöscht, sobald die Test-Fixture daraus erzeugt ist (Stufe 1). Künftige Jahrgänge
> kommen **nur über den Upload im Frontend** ins System.

## Ziel

Der **Infraplan** ist der jährlich fortgeschriebene Fünfjahresplan des Bundes für die
Schieneninfrastruktur (Infraplan 2026 = 2026–2030). Er enthält

- je **Maßnahme**: Realisierungsstand/Leistungsphase, geplantes Inbetriebnahmejahr,
  Gesamtwertumfang (GWU) bzw. Gesamtkosten, Stand der parlamentarischen Befassung;
- **Kennzahlen**: 8 Steuerungskennzahlen und 15 Informationskennzahlen mit Ist-Werten
  (Rückschau) und Zielwerten je Jahr.

Der Import macht beides nutzbar und baut über die Jahrgänge **Zeitreihen** auf:
Kostenentwicklung und Terminverschiebungen je Projekt, Soll/Ist je Kennzahl. Kein
Jahrgang überschreibt einen anderen — jeder Wert behält seinen Jahrgang, damit
Vergleiche (Infraplan 2026 vs. 2027 vs. …) dauerhaft möglich bleiben.

---

## Entscheidungen (Grilling 2026-10-14/15)

| # | Frage | Entscheidung |
|---|---|---|
| 1 | Umfang | Maßnahmentabellen Kap. 2.3 **und alle Kennzahlen** (Steuerungs- + Informationskennzahlen). Kennzahl-Maßnahmenlisten im Anhang (nur Name + Jahr) vorerst nicht |
| 2 | GVFG-Vorhaben | wie Bedarfsplan behandeln — sie gehören ins Dashboard |
| 3 | Granularität | Zeilen werden **Teilprojekten** zugeordnet; unklare Fälle manuell |
| 4 | Vertrauen | hoch: Bedarfsplan/InvKG **0.85**, GVFG **0.75** (Länderangaben, laut Fn. 23 unplausibilisiert) |
| 5 | Kosten | Infraplan = **Gesamtkostenprognose** (Kopfzahl); Haushalt/FinVe = **vom Bund zugesicherte Mittel** (daneben) |
| 6 | Review-Vorauswahl | Projektnummer-Treffer und Fuzzy ≥ 0.85 vorausgewählt, Rest leer |
| 7 | Befassung „nicht vereinbart“ | Projekt hat keine parlamentarische Befassung |
| 8 | PDF-Quelle | nur Upload im Frontend; das PDF im Repo war einmalig |
| 9 | Kennzahlen-Erfassung | per **MCP + Skill** (KI liest Diagramme); manuelles Formular als Rückfall |
| 10 | Kennzahlen-Modell | generisch, alle Kennzahlen inkl. Anhang |
| 11 | Zeitreihen | Werte aller Jahrgänge bleiben erhalten |
| 12 | Anzeige Kennzahlen | neue **öffentliche Seite** `/infraplan`; Startseite bleibt vorerst unverändert |
| 13 | Rangfolge Termine | Infraplan schlägt VIB-PFA, Fulda-Runde und BVWP, aber nicht manuelle Termine |
| 14 | Deckungsgrad | **nicht** anzeigen (andere Organisationen finanzieren mit) |
| 15 | PaBe-Relevanz | eigene Ebene „laut Infraplan“: manuell > Infraplan > Projektgruppen |
| 16 | Fehlendes Teilprojekt | Review bietet „Teilprojekt anlegen unter …“ |
| 17 | Maßnahme fehlt im neuen Jahrgang | Hinweis im Projektdetail, Liste im Review; kein Einfluss auf die Phase |
| 18 | Zwei Wege | **manuell** im Frontend und **per MCP** mit gleichem Ergebnis |
| 19 | Autonomie MCP | Agent darf alles bis einschließlich Bestätigen und Kennzahlen eintragen — Halt nur bei Parser-Warnungen |
| 20 | KI-Kennzahlen | Status „ungeprüft“, öffentlich erst nach Freigabe |
| 21 | Skills | Ordner `skills/` im Repo (`skills/infraplan-import/SKILL.md`); Upload nach claude.ai von Hand |
| 22 | GVFG: Infraplan vs. GVFG-Bundesprogramm | Es gilt der **jüngere Stand** (Stand-Datum der GVFG-Ausgabe vs. Veröffentlichungsdatum des Infraplans) — für Lph, Inbetriebnahme und Kosten |
| 23 | Summen in der Projekthierarchie | **Grundsatz für alle Projekte:** Elternprojekte bilden Summen über ihre Teilprojekte (auch reine GVFG-Elternprojekte) — siehe `docs/architecture.md` → „Grundsätze“ |

---

## Aufbau des Dokuments (Infraplan 2026)

160 Seiten: Hauptteil (S. 1–77) und Anhang (S. 78–160, eigene Seitenzählung).

### Maßnahmentabellen (Kap. 2.3, S. 32–56)

| Abschnitt | Kennung | Zeilen | Realisierungsstand | Kostenspalte |
|---|---|---|---|---|
| Bedarfsplan, Teil A – im Bau und/oder mit durchgängigem Baurecht (Lph 4–9) | `BP_A` | 38 | `Bau` · `Lph 4 abgeschlossen – durchgängiges Baurecht vorliegend` | GWU in Mio. € |
| Bedarfsplan, Teil B – Entwurfs- und Genehmigungsplanung (Lph 3–4) | `BP_B` | 40 | `Lph 3-4` | GWU |
| Bedarfsplan, Teil C – Vorplanung (Lph 1–2) | `BP_C` | 69 | `Lph 1` · `Lph 1-2` | GWU |
| Bedarfsplan, Teil D – Grundlagenermittlung (noch keine Lph) | `BP_D` | 71 | leer | GWU |
| GVFG, Kat. A – endgültig ins Bundesprogramm aufgenommene DB-Vorhaben | `GVFG_A` | 35 | `Lph 5 - 9`, `Lph 3 - 4`, `offen`, … | Gesamtkosten in Mio. € |
| GVFG, Kat. C – bedingt aufgenommene DB-Vorhaben | `GVFG_C` | 42 | wie Kat. A | Gesamtkosten |
| InvKG – Maßnahmen im Bau | `INVKG` | 5 | `Bau` | GWU |

Summe **300 Zeilen**.

**Spalten Bedarfsplan:** `Laufende Nummer | Projektnummer` · `Bezeichnung` · `Maßnahme` ·
`Land` · `Realisierungsstand / Lph` · `Geplante Inbetriebnahme` · `GWU in Mio. €` ·
`Parlamentarische Befassung`. **GVFG/InvKG:** ohne `Bezeichnung` und ohne Befassung;
GVFG heißt die Terminspalte „Geplante oder tatsächliche Inbetriebnahme“.

Beispielzeile (Teil A, S. 34):

```
20 | E.1637290101 · PB 03: ABS Magdeburg – Stendal – Uelzen (Ostkorridor Nord)
   · 2gl. Einbindung Bf Stendal und Ausbau Str. bis Hohenwulsch und Salzwedel – Uelzen
   · Niedersachsen/Sachsen-Anhalt · Bau · 2030 · 1.720,48¹⁴ · nicht vereinbart
```

### Kennzahlen

- **Steuerungskennzahlen** (Kap. 3, S. 57–72): Neu gebaute Gleiskilometer · Umsetzung
  Kleiner und Mittlerer Maßnahmen (KMM) · Elektrifizierungsgrad (elektrifizierte
  Strecken-km) · Streckenkilometer Korridorsanierungen · Anlagenbedingte
  Verspätungsminuten · Lärmsanierte Streckenkilometer · Bahnhöfe nach abgestimmtem
  Zielbild (Bau- und Ausstattungsstandards) · ETCS-Streckenkilometer und -Ausrüstungsgrad.
- **Informationskennzahlen** (Anhang I, S. 85–101): Betriebsleistung ·
  Kapazitätsauslastung · Mittelherkunft und Mitteleinsatz · Bedarfsplan: Einreichung
  Planfeststellungsunterlagen · Bedarfsplan: Bundeshaushaltsmittel · Aus- und Neubau von
  Serviceeinrichtungen · Elektrische Betriebsleistung · Einhaltung von Sperrpausen (ab
  2027) · Trassenstornierungen · Langsamfahrstellen · Stellwerksbesetzungsquote ·
  Lärmsanierung: Entlastete Anwohner · Bahnhöfe (Betriebliche Standards) · Bahnhöfe
  (Anschlussmobilität und Vorplatz) · Barrierefreie Bahnsteige.

Die Werte stehen **nur als Diagrammbeschriftungen** im PDF: Nullwerte sind nicht
beschriftet, Ist- und Zielreihen stehen ohne Bezug nebeneinander, die KMM-Balken sind
nach Teilprogrammen gestapelt. Ein deterministisches Auslesen ist nicht verlässlich —
deshalb liest die KI die Seitenbilder (MCP-Weg) oder der Nutzer trägt ein (manueller
Weg). Begleittexte enthalten Summen („Zwischen 2020 und 2025 wurden in Summe 266 Gleis-km
in Betrieb genommen“), die sich als Gegenprobe eignen.

### Besonderheiten, die der Parser abdecken muss

| Fall | Beispiel | Behandlung |
|---|---|---|
| Mehrere Projektnummern | `E.1637230040 // X.016030472300201` | Liste; erste = Hauptnummer |
| Projektnummer-Formate | `E.16…` (DB InfraGO), `T.016…`/`G.016…`/`X.016…`, GVFG `07 D 2825_A`, InvKG `6)` bzw. „InvKG Nr. 6“ | Rohtext speichern; `E.`-, GVFG- und InvKG-Nummer als Wiedererkennungs-Schlüssel |
| Hochgestellte Fußnoten kleben an Werten | `1.720,48` + ¹⁴ → Text `1.720,4814` | Wörter mit kleinerer Schriftgröße **vor** dem Zusammensetzen abtrennen → `footnote_refs` |
| Kostenverweis statt Zahl | `Ref. Teil B 20 \| E.1637290100` | `cost_mio = NULL`, `cost_ref_raw` speichern und nach dem Parse auf den Zieleintrag auflösen |
| Sammel-GWU per Fußnote | Fn. 14: „GWU 1.720,48 Mio. € bezieht sich auf Teil A 20 und Teil A 33“ | Fußnotentext am Eintrag speichern und im Review anzeigen |
| Inbetriebnahme nicht als Jahr | `offen`, `bis 2035`, `2029/2030`, `2023/2024`, `2022–2029` | `ibn_raw` + `ibn_year` (späteres Jahr) + `ibn_qualifier` (`OFFEN`/`BIS`/`SPANNE`) |
| GVFG-Termin in der Vergangenheit | `2019` (Restarbeiten laut Fn. 23) | speichern, **nicht** als erwartete Inbetriebnahme verwenden |
| Silbentrennung über Zeilen | `Lehr- ter Stamm- bahn` | Trennstrich am Zeilenende entfernen |
| Seite ohne erkannte Kopfzeile | Teil D und GVFG Kat. A auf Folgeseiten | Spaltengrenzen der letzten Kopfzeile desselben Abschnitts übernehmen |
| Fußnotenbereich am Seitenende | Fn. 12–14 unter der Tabelle | Bereich ab der ersten kleinen Fußnotenziffer am linken Rand abschneiden; Fußnotentexte separat einlesen |

**Plausibilitätsprüfung:** Die laufende Nummer ist je Abschnitt lückenlos `1..n`. Der
Parser meldet Lücken und Dubletten in `warnings_json`. Das ist die wichtigste
Absicherung gegen Layoutänderungen späterer Jahrgänge — und das Signal, an dem der
MCP-Weg anhält (siehe unten).

---

## Zwei Wege, ein Ergebnis

Beide Wege nutzen dieselben Backend-Funktionen; der MCP-Weg ruft nur andere
Einstiegspunkte auf. Hochgeladen wird **immer im Frontend**.

| Schritt | Manuell (Frontend) | MCP + Skill (KI) |
|---|---|---|
| 1 Hochladen | `InfraplanImportPage`, Jahrgang angeben | — (Nutzer hat im Frontend hochgeladen) |
| 2 Auslesen | startet automatisch nach dem Upload (Celery) | `start_infraplan_parse` (erneutes Auslesen) / Status abfragen |
| 3 Sichere Zuordnungen | vorausgewählt im Review | `apply_infraplan_suggestions(min_confidence=0.85)` |
| 4 Unsichere Zeilen | Nutzer wählt im MultiSelect | Agent sucht (`list_projects`, Geometrie, Texte) und ordnet begründet zu |
| 5 Fehlendes Teilprojekt | Schaltfläche „Teilprojekt anlegen unter …“ | `create_infraplan_subproject` |
| 6 Bestätigen | Schaltfläche „Übernehmen“ | `confirm_infraplan_import` — **nur ohne Parser-Warnungen** |
| 7 Kennzahlen | Formular (Jahr × Wert × Ist/Ziel) — Einträge gelten als geprüft | Agent liest Seitenbilder (`get_infraplan_page_image`), gleicht mit Textsummen ab, schreibt mit `set_infraplan_kpi_values` — Status **ungeprüft** |
| 8 Rest | „Offene Zuordnungen“ | Agent berichtet, was offen blieb und was er selbst entschieden hat; Rest unter „Offene Zuordnungen“ |
| 9 Freigabe | — | Nutzer gibt die Kennzahlen des Jahrgangs in der Admin-Ansicht frei (Werte neben Diagrammbild) |

Alle schreibenden Schritte stehen im Änderungsprotokoll mit Nutzer bzw. API-Key.
Ein Jahrgang lässt sich vollständig löschen und neu einlesen; damit ist auch die
Bestätigung durch den Agenten umkehrbar.

---

## Pipeline (Auslesen)

| Stufe | Was passiert | Wo (neu) |
|---|---|---|
| 1 Textgewinnung | pdfplumber, Wörter **mit Schriftgröße** (`extra_attrs=["size"]`); Spaltengrenzen aus der Kopfzeile (`find_tables()[0]`) | `tasks/infraplan.py` |
| 2 Segmentierung | Abschnitte über die Überschriften `Bedarfsplan, Teil A–D`, `GVFG, Kat. A/C`, `InvKG`; Zeilen an der laufenden Nummer in Spalte 1; Fußnotenzone abschneiden | `tasks/infraplan.py` |
| 3 Semantik | Kopfzeile → kanonisches Schema (deterministisch über Spaltentitel, Muster `haushalt_columns`); Werte normalisieren (deutsche Zahlen, Jahr, Lph, Befassung) | `tasks/infraplan_columns.py` |
| 4 Matching | Vorschläge je Zeile, siehe [Zuordnung](#zuordnung-zu-projekten) | `tasks/infraplan_matching.py` |
| 5 Kennzahl-Seiten | Seitenzahlen der Kennzahl-Diagramme merken (Überschrift „Steuerungskennzahl:“ / „Informationskennzahl:“) für die Bildausgabe | `tasks/infraplan.py` |

Das hochgeladene PDF wird je Entwurf gespeichert (Seitenbilder für MCP und Freigabe-
Ansicht werden bei Bedarf mit pymupdf gerendert). OCR ist nicht nötig; fehlt einem
künftigen Jahrgang der Textlayer, kann `services/document_ocr.py` nachgerüstet werden.

---

## Datenmodell

Neue Tabellen (Migration via `make migrate-create`, rein additiv):

**`infraplan_parse_result`** — Entwurf je Upload (Muster `haushalts_parse_result`)
- `id`, `year`, `status`, `result_json`, `warnings_json`, `error_message`, `file_name`,
  `pdf_path` (gespeicherte Datei), `kpi_pages_json`, `created_at`, `confirmed_at`,
  `confirmed_by_snapshot`

**`infraplan_report`** — bestätigter Jahrgang
- `id`, `year` (unique), `title`, `published_on` (Date), `parse_result_id`, `created_at`

**`infraplan_entry`** — eine Tabellenzeile
- `report_id` (FK, CASCADE), `section` (`BP_A` … `INVKG`), `lfd_nr`, `page`
- `project_numbers` (JSON-Liste), `primary_number` (String, indiziert)
- `bezeichnung`, `massnahme`, `laender` (Rohtext)
- `state_raw`, `lph_from`, `lph_to` (Int, nullable), `under_construction`, `baurecht` (Bool)
- `ibn_raw`, `ibn_year` (Int, nullable), `ibn_qualifier`
- `cost_mio` (Numeric(12,2), nullable), `cost_kind` (`GWU` | `GESAMTKOSTEN`),
  `cost_ref_raw`, `cost_ref_entry_id` (FK self, nullable)
- `parl_raw`, `parl_state` (`ABGESCHLOSSEN` | `LAEUFT` | `VORGESEHEN` | `NICHT_VEREINBART` | NULL)
- `footnote_refs` (JSON), `footnotes` (JSON: `{nr: text}`)
- Unique `(report_id, section, lfd_nr)`

**`infraplan_entry_project`** — m:n-Zuordnung (Muster `vib_entry_project`)
- `entry_id`, `project_id`, `assigned_by_snapshot`, `assignment_source`
  (`NUMBER` | `FUZZY` | `MANUAL` | `AGENT`), `note` (Begründung des Agenten), `created_at`

**`infraplan_kpi`** — Kennzahl-Definition, jahrgangsübergreifend
- `key` (unique, stabil, z. B. `neu_gebaute_gleis_km`), `name`, `unit`, `kind`
  (`STEUERUNG` | `INFORMATION`), `category` (`AUS_NEUBAU` | `BESTANDSNETZ` | `UEBERGEORDNET`),
  `description`, `sort_order`

**`infraplan_kpi_value`** — ein Wert
- `report_id` (FK, CASCADE — der Jahrgang, **aus dem** der Wert stammt), `kpi_id`,
  `year` (Bezugsjahr), `value_kind` (`IST` | `ZIEL`), `series` (nullable; Teilreihe,
  z. B. KMM-Teilprogramm oder TEN-Netzebene), `value` (Numeric), `source_page`,
  `status` (`UNGEPRUEFT` | `GEPRUEFT`), `entered_by_snapshot`, `created_at`
- Unique `(report_id, kpi_id, year, value_kind, series)`

**`progress_observation`** — neue nullable Spalte `infraplan_entry_id` (FK, SET NULL).
`SourceType` bekommt `INFRAPLAN` (plain String, keine Enum-Migration).

**`project_progress`** — keine neue Spalte für die PaBe-Relevanz; die Ebene „laut
Infraplan“ wird beim Auflösen aus dem neuesten zugeordneten Eintrag gelesen (siehe unten).

Eine Projektnummer-Spalte am `Project` gibt es **nicht**: Die Wiedererkennung im
Folgejahr läuft über die bestätigten Zuordnungen (`primary_number` → Projekt).

---

## Zuordnung zu Projekten

Reihenfolge je Zeile:

1. **Projektnummer aus früheren Jahrgängen** — bestätigte Zuordnung für dieselbe
   `primary_number` → Vorschlag mit Konfidenz 1.0 (vorausgewählt).
2. **Fuzzy-Matching** über `Bezeichnung + Maßnahme` mit den Funktionen aus
   `tasks/vib_matching.py` (VDE-Nummer, `_score`). Präfixe wie `PB 07:` werden vorher
   entfernt. **Teilprojekte werden bevorzugt**: passt ein Teilprojekt, schlägt der
   Matcher es statt des übergeordneten Projekts vor. Ab Konfidenz 0.85 vorausgewählt.
   **GVFG-Zeilen** werden zuerst über den normalisierten GVFG-Schlüssel gegen
   `Project.project_number` abgeglichen — GVFG-Projekte tragen dort ihren Schlüssel
   (`feature-gvfg-import.md` → „Zuordnung zu Projekten“, gleicher Normalisierer, im
   Code gemeinsam nutzen). Ein exakter Treffer zählt wie ein Projektnummer-Treffer.
3. **Kein Treffer** → im Review leer; nach der Bestätigung in `/admin/unassigned`
   (Sektion „Infraplan“) mit „Projektentwurf anlegen“.

Fehlt zu einer Abschnittszeile (z. B. „PB 07 Abschnitt 9.2“) das Teilprojekt, legt
„Teilprojekt anlegen unter …“ ein Teilprojekt mit dem Namen aus der Zeile unter dem
gewählten Projekt an (Entwurf ohne Geometrie) und ordnet die Zeile zu.

Mehrere Zeilen können auf dasselbe Projekt zeigen, eine Zeile kann mehreren Projekten
zugeordnet werden (m:n).

**Abgleich mit dem Vorjahr:** Das Review listet zusätzlich die Projekte, die im
vorigen Jahrgang einen Eintrag hatten und im neuen keinen — damit Umbenennungen von
Hand zugeordnet werden können.

---

## Übernahme in den Projektfortschritt

Neue Mapper-Funktion `infraplan_entry_to_specs` in `services/progress_materialization.py`;
die Rows sind `is_derived=True` und werden über `sync_derived_observations` idempotent
neu erzeugt. Es zählt der **neueste** Jahrgang je Projekt. `SOURCE_TYPE_DEFAULT_TRUST`:
`INFRAPLAN = 0.85`; GVFG-Zeilen bekommen explizit 0.75 und fließen nur ein, wenn der
Infraplan-Jahrgang **jünger** ist als die neueste GVFG-Ausgabe mit demselben Schlüssel
(Entscheidung 22; sonst liefert der GVFG-Eintrag Lph und Inbetriebnahme). `observed_date` =
Veröffentlichungsdatum des Jahrgangs.

**Track MAIN** (Untergrenze der Hauptphase):

| Realisierungsstand | MainPhase |
|---|---|
| `Bau` (BP_A, InvKG) | `BAU` |
| `Lph 4 abgeschlossen – durchgängiges Baurecht` | `GENEHMIGUNGSPLANUNG` + Track PF `ABGESCHLOSSEN` |
| `Lph 3-4` | `GENEHMIGUNGSPLANUNG` |
| `Lph 1`, `Lph 1-2` | `VORPLANUNG` |
| BP_D (keine Lph) | `NICHT_GESTARTET` |
| GVFG `Lph 5 - 9`, `Lph 5 - 7`, `Lph 5` | `BAU` |
| GVFG `Lph 3 - 4`, `Lph 4` | `GENEHMIGUNGSPLANUNG` |
| GVFG `Lph 1 - 2` | `VORPLANUNG` |
| GVFG `Lph 1 - 4`, `Lph 1 - 9`, `offen` | keine Observation |

**Track PARL** (nur Bedarfsplan):

| Befassung | ParallelState | PaBe-Relevanz (Ebene „laut Infraplan“) |
|---|---|---|
| `abgeschlossen – Entschließung BT liegt vor` | `ABGESCHLOSSEN` | relevant |
| `Übergabe seitens DB InfraGO AG erfolgt – Verfahren läuft` | `LAEUFT` | relevant |
| `vorgesehen` | keine Observation | relevant |
| `nicht vereinbart` | keine Observation | **nicht relevant** |

**PaBe-Relevanz:** `resolve_parl_relevant` (`crud/projects/progress.py`) bekommt eine
mittlere Ebene: manuelle Festlegung (`parl_befassung_relevant` ≠ NULL) > **neuester
zugeordneter Infraplan-Eintrag mit Befassungsangabe** > Default aus den Projektgruppen.
Der Import schreibt nie in `parl_befassung_relevant`. Ändert sich die Angabe im nächsten
Jahrgang, folgt die Anzeige automatisch.

**Prognose:** `concrete_milestone_dates` (`services/progress_forecast.py`) bekommt den
Eingang `infraplan: list[(MainPhase.IN_BETRIEB, date)]` mit Quelle `"Infraplan"`.
Datum = 31.12. des `ibn_year`, Anzeige nur als Jahr. Rangfolge: BVWP-Schätzung <
VIB-PFA < Fulda-Runde < **Infraplan** < Manuell. Kein Eingang bei `ibn_qualifier = OFFEN`
oder einem Jahr vor dem Jahrgang (GVFG-Altfälle). Mehrere Einträge je Projekt →
spätestes Jahr. Die Multi-Projekt-Zeitleiste nutzt dieselbe Funktion und übernimmt das
automatisch.

---

## Kosten

- **Gesamtkostenprognose** (Kopfzahl im Projektdetail, oberer Kostenblock):
  - Projekt mit eigener Zeile → deren `cost_mio` (bzw. der über `cost_ref_entry_id`
    aufgelöste Wert, wenn die Zeile auf einen anderen Eintrag verweist);
  - übergeordnetes Projekt ohne eigene Zeile → Summe der Teilprojekte (Grundsatz für
    **alle** Projekte, auch reine GVFG-Elternprojekte);
  - Sammel-GWU und Verweise zählen **einmal**, beim tragenden Eintrag (Deduplizierung
    über die Eintrags-ID).
  - Beschriftung: „Gesamtkostenprognose (Infraplan 2026)“; bei GVFG „Gesamtkosten
    (Länderangabe, Infraplan 2026)“. Fußnoten als Tooltip.
- **Vom Bund zugesichert** — daneben die FinVe-Mittel aus dem Haushalt (bestehende
  Daten, nur neu beschriftet und in denselben Block gezogen).
- **Kein Deckungsgrad** — andere Organisationen finanzieren mit, ein Verhältnis wäre
  irreführend.

---

## Anzeige

**Projektdetail, Abschnitt „Infraplan“** (nur wenn Einträge zugeordnet sind): Zeile je
Jahrgang und Eintrag mit Abschnitt, Realisierungsstand, geplanter Inbetriebnahme,
Kosten, Befassung; ab dem zweiten Jahrgang Delta-Spalten („GWU +12 %“, „IBN 2028 →
2030“). Hinweis „nicht mehr im Infraplan 20xx“, wenn das Projekt im neuesten Jahrgang
fehlt, zuvor aber enthalten war. Mobil über `ResponsiveTable`.

**Öffentliche Seite `/infraplan`:** Kennzahlen gruppiert nach Kategorie, je Kennzahl ein
Diagramm: Ist-Werte aus dem neuesten Jahrgang als Balken/Linie, Zielwerte **jedes**
Jahrgangs als eigene Linie („Ziel IP 2026“, „Ziel IP 2027“), sodass Zielverschiebungen
sichtbar sind. Teilreihen (`series`) als Stapel/Legende. Nur Werte mit Status
`GEPRUEFT`. Darunter je Jahrgang die Liste der Maßnahmen mit Link aufs Projekt.
Navigationseintrag „Infraplan“. Die Startseite bleibt vorerst unverändert.

**Admin-Ansicht Kennzahlen** (`/admin/infraplan/kpis/:year`): Formular für den
manuellen Weg (Kennzahl × Jahr × Ist/Ziel × Teilreihe) und Freigabe-Ansicht für den
MCP-Weg — Werte neben dem gerenderten Diagrammbild der Quellseite, „Jahrgang
freigeben“ setzt alle Werte auf `GEPRUEFT`.

---

## API

Prefix `/import/infraplan`, Recht `infraplan.import` (neu, `GROUP_FINANCING`, in
`_EDITOR_PERMISSIONS`):

| Methode | Pfad | Zweck |
|---|---|---|
| POST | `/parse` | PDF hochladen, Task startet automatisch (`year` als Formularfeld) |
| POST | `/parse-result/{id}/reparse` | erneut auslesen (gleiche Datei) |
| GET | `/parse-result`, `/parse-result/{id}` | Entwürfe listen / laden (inkl. Warnungen, Vorjahresabgleich) |
| DELETE | `/parse-result/{id}` | Entwurf verwerfen |
| PATCH | `/parse-result/{id}/rows/{row}` | Zuordnung/Werte einer Zeile im Entwurf ändern |
| POST | `/parse-result/{id}/apply-suggestions` | Vorschläge ab Schwelle übernehmen |
| POST | `/parse-result/{id}/rows/{row}/subproject` | Teilprojekt anlegen und zuordnen |
| GET | `/parse-result/{id}/page/{page}.png` | Seitenbild (für Freigabe und MCP) |
| POST | `/confirm` | Entwurf übernehmen; 409, wenn der Jahrgang existiert oder Warnungen offen sind (`force` nur im Frontend) |
| DELETE | `/report/{year}` | Jahrgang löschen (Einträge, Zuordnungen, Kennzahlwerte) |
| PUT | `/report/{year}/kpi-values` | Kennzahlwerte setzen (Status je nach Weg) |
| POST | `/report/{year}/kpi-values/approve` | Kennzahlwerte freigeben |

Lesend (öffentlich wie die übrigen Projektdaten): `GET /projects/{id}/infraplan`,
`GET /infraplan/kpis` (nur geprüfte Werte, alle Jahrgänge), `GET /infraplan/reports`.

Admin: `GET /admin/unassigned-infraplan-entries`,
`PATCH /admin/unassigned-infraplan-entries/{id}/assign` (Recht `assignment.manage`).

---

## Frontend

- `src/features/infraplan-import/`: `InfraplanImportPage` (Upload + Entwurfsliste),
  `InfraplanReviewPage` (Tabelle je Abschnitt, Warnungen oben, MultiSelect,
  „Teilprojekt anlegen unter …“, Filter „ohne Zuordnung“, Vorjahresabgleich),
  `InfraplanKpiPage` (Formular + Freigabe). Routen `admin/infraplan-import`,
  `…/review/:parseResultId`, `admin/infraplan/kpis/:year`.
- `src/features/infraplan/InfraplanPage.tsx` — öffentliche Seite `/infraplan`
  (Diagramme nach dem `dataviz`-Vorgehen, vorhandene Chart-Bibliothek nutzen).
- Sektion in `features/admin/UnassignedPage.tsx`; Abschnitt + Kostenblock in
  `features/projects/`.
- Guide (Slug `infraplan`) in `guides/guideContent.ts` mit beiden Wegen; In-App-Doku
  (`documentationData.ts`) ergänzen. Hooks in `shared/api/queries.ts`, danach
  `make gen-api`. Alles funktioniert bei 360 px.

---

## MCP & Skill

**Abweichung von `feature-mcp-server.md`:** Dort sind Importe aus dem MCP
ausgeklammert. Für den Infraplan wird das bewusst aufgehoben — der Agent soll den
Import so weit abschließen, dass nur unklare Reste übrig bleiben. Alle Tools prüfen
`infraplan.import` über `require(principal, …)`; Lese-Tools sind `READ_ONLY`.

| Tool | Art | Zweck |
|---|---|---|
| `list_infraplan_drafts` | lesend | Entwürfe mit Status, Warnungen, Zuordnungsstand |
| `get_infraplan_draft(id, section?, only_open?)` | lesend | Zeilen mit Vorschlägen, gefiltert |
| `start_infraplan_parse(id)` | schreibend | erneut auslesen |
| `apply_infraplan_suggestions(id, min_confidence)` | schreibend | Vorschläge übernehmen |
| `assign_infraplan_row(id, row, project_ids, note)` | schreibend | Zuordnung mit Begründung (`assignment_source=AGENT`) |
| `create_infraplan_subproject(id, row, parent_id, name?)` | schreibend | Teilprojekt anlegen + zuordnen |
| `confirm_infraplan_import(id)` | schreibend | Jahrgang übernehmen; verweigert bei offenen Warnungen |
| `get_infraplan_page_image(id, page)` | lesend | Seitenbild als Bild-Content |
| `list_infraplan_kpis` / `get_infraplan_kpi_values(year)` | lesend | Definitionen und Werte |
| `set_infraplan_kpi_values(year, values[])` | schreibend | Werte setzen, Status `UNGEPRUEFT`; neue Kennzahl-Definitionen nur mit stabilem `key` |
| `get_project_infraplan(project_id)` | lesend | Einträge aller Jahrgänge eines Projekts |

`list_data_gaps` bekommt die Lücke `infraplan_unassigned`.

**Skill** `skills/infraplan-import/SKILL.md` (neuer Ordner `skills/` für alle
claude.ai-Skills dieses Projekts, mit kurzer `skills/README.md` zum Hochladen):
1. Neuesten Entwurf holen; Warnungen → anhalten und berichten.
2. Vorschläge ≥ 0.85 übernehmen.
3. Offene Zeilen einzeln: Projekt suchen (Name, Strecke, Bundesland, Projektnummer in
   Texten), Teilprojekt bevorzugen, begründet zuordnen oder Teilprojekt anlegen; wirklich
   Unklares offen lassen.
4. Bestätigen.
5. Kennzahl-Seiten als Bild lesen, Werte je Jahr/Art/Teilreihe ablesen, mit den Summen im
   Begleittext gegenprüfen, schreiben.
6. Bericht: übernommen / selbst entschieden (mit Begründung) / offen / Kennzahlen zur
   Freigabe.

---

## Tests

- Fixture `tests/fixtures/infraplan_2026_pages.json`: Wortlisten (Text, Position,
  Schriftgröße) der Seiten 33–56, erzeugt per Skript `scripts/dump_infraplan_pages.py`
  aus dem PDF (Muster `haushalt_ep12_2027_pages.json`). Danach wird
  `docs/261002_Infraplan_2026_1.pdf` gelöscht.
- Parser: Zeilenzahl je Abschnitt (38/40/69/71/35/42/5), lückenlose laufende Nummern,
  Fußnote abgetrennt (`1.720,48` + `[14]`), Kostenverweis aufgelöst, `bis 2035` →
  (2035, `BIS`).
- Mapper: Tabellen MAIN/PF/PARL parametrisiert; PaBe-Relevanz-Ebenen.
- Prognose: Rangfolge Infraplan vs. VIB-PFA/Fulda/Manuell.
- Kosten: Summe über Teilprojekte ohne Doppelzählung von Verweisen.
- Confirm: 409 bei bestehendem Jahrgang und bei Warnungen; Löschen + Neuimport ohne
  Dubletten; Werte früherer Jahrgänge bleiben unberührt.
- Matching: Zuordnung aus Jahrgang N wird in N+1 über die Projektnummer vorgeschlagen.
- MCP: Rechteprüfung, `confirm` verweigert bei Warnungen, KPI-Werte landen `UNGEPRUEFT`.

---

## Abgleich mit `feature-gvfg-import.md`

Der GVFG-Import (eigenes Feature, Quelle: GVFG-Bundesprogramm) überschneidet sich bei
den GVFG-Zeilen des Infraplans (Kat. A/C, 77 Zeilen):

- **Synergie:** Zuordnung über den GVFG-Schlüssel in `project_number` (siehe oben).
- **Entschieden (2026-10-15) — jüngerer Stand gilt:** Für ein GVFG-Vorhaben liefern
  Infraplan und GVFG-Bundesprogramm dieselben Angaben (Lph, Inbetriebnahme,
  Gesamtkosten). Maßgeblich ist die Quelle mit dem **jüngeren Stand** (Stand-Datum der
  GVFG-Ausgabe vs. Veröffentlichungsdatum des Infraplans). Diese Quelle fließt in
  Planungsstand, Prognose und Kostenblock; die andere bleibt in ihrem Abschnitt
  sichtbar. Beim Gleichstand gewinnt der Infraplan. Die Prüfung erfolgt beim
  Materialisieren über den normalisierten Schlüssel.
- **Entschieden (2026-10-15) — Summen überall:** Auch reine GVFG-Elternprojekte bilden
  Summen über ihre Teilprojekte. Das ist ein projektweiter Grundsatz
  (`docs/architecture.md` → „Grundsätze“); `feature-gvfg-import.md` ist angepasst.

## Ausbaustufen

| Stufe | Inhalt | Issue |
|---|---|---|
| 1 | Parser + Datenmodell (inkl. Kennzahl-Tabellen) + Entwurf + Fixture | #179 |
| 2 | Manueller Weg: Review, Teilprojekt anlegen, Vorjahresabgleich, Übernahme, Offene Zuordnungen | #180 |
| 3 | Fortschritt (`INFRAPLAN`), PaBe-Ebene, Prognose, Kostenblock, Projektdetail-Abschnitt | #181 |
| 4 | Kennzahlen: Formular, Freigabe, öffentliche Seite `/infraplan` | #184 |
| 5 | MCP-Tools für den ganzen Ablauf + `skills/infraplan-import/` | #182 |
| später | Kennzahl-Maßnahmenlisten im Anhang (Name + Jahr), Startseite neu ordnen, wenn mehr solcher Übersichten dazukommen | — |

## Akzeptanzkriterien (gesamt)

- [ ] Upload des Infraplans 2026 liefert 300 Zeilen ohne Lücken-Warnung.
- [ ] Nach Bestätigung zeigt „ABS Magdeburg – Stendal – Uelzen“ im Projektdetail Teil A,
      Bau, IBN 2030, Gesamtkostenprognose 1.720,48 Mio. € mit Fußnote, daneben die
      zugesicherten FinVe-Mittel.
- [ ] Der Fortschritt dieses Projekts enthält eine `INFRAPLAN`-Observation `BAU`; die
      Prognose nennt Inbetriebnahme 2030 mit Quelle „Infraplan“.
- [ ] Ein Projekt mit Befassung „nicht vereinbart“ zeigt keine parlamentarische
      Befassung, solange keine manuelle Festlegung besteht.
- [ ] Unzugeordnete Einträge erscheinen unter `/admin/unassigned` und lassen sich zuordnen.
- [ ] Ein zweiter Import desselben Jahrgangs wird abgewiesen; nach Löschen funktioniert
      er wieder, ohne doppelte Observations; andere Jahrgänge bleiben unberührt.
- [ ] Per MCP + Skill lässt sich der Jahrgang ohne Frontend-Klick bis zur Bestätigung
      führen; Kennzahlen erscheinen erst nach Freigabe auf `/infraplan`.
- [ ] Alle Ansichten funktionieren bei 360 px Breite.
