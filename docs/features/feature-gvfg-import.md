# Feature: GVFG-Bundesprogramm (Import, Projektseite, Finanzen-Übersicht)

**Status: geplant (2026-10-14)** — Entscheidungen mit dem Nutzer abgestimmt
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
sauber. Vorliegende Ausgaben: 2023–2027 (Stand 01.09.2023), 2025–2029 (Stand
18.07.2025); 2024–2028 reicht der Nutzer nach.

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
- `GvfgEntryAmount` — Eintrag × Kategorie (∑/A/B/C): Gesamtkosten, zwf. Kosten,
  Finanzhilfen insgesamt.
- `GvfgEntryYearAmount` — Eintrag × Kategorie × Zeitraum (Spanne oder Jahr) × Art
  (ausgezahlt / voraussichtlich / geplant / Rest ab). Keine festen Jahresspalten.
- `gvfg_entry_project` — m:n zu Projekten (Mehrfachzuordnung erlaubt).

Migration rückwärtskompatibel (nur neue Tabellen).

## Import

- Muster wie der Haushalts-Import: PDF hochladen → Celery-Task → Review-Seite →
  Bestätigen. Zahlen deterministisch aus dem Text, **kein LLM**.
- Spaltenzuordnung über die Kopfzeile mit einer **festen Liste** bekannter
  Spaltennamen; unbekannte Spalte → Abbruch mit klarer Meldung.
- Summen je Land/Teil nur als Plausibilitätsprüfung (Warnung im Review), nicht
  gespeichert.
- Testfälle: Ausgaben 2023 und 2025 (größter Layout-Abstand), 2024 nachgereicht.
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
„Projekt anlegen“ je Vorhaben und als Sammelaktion (Name, Schlüssel als
`project_number`, Gruppe GVFG; Geometrie später per MCP-Routing). Offene Vorhaben
der **neuesten Ausgabe** zählen in der Admin-Übersicht „Nicht zugeordnet“ mit.

### Rückwirkung auf Projekte

- Beim Bestätigen Gruppe „GVFG“ setzen, für Land 08 zusätzlich „GVFG BW“. Keine
  weiteren Landesgruppen. Gruppen werden nie entfernt; fehlt ein Projekt in einer
  neuen Ausgabe, zeigt die Übersicht „nicht mehr im Programm“.
- Lph und Inbetriebnahme nur am GVFG-Eintrag, nicht im Projekt/Planungsstand.
- Elternprojekte (München, Nürnberg, Breisgau, …) bekommen **keine Summen**, nur den
  Hinweis „GVFG-Förderung in Teilprojekten“ mit Links. Aufteilungen (z. B.
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

## MCP

Lese-Tools (z. B. `list_project_gvfg`, `list_gvfg_entries`) und ein Tool zum
Zuordnen von Vorhaben zu Projekten. Der Import selbst bleibt außerhalb des MCP.

## Etappen

0. Projekte zusammenführen (`merge_projects`) — siehe eigene Feature-Datei.
1. Datenpflege per MCP: falsche Schlüssel (~12), per Namen gefundene Schlüssel (10),
   kaputte Namen (36), dann ~48 Dubletten-Gruppen zusammenführen. Regel für das
   bleibende Projekt: kein Entwurf und in GVFG → manuell gepflegte Daten → bessere
   Geometrie → Beschreibung mit Fördersatz → Welle W2 vor W3 vor W1. Analyse direkt
   vor dem Zusammenführen auf dem aktuellen Stand wiederholen.
2. Datenmodell + Import mit Review.
3. Anzeige (Finanzen-Menü, GVFG-Übersicht, Projektseite).
4. Ausgabenvergleich + MCP-Tools.

Etappe 1 läuft parallel zu 2/3, muss aber vor dem ersten echten Import abgeschlossen sein.
