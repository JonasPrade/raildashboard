# Feature: GVFG-Bundesprogramm (Import, Projektseite, Finanzen-Übersicht)

**Status: Etappen 2 und 3 umgesetzt (2026-10-15), MCP-Tools aus Etappe 4 umgesetzt
(2026-10-19)** — Datenmodell, Parser, Import mit Review, Lese-API, Finanzen-Menü,
GVFG-Übersicht, Projektseite, offene Zuordnungen und MCP-Tools stehen (siehe
[Umsetzungsstand](#umsetzungsstand-2026-10-15) und [MCP](#mcp)). Der Ausgabenvergleich
(Reiter „Änderungen zur Vorausgabe“) folgt. — Entscheidungen mit dem Nutzer abgestimmt
(Grilling-Runde 2026-10-13/14). Vorstufe:
[`feature-project-merge.md`](feature-project-merge.md) (Dubletten bereinigen).

## Ziel

Das jährlich fortgeschriebene **GVFG-Bundesprogramm** (Vorhaben des ÖPNV nach § 6
Abs. 1 GVFG, BMV Referat E 22) als Daten im Dashboard führen:

1. **Projektseite:** Ein Projekt zeigt seine GVFG-Förderung (Kategorie, Fördersatz,
   Fördertatbestand, Bundesfinanzhilfen je Jahr).
2. **Programmübersicht:** alle Vorhaben einer Ausgabe, filterbar.
3. **Vergleich der Ausgaben:** Kostenentwicklung, Verschiebungen, Wechsel C → A,
   neue/entfallene Vorhaben.

Die Daten sind **öffentlich** sichtbar (werden öffentlich diskutiert), obwohl das
PDF „nicht zur Veröffentlichung vorgesehen“ ist — bewusste Entscheidung des Nutzers.

## Quelle: Aufbau des PDFs

Textbasiertes PDF (kein Scan), `pdftotext -layout`/pdfplumber lesen die Tabellen
sauber. Vorliegende Ausgaben: 2023–2027 (Stand 01.09.2023), 2024–2028 (Stand
08.11.2024), 2025–2029 (Stand 18.07.2025).

**2024–2028 kommt in zwei Dateien:** Hauptteil (37 S., 221 Vorhaben, nur
finanzrelevant) und ein separates **Anhang**-PDF (29 S., 217 Vorhaben, nachrichtlich,
ohne Jahreswerte; „- Anhang -“ im Seitenkopf, eigene Übersicht „alle Länder“). Beide
Schlüsselmengen sind disjunkt. Der Import muss deshalb mehrere PDFs zu **einer**
Ausgabe zusammenführen können (Anhang nachträglich zu einer bestehenden Ausgabe
hochladen). 2023–2027 hat keinen nachrichtlichen Teil, 2025–2029 hat ihn im selben PDF.
Layout 2024 entspricht 2025 (Lph, Stadt/Region, Inbetriebnahme); Jahresspalten 2024:
`1967–2022`, `2023`, `2024`, `2025`–`2028`, Rest ab `2029`.

- Vorbemerkungen, Übersicht „alle Länder“ (Summen kommunal/DB/gesamt).
- Je **Land** und je **kommunale Vorhaben / DB-Vorhaben** eine Tabelle, jeweils
  **finanzrelevanter Teil** und (ab 2025) **nachrichtlicher Teil**.
- Je Vorhaben: Nr., **Schlüssel** (`02 G 510_A`; 2023 auch `01 D 508 _ A`),
  Stadt/Region (2025), Bezeichnung (mehrzeilig), Lph (2025), Fördertatbestand,
  Fördersatz, Beginnjahr Mittelabfluss, Baubeginn, Inbetriebnahme geplant/tatsächlich
  (2025), dann bis zu drei Zeilen **∑ / A / B / C** mit Gesamtkosten, zwf. Kosten,
  Finanzhilfen insgesamt, bereits ausgezahlt (2023: `1967–2021`, `vsl. 2022`;
  2025: `1967–2023`, `2024`), Jahre der Ausgabe (5 Spalten), Rest ab Folgejahr.
- Nachrichtlicher Teil: nur Kosten und maximale Bundesfinanzhilfen, keine Jahre.
- Schlüssel: `LL X NNNN_S` — LL = Land (01 SH … 16 TH), X = `G` kommunal / `D` DB,
  Suffix `A` (Regelfall), `T`, `S`, `N`, `U` (Bedeutung unbekannt, **roh speichern**).
- Etwa 500 Vorhaben je Ausgabe (2025: 488 Schlüssel; 363 auch 2023 enthalten).

## Datenmodell

- `GvfgProgram` — Ausgabe (z. B. „2025–2029“), Startjahr, Stand-Datum, Quelldatei.
- `GvfgEntry` — Programm, Schlüssel roh + normalisiert, Land, kommunal/DB,
  finanzrelevant/nachrichtlich, Bezeichnung, Stadt/Region, Lph, Fördertatbestand,
  Fördersatz, Beginnjahr Mittelabfluss, Baubeginn, Inbetriebnahme geplant/tatsächlich.
  Alles, was 2023 fehlt, ist optional.
- `GvfgEntryAmount` — eine Zeile je gedruckter Kategoriezeile (∑/A/B/C, in
  Druckreihenfolge; ein Vorhaben kann zwei C-Zeilen haben, z. B. angekündigte
  Mehrkosten): Gesamtkosten, zwf. Kosten, Finanzhilfen insgesamt und die
  Jahreswerte als `periods` = `{Spaltenbeschriftung: Betrag}`. Die Spalten selbst
  (Beschriftung, Jahre, Art ausgezahlt/voraussichtlich/geplant/Rest) stehen am
  Programm (`GvfgProgram.periods`). Keine festen Jahresspalten.
- `gvfg_entry_project` — m:n zu Projekten (Mehrfachzuordnung erlaubt).

Migration rückwärtskompatibel (nur neue Tabellen).

## Import

- Muster wie der Haushalts-Import: PDF hochladen → Celery-Task → Review-Seite →
  Bestätigen. Zahlen deterministisch aus dem Text, **kein LLM**.
- Spaltenzuordnung über die Kopfzeile mit einer **festen Liste** bekannter
  Spaltennamen; unbekannte Spalte → Abbruch mit klarer Meldung.
- Summen je Land/Teil nur als Plausibilitätsprüfung (Warnung im Review), nicht
  gespeichert.
- Testfälle: alle drei Ausgaben, für 2024 Hauptteil + Anhang.
- Berechtigung `gvfg.import` (Gruppe Finanzierung, für Editoren).

### Zuordnung zu Projekten

Die GVFG-Projekte existieren größtenteils schon (Gruppe „GVFG“, `project_number` =
Schlüssel, Schreibweise uneinheitlich). Abgleich auf **beiden Seiten normalisiert**:
Regex `(\d{1,2})\s*([GD])\s*(\d+)\s*_\s*([A-Z])`, Land auf zwei Stellen, ohne
Leerzeichen.

1. exakter normalisierter Schlüssel,
2. Schlüssel ohne Suffix (markiert),
3. Name (difflib, wie `finve_matching`).

Mehrfachtreffer, Namensähnlichkeit < 0,45 und widersprüchliche Fördertatbestände
kommen auf eine Prüfliste statt automatisch übernommen zu werden. Neue Vorhaben:
Der Button „Projekt nicht gefunden – als Entwurf anlegen“ unter jedem Vorhaben legt sofort einen Projektentwurf an (Name vorbelegt,
optional Überprojekt) und ordnet ihn zu — wie bei Haushalt, Bauportal und
Fulda-Runde; die Sammelaktion legt alle Vorhaben ohne Projekt beim Übernehmen an
(Name, Schlüssel als `project_number`, Gruppe GVFG; Geometrie später per
MCP-Routing). **Der Import legt Projekte immer als Entwurf an** (`is_draft = true`,
der Review-Dialog sagt das): sie haben außer Name und Nummer keine Daten und sollen
nicht wie gepflegte Projekte in Listen und Karte erscheinen. Fertigstellen: Oberfläche
oder `set_project_draft`; Entwürfe finden: `list_projects(drafts="only")`.

**Entwürfe in Summen und Gruppen** (festgelegt): Die Förderdaten des Vorhabens bleiben
sichtbar und zählen in allen GVFG-Summen und -Übersichten mit — sie hängen am Vorhaben,
nicht am Projekt. Das Projekt selbst ist als Entwurf markiert (`is_draft` in
`list_gvfg_entries`, `list_project_gvfg`) und fehlt in Projektlisten, Karte und den
Projektzählern der Gruppen (`list_project_groups`, Gruppenansichten), bis es
fertiggestellt ist. Offene Vorhaben
der **neuesten Ausgabe** zählen in der Admin-Übersicht „Nicht zugeordnet“ mit.

### Rückwirkung auf Projekte

- Beim Bestätigen Gruppe „GVFG“ setzen, für Land 08 zusätzlich „GVFG BW“. Keine
  weiteren Landesgruppen. Gruppen werden nie entfernt; fehlt ein Projekt in einer
  neuen Ausgabe, zeigt die Übersicht „nicht mehr im Programm“.
- Lph und Inbetriebnahme: Für dasselbe Vorhaben liefert auch der **Infraplan** diese
  Angaben (GVFG Kat. A/C). Es gilt der **jüngere Stand** — Stand-Datum der GVFG-Ausgabe
  vs. Veröffentlichungsdatum des Infraplans (Entscheidung 2026-10-15, siehe
  `feature-infraplan-import.md` → „Abgleich mit `feature-gvfg-import.md`“). Die jüngere
  Quelle fließt in Planungsstand und Prognose (Vertrauen 0.75), die ältere bleibt im
  GVFG-Abschnitt sichtbar. Seit 2026-10-22 ist die GVFG-Ausgabe dafür eine eigene
  Fortschrittsquelle `GVFG` (Lph, Baubeginn, Inbetriebnahme; Regeln in
  `feature-project-progress.md` → „Planungsstand aus dem GVFG-Bundesprogramm“).
  Übernahme und Zuordnung berechnen den Planungsstand der Projekte sofort neu.
- Elternprojekte (München, Nürnberg, Breisgau, …) bilden **Summen** über ihre
  Teilprojekte (projektweiter Grundsatz, `docs/architecture.md` → „Grundsätze“;
  ersetzt die frühere Festlegung „keine Summen“, 2026-10-15) und verlinken die
  Teilprojekte. Aufteilungen (z. B.
  `03 D 2807_A` 2023 → 2807/2842/2843 2025) zeigt der Ausgabenvergleich als Hinweis;
  die Projekthierarchie bleibt unberührt.

## Anzeige

- Hauptmenü: „Haushalt“ heißt **„Finanzen“** mit Auswahl **„Bedarfsplan Schiene“**
  (bisherige FinVe-/Haushaltsansicht) und **„GVFG“**; später weitere Punkte.
  `/finanzen/bedarfsplan`, `/finanzen/gvfg`; `/finves` leitet um.
- `/finanzen/gvfg`: Tabelle der gewählten Ausgabe, Filter Land, kommunal/DB,
  Fördertatbestand, Kategorie, Teil, „ohne Projekt“; Summen je Land; Reiter
  „Änderungen zur Vorausgabe“.
- Projektseite: Abschnitt „GVFG“ unter „Finanzierungsvereinbarungen (FinVe)“ mit
  eigenem Inhaltsverzeichnis-Eintrag: neueste Ausgabe (A/B/C, Fördersatz,
  Fördertatbestand, Lph, Inbetriebnahme), Balkendiagramm Bundesfinanzhilfen je
  Jahr, Tabelle „Entwicklung über die Ausgaben“.
- Plant die neueste Ausgabe nach dem bekannten Inbetriebnahmejahr noch einen relevanten
  Teil der Finanzhilfen ein, stellt die Prognose das Jahr in Frage
  (`feature-project-progress.md` → „IBN-Plausibilität aus der GVFG-Finanzreihe“).

## Umsetzungsstand (2026-10-15)

- **Parser** `services/gvfg_parser.py` (pdfplumber): Tabellen und Kopfzeilen per
  `find_tables`, Spalten über eine feste Liste von Kopfzeilentexten (unbekannte
  Spalte → `GvfgParseError`). Zahlen werden über die Spaltenpositionen der Kopfzeile
  und die Höhe der Kategoriezeile zugeordnet — einige Datenzeilen haben keine
  senkrechte Trennlinie, dann stehen zwei Zahlen in einer Zelle. Toleranzen
  skalieren mit der Schriftgröße (2023 gibt es eine Seite in 2,2 pt, 2024 ist in
  9 pt gesetzt). Fehlt die ∑-Zeile (einige Seiten 2023), wird sie aus A/B/C
  berechnet (`computed`). Die Art (kommunal/DB) kommt aus der Seitenüberschrift,
  nicht aus dem Schlüsselbuchstaben — einige G-Vorhaben stehen in DB-Tabellen.
- **Summenprüfung:** „Summe über <Land>“ und „Kat. A/C“ je Tabelle gegen die
  eingelesenen Vorhaben, dazu ∑ gegen A+B+C je Vorhaben. Abweichungen sind
  Hinweise im Review, kein Abbruch: Gegen die echten PDFs geprüft liest der Parser
  2024–2028 (Haupt + Anhang) ohne Abweichung; die übrigen Hinweise in 2023/2025
  sind Rechenfehler der PDF-Summenzeilen selbst (z. B. fehlt 05 D 633_A in der
  NRW-DB-Summe 2025).
- **Import:** `POST /api/v1/import/gvfg/parse` (Celery `parse_gvfg_pdf_task`) →
  `GvfgParseResult` mit Vorschlägen; Review unter `/admin/gvfg-import`;
  `POST …/parse-result/{id}/confirm` mit `assignments` und `create_projects`
  ersetzt die enthaltenen Teile der Ausgabe in einer Transaktion. Vorschlag zuerst
  die Projekte der Vorausgabe, dann normalisierter Schlüssel, dann ohne Suffix,
  dann Name. Test mit dem echten 2025-PDF gegen den Bestand: 446 von 488 per
  Schlüssel, 42 mit mehreren Projekten (die Dubletten), 42 ohne Projekt.
- **Lese-API (öffentlich):** `GET /api/v1/gvfg/programs`,
  `GET /api/v1/gvfg/programs/{id}/entries`, `GET /api/v1/gvfg/projects/{id}/entries`.
- **Recht** `gvfg.import` (Editoren), Migration `20261015001`.
- **Offene Zuordnungen:** `GET /api/v1/admin/unassigned-gvfg-entries` (Vorhaben der
  neuesten Ausgabe ohne Projekt) und `PATCH …/{id}/assign` (Recht
  `assignment.manage`); das Zuordnen ergänzt wie der Import die Gruppen „GVFG“/„GVFG BW“.
  Die Vorhaben zählen im Admin-Badge mit.
- **Anzeige (Etappe 3):** Menüpunkt „Finanzen“ (`FinanzenLayout`, Umschalter
  „Bedarfsplan Schiene“ / „GVFG“); `/finves?q=` leitet auf `/finanzen/bedarfsplan` um.
  `/finanzen/gvfg` (`GvfgOverviewPage`): Ausgabe wählen, Filter Land, Fördertatbestand,
  kommunal/DB, Teil, „ohne Projekt“, Suche; Kennzahlen, Tabelle mit Projektlinks,
  Summen je Land. Der Kategorie-Filter entfällt — die Spalte „Kat.“ zeigt die
  Kategorien. Projektseite (`GvfgSection`, Inhaltsverzeichnis „GVFG“): je Schlüssel die
  neueste Ausgabe mit Eckdaten, aufklappbar ∑/A/B/C-Tabelle, Balkendiagramm der
  Finanzhilfen je Jahresspalte (ausgezahlt / geplant) und „Entwicklung über die
  Ausgaben“. Ein Elternprojekt listet unter „GVFG-Förderung in Teilprojekten“ die
  Vorhaben seiner direkten Unterprojekte als Links, ohne Summe
  (`GET /api/v1/gvfg/projects/{id}/entries?with_subprojects=true`).

## MCP

Lese-Tools und ein Tool zum Zuordnen von Vorhaben zu Projekten
(`mcp/tools/gvfg.py`, umgesetzt 2026-10-19). Der Import selbst bleibt außerhalb des MCP.
Beträge in Mio. €.

| Tool | Wirkung | Recht |
|---|---|---|
| `list_gvfg_programs` | Ausgaben (neueste zuerst) mit Jahresspalten, Zahl der Vorhaben und der Vorhaben ohne Projekt | — |
| `list_gvfg_entries` | Vorhaben einer Ausgabe (Standard: neueste), kompakt mit ∑-Zeile, Kategorien mit Finanzhilfe, geplanten Finanzhilfen in den Jahren der Ausgabe und Projekten. Suche: Schlüssel in jeder Schreibweise (auch ohne Suffix) oder Text in Name/Stadt; Filter Land, kommunal/DB, Teil, Fördertatbestand, mit/ohne Projekt | — |
| `get_gvfg_entry` | ein Vorhaben mit allen gedruckten Zeilen, PDF-Seite und `history` (derselbe Schlüssel in allen Ausgaben) | — |
| `list_project_gvfg` | Förderung eines Projekts über alle Ausgaben, `with_subprojects` ergänzt die direkten Teilprojekte | — |
| `assign_gvfg_entry` | setzt die Projekte eines Vorhabens (ersetzt die bisherigen, leere Liste löscht), `all_editions` für denselben Schlüssel in allen Ausgaben. Neue Projekte bekommen „GVFG“ (Land 08 auch „GVFG BW“); Gruppen werden nie entfernt | `assignment.manage` |

`assign_gvfg_entry` ersetzt statt zu ergänzen (anders als die REST-Zuordnung unter
„Offene Zuordnungen“), weil es vor allem falsche Zuordnungen korrigiert — etwa wenn
nach dem Zusammenführen von Dubletten ein Vorhaben noch auf zwei Projekte zeigt.

## Etappen

0. Projekte zusammenführen (`merge_projects`) — umgesetzt, siehe eigene Feature-Datei.
1. Datenpflege per MCP (Block A der Korrekturen erledigt 2026-10-15): falsche Schlüssel (~12), per Namen gefundene Schlüssel (10),
   kaputte Namen (36), dann ~48 Dubletten-Gruppen zusammenführen. Regel für das
   bleibende Projekt: kein Entwurf und in GVFG → manuell gepflegte Daten → bessere
   Geometrie → Beschreibung mit Fördersatz → Welle W2 vor W3 vor W1. Analyse direkt
   vor dem Zusammenführen auf dem aktuellen Stand wiederholen.
2. Datenmodell + Import mit Review — umgesetzt.
3. Anzeige (Finanzen-Menü, GVFG-Übersicht, Projektseite) — umgesetzt; Reiter
   „Änderungen zur Vorausgabe“ kommt mit Etappe 4.
4. Ausgabenvergleich + MCP-Tools — MCP-Tools umgesetzt (2026-10-19), Ausgabenvergleich offen.

Etappe 1 läuft parallel zu 2/3, muss aber vor dem ersten echten Import abgeschlossen sein.
