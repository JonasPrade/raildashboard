# Feature: Infraplan-Import

> **Status: Stufen 1–5 umgesetzt (#179–#182, #184; Stufen 2–5 am 2026-10-20), mit dem
> Nutzer abgestimmt (2026-10-15).** Abweichungen und Umsetzungsdetails stehen unter
> [„Umsetzung (2026-10-20)“](#umsetzung-2026-10-20). Grundlage ist der Infraplan 2026 (BMV,
> 6. Oktober 2026). Die Zeilenzahlen unten stammen aus dem Parser von Stufe 1 und
> stimmen mit den laufenden Nummern im Dokument überein (der Prototyp hatte 300 Zeilen
> gemeldet, weil er Teil C/D und GVFG Kat. A/C falsch abgegrenzt hatte). Das PDF lag
> nur vorübergehend im Repo; die Test-Fixtures sind daraus erzeugt
> (`apps/backend/tests/fixtures/infraplan_2026_*.json`). Künftige Jahrgänge kommen
> **nur über den Upload im Frontend** ins System.

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
| 13 | Rangfolge Termine | Je Phase Glaubwürdigkeit × Aktualität des Berichts (Infraplan 0.85 > VIB 0.6 > Fulda 0.55); BVWP nur als Lückenfüller, manuelle Termine gewinnen immer (angepasst 2026-10-17, `feature-fulda-import.md` W1) |
| 14 | Deckungsgrad | **nicht** anzeigen (andere Organisationen finanzieren mit) |
| 15 | PaBe-Relevanz | eigene Ebene „laut Infraplan“: manuell > Infraplan > Projektgruppen |
| 16 | Fehlendes Teilprojekt | Review bietet „Teilprojekt anlegen unter …“ |
| 17 | Maßnahme fehlt im neuen Jahrgang | Hinweis im Projektdetail, Liste im Review; kein Einfluss auf die Phase |
| 18 | Zwei Wege | **manuell** im Frontend und **per MCP** mit gleichem Ergebnis |
| 19 | Autonomie MCP | Agent darf alles bis einschließlich Bestätigen und Kennzahlen eintragen — Halt nur bei Parser-Warnungen |
| 20 | KI-Kennzahlen | Status „ungeprüft“, öffentlich erst nach Freigabe |
| 21 | Skills | **Alle** Dashboard-Skills liegen in einem Ordner im Repo, `.claude/skills/` (hier `.claude/skills/infraplan-import/SKILL.md`), immer in der aktuellen Fassung; ~~Upload nach claude.ai von Hand~~ — **seit 2026-10-17 liefert der MCP-Server den Skill selbst aus** (`list_skills`/`get_skill`, Markierung `metadata: mcp: true`), siehe `feature-mcp-server.md` → „Skills über MCP“ |
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
| Bedarfsplan, Teil C – Vorplanung (Lph 1–2) | `BP_C` | 71 | `Lph 1` · `Lph 1-2` | GWU |
| Bedarfsplan, Teil D – Grundlagenermittlung (noch keine Lph) | `BP_D` | 34 | leer | GWU |
| GVFG, Kat. A – endgültig ins Bundesprogramm aufgenommene DB-Vorhaben | `GVFG_A` | 42 | `Lph 5 - 9`, `Lph 3 - 4`, `offen`, … | Gesamtkosten in Mio. € |
| GVFG, Kat. C – bedingt aufgenommene DB-Vorhaben | `GVFG_C` | 41 | wie Kat. A | Gesamtkosten |
| InvKG – Maßnahmen im Bau | `INVKG` | 5 | `Bau` | GWU |

Summe **271 Zeilen** (Seiten 33–56; Teil C endet und Teil D beginnt auf S. 47,
GVFG Kat. A endet und Kat. C beginnt auf S. 53).

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
| 1 Textgewinnung | pdfplumber, Wörter **mit Schriftgröße** (`extra_attrs=["size"]`); Spaltengrenzen aus der Kopfzeile (`find_tables()[0]`); „�“ (U+FFFD) → „.“, weil manche Drucke den Punkt der Tabellenschrift so kodieren | `tasks/infraplan.py` |
| 2 Segmentierung | Abschnitte über die Überschriften `Bedarfsplan, Teil A–D`, `GVFG, Kat. A/C`, `InvKG`; Zeilen an der laufenden Nummer in Spalte 1; Fußnotenzone abschneiden | `tasks/infraplan.py` |
| 3 Semantik | Kopfzeile → kanonisches Schema (deterministisch über Spaltentitel, Muster `haushalt_columns`); Werte normalisieren (deutsche Zahlen, Jahr, Lph, Befassung) | `tasks/infraplan_columns.py` |
| 4 Matching | Vorschläge je Zeile, siehe [Zuordnung](#zuordnung-zu-projekten) | `tasks/infraplan_matching.py` |
| 5 Kennzahl-Seiten | Seitenzahlen der Kennzahl-Diagramme merken für die Bildausgabe: innerhalb der Kennzahl-Kapitel („3 Steuerungskennzahlen“, „I: Informationskennzahlen“) setzt die Überschrift „Steuerungskennzahl:“ / „Informationskennzahl:“ die aktuelle Kennzahl; eine Seite mit Diagrammbeschriftung und Einheitenzeile („(jährlich in km)“) wird ihr zugeordnet (das Diagramm steht oft eine Seite nach der Überschrift) | `tasks/infraplan.py` |

Was die Textgewinnung danach noch nicht lesen kann (`�`, `(cid:N)`), und Kostenzellen,
die weder Zahl noch Verweis sind, werden Warnungen (`UNREADABLE_TEXT`, `UNPARSED_COST`)
statt still zu verschwinden. Entwürfe aus der Zeit vor der Punkt-Korrektur und die daraus
bestätigten Jahrgänge repariert `scripts/repair_infraplan_full_stops.py` an Ort und Stelle
aus den gespeicherten Zelltexten (Zuordnungen und Kennzahlwerte bleiben).

Das hochgeladene PDF wird je Entwurf gespeichert (Seitenbilder für MCP und Freigabe-
Ansicht werden bei Bedarf mit pymupdf gerendert). OCR ist nicht nötig; fehlt einem
künftigen Jahrgang der Textlayer, kann `services/document_ocr.py` nachgerüstet werden.

---

## Datenmodell

Neue Tabellen (Migration via `make migrate-create`, rein additiv):

**`infraplan_parse_result`** — Entwurf je Upload (Muster `haushalts_parse_result`)
- `id`, `year`, `status`, `result_json`, `warnings_json`, `error_message`, `file_name`,
  `pdf_path` (gespeicherte Datei in `INFRAPLAN_PDF_DIR`), `kpi_pages_json`, `task_id`
  (letzter Auslese-Task), `created_at`, `created_by_user_id`, `username_snapshot`,
  `confirmed_at`, `confirmed_by_snapshot`

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

**Track MAIN** (Statusbericht zur Hauptphase; mit 0.85 darf er eine FinVe-Untergrenze
zurückstufen, gemeldet als Konflikt — `feature-project-progress.md`):

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
Datum = 31.12. des `ibn_year`, Anzeige nur als Jahr. Rangfolge: Wie VIB-PFA und Fulda
konkurriert der Infraplan-Termin über Glaubwürdigkeit × Aktualität des Jahrgangs
(`feature-fulda-import.md` → „Termine im Prognose-Panel“); BVWP-Schätzungen füllen nur
Lücken, manuelle Termine gewinnen immer. Kein Eingang bei `ibn_qualifier = OFFEN`
oder einem Jahr vor dem Jahrgang (GVFG-Altfälle). Mehrere Einträge je Projekt →
spätestes Jahr. Die Multi-Projekt-Zeitleiste nutzt dieselbe Funktion und übernimmt das
automatisch.

---

## Kosten

- **Gesamtkostenprognose** (Kopfzahl im Projektdetail; der Kostenblock steht direkt
  unter Projektdetails und Karte, vor Planungsstand und Infraplan):
  - Projekt mit eigener Zeile → deren `cost_mio` (bzw. der über `cost_ref_entry_id`
    aufgelöste Wert, wenn die Zeile auf einen anderen Eintrag verweist);
  - übergeordnetes Projekt ohne eigene Zeile → Summe der Teilprojekte (Grundsatz für
    **alle** Projekte, auch reine GVFG-Elternprojekte);
  - Sammel-GWU und Verweise zählen **einmal**, beim tragenden Eintrag (Deduplizierung
    über die Eintrags-ID).
  - Beschriftung: „Gesamtkostenprognose (Infraplan 2026)“; bei GVFG „Gesamtkosten
    (Länderangabe, Infraplan 2026)“. Fußnoten als Tooltip hinter einem „?“-Symbol neben
    der Beschriftung, nicht hochgestellt an der Zahl.
- **Vom Bund zugesichert** — daneben die FinVe-Mittel aus dem Haushalt (bestehende
  Daten, nur neu beschriftet und in denselben Block gezogen). Bei übergeordneten
  Projekten zählen die FinVe **aller** Teilprojekte mit (jede FinVe einmal, auch wenn
  mehrere Teilprojekte sie tragen); die Beschriftung nennt, wie viele davon aus
  Teilprojekten stammen. Quelle: `GET /projects/{id}/finves?include_subprojects=true`.
  Derselbe Grundsatz gilt für den Abschnitt „Finanzierungsvereinbarungen (FinVe)“:
  Er listet erst die eigenen FinVe, dann die der Teilprojekte, jede mit dem Hinweis
  „Aus Teilprojekt …“ und einem Link darauf.
- **GVFG-Projekte:** daneben die **Bundesförderung (GVFG)** als eigener Wert (dritter
  Wert neben der FinVe, ohne FinVe an deren Stelle) — die Finanzhilfen der ∑-Zeile, je Schlüssel die jüngste
  Ausgabe, eigene Vorhaben (ohne eigene die der Teilprojekte, nie beide addiert). Ohne
  Infraplan-Zahl steht der Block trotzdem, mit den GVFG-Gesamtkosten als Kopfzahl.
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
Diagramm für den gewählten Jahrgang: Ist-Werte aus diesem Jahrgang (fehlen sie dort, aus dem
jüngsten älteren) als Balken, seine Zielwerte als durchgezogene Linie und die Zielwerte des
**Vorjahrgangs** gestrichelt daneben („Ziel IP 2027“ gegen „Ziel IP 2026“), sodass
Zielverschiebungen sichtbar sind. Spätere Jahrgänge blendet die Auswahl aus
(`kpisAsOf` in `infraplanFormat.ts`). Teilreihen (`series`) nur mit Ist-Werten (z. B. Betriebsleistung nach
SPNV/SPFV/SGV) bleiben ein Stapel; der Tooltip nennt zusätzlich die Summe. Hat eine
Kennzahl Zielwerte je Teilreihe (z. B. die KMM-Kategorien), zeigt die Übersicht nur
deren Summe je Jahr; der Button „Details“ öffnet eine Ansicht
mit einem Diagramm je Teilreihe (Ist und Ziele der Kategorie). Sind die Teilreihen nicht
additiv, weil eine davon schon das Ganze ist (ETCS: „Gesamtnetz“, die TEN-Netze sind
Teilmengen), zeigt die Übersicht diese Teilreihe und die Details die übrigen
(`total_series`). Gehört zu einer Kennzahl eine zweite
Aussage in anderer Einheit (ETCS-Strecken-km und Ausrüstungsgrad in %), steht die
Begleitkennzahl als zweiter Balken daneben auf einer eigenen rechten Skala, in der
Übersicht wie in jedem Detaildiagramm; eine eigene Karte bekommt sie nicht
(`companion_key`, Bezeichnung `companion_label`; ETCS mit Ausrüstungsgrad). Der
Elektrifizierungsgrad ist dagegen bewusst **zwei Karten** nebeneinander: die je Jahr neu
elektrifizierten Strecken-km (Jahreswert) und der Anteil am Gesamtnetz (kumulierter
Bestand) — ein gemeinsames Diagramm würde eine Jahresentwicklung mit einer aufsummierten
verwechseln (Migration `20261021002` löst die Begleitkennzahl auf bestehenden
Datenbanken). Sonderfälle legt `chart_layout` fest: Barrierefreie Bahnsteige
(überlappende Anteile je Merkmal) als kleine Einzeldiagramme in der Karte,
Planfeststellungsanträge (Bestand neben Zu- und Abgängen) als Balken nebeneinander,
Mittelherkunft und -einsatz (ein Jahr, Herkunft/Einsatz je `series`-Präfix) als zwei
Ranglisten mit Anteilsbalken statt Zeitreihe. Werte nahe 100 % (Stellwerksbesetzungsquote,
`zoomed_axis`) bekommen eine Achse, die knapp unter dem kleinsten Wert beginnt, mit
Hinweis unter dem Diagramm. Kurze Einheiten (km, %) stehen an der Achse, längere
(„Mio. Trkm“) unter dem Titel; der Tooltip nennt die Einheit je Reihe. Die Karte der
Mittelherkunft trägt das gezeigte Jahr im Titel („Mittelherkunft und Mitteleinsatz 2025“).
Die `description` einer Kennzahl (Admin „Beschreibung“) erscheint als Tooltip hinter einem
Info-Symbol neben dem Namen — für Kennzahlen, deren Name allein nicht sagt, was gemessen
wird (Kapazitätsauslastung: Anteil der gefahrenen Trassenkilometer in überausgelasteten
Netzabschnitten, Infraplan 2026 Anhang I; der Seed und Migration `20261021002` tragen
diese Erklärung ein). Nur Werte mit Status
`GEPRUEFT`.

Aufbau der Seite: Kopf mit Titel, Info-Symbol (Tooltip mit der Erklärung, was der Infraplan
ist) und — sobald es mehr als einen Jahrgang gibt — einem Dropdown für den Jahrgang; er
gilt für beide Ansichten (Kennzahlen: Ist und Ziel des Jahrgangs gegen die Ziele des
Vorjahrgangs; Maßnahmen: Einträge des Jahrgangs). Darunter
ein zentraler Umschalter wie auf der Startseite (Karte/Liste/Zeitstrahl) mit den Ansichten
**Kennzahlen** und **Maßnahmen**; die Wahl steht in der URL (`?view=massnahmen`), damit
sich die Ansicht teilen lässt. Die Kennzahlen bekommen das Inhaltsverzeichnis der
Projektseite (Knopf am linken Rand) mit einem Eintrag je Bereich (Kennzahl-Art bzw.
Kategorie). Die Maßnahmen des gewählten Jahrgangs stehen mit Filter (Abschnitt, Suche) als
Karten wie in der FinVe-Übersicht: Kopf mit Abschnitt und Nummer, Bezeichnung, rechts
Stand, Inbetriebnahme, Kosten und Befassung, darunter die verknüpften Projekte als Knöpfe.

Diese Darstellungsregeln sind Felder der Kennzahl-Definition (`infraplan_kpi`), keine
Konstanten im Frontend: Admin → Infraplan → Reiter „Allgemeines“ → Kennzahlen zeigt alle
Definitionen und ändert je Kennzahl Name, Einheit, Kategorie, Beschreibung, Reihenfolge und
die Darstellung (`PATCH /kpis/{key}`). Änderungen gelten sofort für alle Jahrgänge. Die
Regeln des Infraplans 2026 setzt die Migration `20261021001` auf die bestehenden Zeilen,
neue Installationen bekommen sie aus `services/infraplan_kpis.py`.
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
| PATCH | `/kpis/{key}` | Kennzahl-Einstellungen (Name, Einheit, Kategorie, Beschreibung, Reihenfolge, Darstellung); nur gesendete Felder, `null` leert |

Außerdem (Recht `infraplan.import`): `GET /report` (übernommene Jahrgänge mit Zählern),
`GET /kpis` (Kennzahl-Definitionen), `GET /report/{year}/kpi-values` (alle Werte mit Status).

Lesend (öffentlich wie die übrigen Projektdaten): `GET /infraplan/projects/{id}`
(Einträge, Kostenprognose, „nicht mehr im Infraplan“), `GET /infraplan/kpis` (nur
geprüfte Werte, alle Jahrgänge), `GET /infraplan/reports`,
`GET /infraplan/reports/{year}/entries`.

Admin: `GET /admin/unassigned-infraplan-entries`,
`PATCH /admin/unassigned-infraplan-entries/{id}/assign` (Recht `assignment.manage`).

---

## Frontend

- `src/features/infraplan-import/`: `InfraplanImportPage` (Reiter „Import“: Upload +
  Entwurfsliste; Reiter „Allgemeines“: `InfraplanKpiSettings`, `?tab=allgemeines`),
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
| `get_project_infraplan(project_id)` | lesend | Einträge aller Jahrgänge eines Projekts (ohne Sonderrecht, öffentliche Daten) |

`list_data_gaps` bekommt die Lücke `infraplan_unassigned` (Zeilen des neuesten Jahrgangs
ohne Projekt, gesondert neben der Projektliste ausgegeben, mit `draft_id` und `row_key`).

**Skill** `.claude/skills/infraplan-import/SKILL.md` mit `metadata:` → `mcp: true`, damit
der MCP-Server ihn über `list_skills`/`get_skill` ausliefert (alle Dashboard-Skills liegen
in `.claude/skills/`, Übersicht in `.claude/skills/README.md`):
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
  Schriftgröße) und Tabellenköpfe der Seiten 33–56, erzeugt per Skript
  `scripts/dump_infraplan_pages.py` aus dem PDF (Muster `haushalt_ep12_2027_pages.json`);
  dazu `infraplan_2026_kpi_pages.json` mit ausgewählten Kennzahl-Seiten (57, 60–62,
  66–68, 85, 93–94, 102). Danach wurde `docs/261002_Infraplan_2026_1.pdf` gelöscht.
- Parser: Zeilenzahl je Abschnitt (38/40/71/34/42/41/5), lückenlose laufende Nummern,
  Fußnote abgetrennt (`1.720,48` + `[14]`), Kostenverweis aufgelöst, `bis 2035` →
  (2035, `BIS`), Folgeseiten ohne Kopfzeile, Lücken/Dubletten als Warnung,
  Kennzahl-Diagrammseiten.
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
  Materialisieren über den normalisierten Schlüssel. Die Richtung „GVFG-Ausgabe ist
  jünger“ liefert seit 2026-10-22 die Quelle `GVFG` (`feature-project-progress.md` →
  „Planungsstand aus dem GVFG-Bundesprogramm“); vorher fiel die Angabe dann ganz weg.
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
| 5 | MCP-Tools für den ganzen Ablauf + `.claude/skills/infraplan-import/` | #182 |
| später | Kennzahl-Maßnahmenlisten im Anhang (Name + Jahr), Startseite neu ordnen, wenn mehr solcher Übersichten dazukommen | — |

## Akzeptanzkriterien (gesamt)

- [ ] Upload des Infraplans 2026 liefert 271 Zeilen ohne Lücken-Warnung.
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

## Umsetzung (2026-10-20)

Stufen 2–5 in einem Zug. Was vom Plan oben abweicht oder ihn präzisiert:

- **Zuordnung beim Auslesen.** `tasks/infraplan_matching.py` rechnet die Vorschläge im
  Parse-Task (Projektnummer des Vorjahres → GVFG-Schlüssel → Fuzzy mit Vorfilter auf ein
  gemeinsames Wort ab 4 Zeichen; ein passendes Teilprojekt verdrängt sein Elternprojekt).
  Vorschläge ab 0.85 werden gleich als Zuordnung gespeichert (Quelle `NUMBER`/`FUZZY`).
  Der Review-Zustand liegt in `result_json.rows` (`suggestions`, `project_ids`,
  `assignment_source`, `assignment_note`, `assigned_by`); ein erneutes Auslesen behält
  die Zuordnungen je `row_key`.
- **Bestätigen** nimmt `published_on` (Titelblatt) und optional `title`; ohne Datum gilt
  das Importdatum für die Aktualität. Danach wird der Planungsstand aller Projekte mit
  Infraplan-Einträgen neu berechnet.
- **Jahrgang löschen** entfernt Einträge, Zuordnungen, Kennzahlwerte und die abgeleiteten
  Beobachtungen und öffnet den Entwurf wieder, sodass er erneut bestätigt werden kann.
- **Projekt-Endpunkt** heißt `GET /infraplan/projects/{id}` (Muster GVFG) statt
  `/projects/{id}/infraplan`.
- **Planungsstand:** `infraplan_entry_to_specs` mappt allgemein über den Stand: `Bau` →
  BAU, Baurecht → GENEHMIGUNGSPLANUNG + PF abgeschlossen, Teil D → NICHT_GESTARTET, sonst
  Lph 1–2/3–4/ab 5. Die geplante Inbetriebnahme ist eine erwartete Beobachtung
  (`is_expected`, 31.12.), die Prognose und Zeitstrahl über den neuen Eingang
  `infraplan` von `concrete_milestone_dates` erreicht. PaBe-Relevanz: neue Ebene in
  `resolve_parl_relevant` und im SQL-Zwilling des MCP-Filters `list_projects`.
- **GVFG-Zeilen (Entscheidung 22):** Ist die neueste GVFG-Ausgabe mit demselben Schlüssel
  jünger als der Infraplan, liefert die Infraplan-Zeile keine Phase und keinen Termin.
  Die GVFG-Ausgabe selbst speist den Planungsstand noch nicht — das gehört zum
  GVFG-Import und ist dort offen.
- **Kosten:** die Kostenprognose rechnet `crud/infraplan.py` (eigene Zeilen des neuesten
  Jahrgangs, sonst Summe über den ganzen Teilprojektbaum; Verweise und Sammel-GWU je
  tragendem Eintrag einmal).
- **Kennzahlen:** Die 25 Definitionen des Infraplans 2026 (23 Kennzahlen plus die beiden
  Prozent-Begleitkennzahlen) liegen in `services/infraplan_kpis.py` und werden beim ersten
  Zugriff angelegt. Einheiten sind aus dem PDF abgelesen, Kategorien der
  Informationskennzahlen fehlen; beides lässt sich in Admin → Infraplan → Allgemeines oder über
  `definitions` in `PUT …/kpi-values` bzw. `set_infraplan_kpi_values` berichtigen. Ein Wert `null` löscht den Platz.
- **MCP:** `assign_infraplan_row` wirkt nach der Bestätigung auf den übernommenen Eintrag
  (ersetzt die Projekte), damit der Agent Reste ohne Frontend nacharbeiten kann. Die Tools
  stehen in `mcp/tools/infraplan.py`, der Ablauf im Skill
  `.claude/skills/infraplan-import/SKILL.md`.
- **Offen für den Nutzer:** Test-Checklisten der Issues #180–#182, #184 (Upload des echten
  PDFs, Review, Freigabe der Kennzahlen).

## Ausbau für den Import 2027 (2026-10-20)

Erfahrung aus dem MCP-Import 2026: Die automatische Zuordnung traf 93 von 271 Zeilen,
rund 180 Zeilen wurden einzeln nachgeschlagen und zugeordnet, 29 Teilprojekte neu
angelegt, 14 Zeilen blieben offen. Teuer waren Einzelaufrufe, Listen ohne
Beschreibung und schwaches Matching. Ziel: der Infraplan 2027 in einer Sitzung mit
deutlich weniger Aufrufen. Entscheidungen des Nutzers (2026-10-20):

| # | Thema | Entscheidung |
|---|---|---|
| A1 | Aliase | Ein **allgemeines Alias-Feld** am Projekt, **mehrere Werte** (`project.aliases`, JSON-Liste). Eine Deutschlandtakt-Kennung `DT 38` zählt beim Matching als sicherer Treffer; `PB 07`/`VDE 8.1` bestimmen nur den Kontext (Elternprojekt), weil eine Zeile meist einen Teil davon meint; freie Aliase („Gäubahn“) fließen in den Namensvergleich und die Suche. Kein eigenes Feld `infraplan_dt`. |
| A2 | Pflege der Aliase | vorerst nur per MCP (`update_project`) und API, kein Frontend-Feld |
| A3 | Teilprojekt nach Bestätigung | `create_infraplan_subproject(s)` wirkt auch auf bestätigte Jahrgänge |
| A4 | %-Kennzahlen | Keys bleiben (`elektrifizierungsgrad` + `elektrifizierungsgrad_prozent`, `etcs_strecken_km` + `etcs_ausruestungsgrad`); Namen, Einheiten und Darstellung regeln die Kennzahl-Einstellungen (Migrationen `20261021001`/`20261021002`, Admin → Infraplan → Allgemeines) |
| A5 | Konfidenzen | Alias und Vorjahresnummer 1.0, Vorjahrestext 0.95, Kontext mit passender Abschnittsnummer 0.9; ab 0.85 vorausgewählt |

Verhältnis zu „Eine Projektnummer-Spalte am `Project` gibt es nicht“ (oben): Die
Wiedererkennung im Folgejahr läuft weiter über die bestätigten Zuordnungen. Aliase
ergänzen das für Kennungen, die in anderen Quellen anders nummeriert sind
(Deutschlandtakt: „DT 38“ im Infraplan, D-Nummern im Dashboard stimmen nur teilweise
überein — D-38, D-151, D-154, D-167/168 passen, D-37, D-76 nicht). Deshalb wird nie
blind gleichgesetzt, sondern nur über ein gepflegtes Alias.

### Matching

Reihenfolge je Zeile (`tasks/infraplan_matching.py`), stärkster Vorschlag zuerst:

1. **Vorjahr über die Nummer** (`NUMBER`, 1.0) — wie bisher, jetzt mit der Notiz der
   Vorjahreszuordnung (`previous_note`, `previous_year`).
2. **Vorjahr über den Text** (`PREVIOUS_YEAR`, 0.95) — gleiche Abschnittsart und
   gleiche normalisierte Bezeichnung + Maßnahme im neuesten bestätigten Jahrgang, für
   Zeilen ohne `primary_number` (Bedarfsplan). Ebenfalls mit Notiz.
3. **Projektnummer** (`NUMBER`, 1.0) — `primary_number` gleich `project_number`
   (normalisiert; z. B. „InvKG Nr. 6“); bei GVFG-Zeilen wie bisher der Schlüssel
   (`GVFG_KEY`).
4. **Alias-Kennung** (`ALIAS`, 1.0) — `DT nn` aus Bezeichnung oder Maßnahme gleich
   einem Alias des Projekts. Eine Zeile mit mehreren DT-Nummern bekommt alle passenden
   Projekte. Nennt die Maßnahme vorher eine eigene Hauptmaßnahme („Elektrifizierung,
   1gl. Vbk Bad Kleinen inkl. DT 2 …“), ist das DT-Projekt nur ein Teil der Zeile: 0.8,
   ein Vorschlag neben der Hauptmaßnahme.
5. **Kontext** (`CONTEXT`) — aus der Bezeichnung das Elternprojekt bestimmen
   („Großknoten München“ → Knoten München, „PB 07: ABS/NBS Karlsruhe – Basel“ → ABS/NBS
   Karlsruhe – Basel): die meisten Wörter seines Namens oder eines freien Alias stehen in
   der Bezeichnung; ohne Treffer über `PB nn` (Bündel tragen es in `project_number`,
   „BSWAG_2023_PB_7“) oder `VDE n`. Passt ein Projekt *ohne* Teilprojekte besser zur
   Bezeichnung, meint die Zeile dieses Projekt und es gibt keinen Kontext. Dann nur unter
   den Teilprojekten (zwei Ebenen) suchen:
   - gleiche Abschnittsnummer derselben Art (Abschnitt/PFA/StA/PFB/Bauabschnitt,
     Teilmaßnahme/TM, Baustufe/BS; „Abschnitt 2-6“ ist ein Bereich, „PFA 9.2“ fällt ohne
     eigenes Teilprojekt in „Abschnitt 9“) → 0.9. Hat die Stufe selbst Teilprojekte und
     nennt die Maßnahme eines davon, wird es das („3. Baustufe: Knoten Riesa …“);
   - sonst die Wörter des Teilprojekts ohne den Namen des Elternprojekts: Alle vollständig
     genannten Teilprojekte zählen (Sammelzeile mit benannten Teilen), ein einzelnes nur,
     wenn kein anderes nahekommt; Wörter, die mehrere Teilprojekte tragen, zählen
     weniger, allgemeine Wörter („Elektrifizierung“, „Ausbau“) allein nie. 0.6 + 0.3 ×
     Abdeckung.
   - Gibt es unter dem Elternprojekt Teilmaßnahmen ohne Namen und ohne Beschreibung
     („Knoten Mannheim Teilmaßnahme 8“), bleibt ein Worttreffer unter 0.85 — die Zeile
     könnte eine von ihnen meinen.
   - Passt kein Teilprojekt, ist das Elternprojekt ein Hinweis (0.7), nie vorausgewählt.
     Probelauf 2026: „Sammelzeile → Elternprojekt“ automatisch lag 3:9 daneben, weil
     gleiche Zeilen mal dem Elternprojekt, mal einem neuen Teilprojekt gehörten.
6. **Namensvergleich** (`FUZZY`) — wie bisher, aber auf normalisierten Texten und mit
   freien Aliasen als weiteren Namen.

**Normalisierung vor jedem Vergleich:** Abkürzungen werden auf beiden Seiten
ausgeschrieben — Ubf → Umschlagbahnhof, Vbk → Verbindungskurve, Abzw/Bzw → Abzweig,
Ü-BW → Überwerfungsbauwerk, Krbw → Kreuzungsbauwerk, Krzbf/Krzbhf → Kreuzungsbahnhof,
Bf/Bhf → Bahnhof, Hbf → Hauptbahnhof, Gbf → Güterbahnhof, Rbf → Rangierbahnhof,
`2gl.` → zweigleisig, TM → Teilmaßnahme, BS → Baustufe, Großknoten → Knoten; Orte: Mü/MU
→ München, HH → Hamburg, MA → Mannheim, HD → Heidelberg, Ffm → Frankfurt, B → Berlin
(nur vor Bindestrich). Das Ersatzzeichen „�“, das der Parser für Punkte im PDF liefert,
wird zum Punkt.

### MCP

| Tool | Art | Zweck |
|---|---|---|
| `assign_infraplan_rows(id, rows[{row_key, project_ids, note}])` | schreibend | Sammelzuordnung, Ergebnis je Zeile (`ok`/`error`), Teilerfolg erlaubt; Entwurf und bestätigter Jahrgang; Planungsstand einmal am Ende neu berechnet |
| `create_infraplan_subprojects(id, items[{row_key, parent_id?, name?, note?}])` | schreibend | mehrere Teilprojekte samt Zuordnung, Ergebnis je Zeile |
| `create_infraplan_subproject(…, parent_id?)` | schreibend | ohne `parent_id`: eigenständiges Entwurfsprojekt (z. B. GVFG-Vorhaben ohne Elternprojekt); wirkt auch nach der Bestätigung |
| `get_infraplan_draft(…, compact=true)` | lesend | alle Abschnitte in einer Antwort, je Zeile nur `row_key`, Bezeichnung, Maßnahme, Länder, Zuordnung, bester Vorschlag (Projekt, Konfidenz, Grund) |
| `get_infraplan_page_text(id, page)` | lesend | Text einer PDF-Seite als Zeilen mit x-Positionen der Wörter (Diagrammbeschriftungen ohne Bildfreigabe) |
| `suggest_infraplan_kpi_values(id, page)` | lesend | beschriftete Werte je Diagramm über die x-Position den Jahren der Achse zugeordnet, als ungeprüfte Vorschläge; gestapelte Werte werden markiert, nicht zugeordnet |
| `check_project_data(checks?)` | lesend | Prüfliste: doppelte Projektnummern, namensgleiche Geschwister, GVFG-Ländercode ≠ Land, Teilmaßnahmen ohne sprechenden Namen; keine Korrektur |
| `list_projects(…, with_description=true)` | lesend | je Projekt der erste Satz der Beschreibung (gekürzt) und die Aliase; `search` sucht auch in Beschreibung und Aliasen |

Die bestehenden Tools bleiben unverändert nutzbar.

### Datenqualität (`check_project_data`)

- `duplicate_number`: dieselbe `project_number` an mehreren Projekten (Fall 2221/1829
  „2-040-V01 TM8“). Sammelkennungen wie `L 27` werden mitgemeldet; die Liste ist eine
  Prüfliste, keine Fehlerliste.
- `duplicate_sibling_name`: namensgleiche Projekte unter demselben Elternprojekt
  (Fall 1781/1782).
- `gvfg_land_mismatch`: der Ländercode des GVFG-Schlüssels in `project_number` passt
  nicht zum Land — Land aus der Projektgruppe „GVFG <Land>“, den zugeordneten
  GVFG-Vorhaben oder den Ländern der zugeordneten Infraplan-Zeilen; außerdem
  zugeordnete Infraplan-Zeilen, deren Schlüssel sich nur im Ländercode unterscheidet
  (Fall S4 Hamburg: Projekt „01 D 508_A“, Zeile „02 D 508_A“).
- `unnamed_subproject`: Teilprojekte, deren Name nach Abzug des Elternnamens nur aus
  „Teilmaßnahme n“/„TMn“ besteht (Fall Knoten Mannheim TM1–TM9).

### Kennzahlen

- Diagramme mit km und % sind zwei Kennzahlen: `elektrifizierungsgrad` (km) +
  `elektrifizierungsgrad_prozent` (%), `etcs_strecken_km` (km) + `etcs_ausruestungsgrad`
  (%, als Begleitwert im ETCS-Diagramm). Namen, Einheiten und Darstellung kommen aus den
  Kennzahl-Einstellungen in `services/infraplan_kpis.py` bzw. der Admin-Ansicht.

### Abnahme

- Tests für Sammelzuordnung, Abkürzungsnormalisierung, Kontextmatching und das Prüftool.
- Probelauf: Matching auf den 271 Zeilen des Entwurfs 2026 gegen den heutigen
  Projektbestand (ohne die beim Import angelegten Entwurfsprojekte, ohne Vorjahr); Zahl
  der Zeilen ≥ 0,85 (vorher 93) und Anteil, der mit der bestätigten Zuordnung
  übereinstimmt. Der Entwurf 1 selbst bleibt unverändert.

### Probelauf (2026-10-20)

Zeilen und Projektliste lesend per MCP aus der Produktion (1.329 Projekte ohne
Entwürfe, ohne Beschreibungen — die liefert `list_projects` dort noch nicht), Matching
offline:

| Lauf | ≥ 0,85 | = Zuordnung 2026 | teilweise | anders | Zeile 2026 offen bzw. neues Projekt |
|---|---|---|---|---|---|
| vorher | 93 | 93 | – | – | – |
| neu, ohne Vorjahr | 145 | 125 | 3 | 2 | 15 |
| neu, 2026 als Vorjahr (Simulation 2027) | 270 | 257 (alle) | – | – | 13 |

Die zwei „anders“: Sammelzeilen, die 2026 dem Elternprojekt zugeordnet wurden, das
Matching wählt die darin benannten DT-Teilprojekte.

**DT-Aliase:** `scripts/set_dt_aliases_2026.py` setzt 76 eindeutige Paare aus den
Zeilen 2026 (DT-Nummer → D-Projekt, geprüft gegen die Projektnummer). Mit ihnen steigt
der Lauf ohne Vorjahr auf 162 Zeilen ≥ 0,85 (131 wie 2026, 5 teilweise, 7 anders). Die
sieben „anders“ sind reine DT-Listen („DT 157 Wustermark, DT 158 Rathenow, …“), die
2026 dem Bündel bzw. Elternprojekt gehörten und jetzt den genannten DT-Projekten —
nach der Regel „mehrere benannte Teilmaßnahmen → alle Teilprojekte“. Im Folgejahr gilt
dort ohnehin die Vorjahreszuordnung. Die 15: Zeilen, die erst nach der
Bestätigung zugeordnet wurden (Treffer genau auf die dafür angelegten Projekte über
Projektnummer bzw. GVFG-Schlüssel) oder deren Ziel 2026 neu angelegt wurde. Ohne Aliase
und Beschreibungen fehlen v. a. die Knoten mit Teilmaßnahmen ohne Namen (Köln,
Mannheim, München, Mühldorf) — die liefert die Datenpflege nach `check_project_data`.
