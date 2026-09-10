# Feature: Haushaltsberichte-Import

## Ziel

Jährlicher Import der Anlage VWIB, Teil B (Bundeshaushalt) als PDF.
Die Tabelle enthält alle Bedarfsplanmaßnahmen des Schienenwegeinvestitionsprogramms
mit FinVe-Nummern, Kostenschätzungen und Jahresansätzen je Haushaltskonto.

**Status: vollständig implementiert.** Das Einlesen ist am 2026-09-08 auf dem
Dev-Server gegen den EP-12-Bericht Teil B 2027 verifiziert (141 Zeilen aus fünf
Tabellen, Spaltenzuordnung aus der Kopfzeile). Der Import-Schritt selbst ist dort
noch offen — Stand in `docs/manual-tests-backlog.md`.

---

## Implementierung

| Layer | Pfad |
|-------|------|
| Parser (Celery-Task) | `apps/backend/dashboard_backend/tasks/haushalt.py` |
| Spaltenzuordnung | `apps/backend/dashboard_backend/tasks/haushalt_columns.py` |
| Textgewinnung (gemeinsame Stufe 1) | `apps/backend/dashboard_backend/services/document_ocr.py` |
| CRUD | `apps/backend/dashboard_backend/crud/haushalt_import.py` |
| API-Endpoints | `apps/backend/dashboard_backend/api/v1/endpoints/haushalt_import.py` |
| Frontend | `apps/frontend/src/features/haushalt-import/` |
| Fuzzy-Matching | `apps/backend/dashboard_backend/tasks/finve_matching.py` |
| Debug-Script | `apps/backend/scripts/dump_parse_result.py` (`make summarise-parse-result ID=<n>`) |

---

## Pipeline

Die drei Stufen aus [`feature-pdf-import-unification.md`](feature-pdf-import-unification.md):

| Stufe | Was passiert | Wo |
|---|---|---|
| 1 Textgewinnung | `pdfplumber` liest Tabellenstruktur **und** Seitentext; Seiten ohne Trennlinien werden aus den Textzeilen rekonstruiert. Alternativ liefert die gemeinsame OCR-Stufe dieselben Zeilen aus ihren HTML-Tabellen — welcher Weg zählt, entscheidet `HAUSHALT_EXTRACTION` | `_extract_pages`, `_page_table_rows`, `_extract_pages_from_ocr`, `services/document_ocr.py` |
| 2 Segmentierung | Teil B besteht aus mehreren Tabellen; jede wird als eigener Abschnitt verarbeitet | `_detect_table_sections`, `_parse_section` |
| 3 Semantik | Die Kopfzeile wird **einmal pro Dokument** auf das kanonische Schema gemappt, danach werden alle Werte deterministisch übertragen | `haushalt_columns.resolve_column_map` |

**Zahlenwerte laufen nie durch ein Modell.** Ein LLM wird ausschließlich für die
Zuordnung der 16 Spaltenüberschriften benutzt — und auch das nur, wenn die
deterministische Erkennung an der Kopfzeile scheitert.

### Tabellen von Teil B

Der Bericht enthält (Stand HH-Entwurf 2027) fünf Tabellen. **Alle werden
eingelesen**, jede aber als eigener Abschnitt mit eigener Spaltenzuordnung —
vor der Segmentierung landeten die Zeilen der Tabellen 2–5 als Titel- und
Erläuterungs-Untereinträge an der letzten Sammel-FinVe von Tabelle 1.

| Tabelle | Inhalt | Zeilen 2027 | Identität der Zeile |
|---|---|---|---|
| 1 | Bedarfsplanmaßnahmen | 83 (+2 unmatched) | FinVe-Nummer aus Spalte 2 |
| 2 | Lärmsanierung | 8 | `finve_key` (`t2:SV 52/2017`) |
| 3 | ERTMS | 10 | `finve_key` (`t3:F08Q0770`) |
| 4 | Kleine und Mittlere Maßnahmen der Bundesschienenwege | 11 | `finve_key` (`t4:F 03 E 0793`) |
| 5 | Maßnahmen nach InvKG | 29 | `finve_key` (`t5:B0094`) |

Erkennung über die Seitenüberschrift `Tabelle <N> - <Titel>`. Ein Bericht ohne
solche Überschriften wird wie bisher als eine einzige Tabelle behandelt. Im
Review erscheint jede Tabelle als eigener Block.

### Identität ohne FinVe-Nummer (`finve_key`)

Nur Tabelle 1 druckt eine FinVe-Nummer; sie bleibt der Primärschlüssel von
`finve`. Die übrigen Tabellen identifizieren ihre Maßnahmen über eine
Zeichenkette, die in `finve.finve_key` landet (`tasks/haushalt_keys.py`):

| Erste Spalte im PDF | Schlüssel |
|---|---|
| `YYY SV 52/2017` | `t2:SV 52/2017` |
| `YYY` + FinVe-Spalte `F08Q0770` | `t3:F08Q0770` |
| `YYY F 03 E 0793` | `t4:F 03 E 0793` |
| `B0094 5/ Nr.1 F 21/S 0555` | `t5:B0094` |
| `YYY` ohne Kennung | `t2:foerderrichtlinie-laermsanierung-1999` (Slug + Aufnahmejahr) |

Tabelle 5 nutzt die laufende Nummer, weil sie sich einen durchgehenden
`B####`-Raum mit Tabelle 1 teilt (im Bericht 2027 geprüft: keine Überschneidung).
Wiederholt der Bericht eine Kennung — 2027 steht `F 03 E 0793` zweimal, einmal
für die ursprüngliche Vereinbarung und einmal für die Änderungsvereinbarung —,
bekommt die zweite Zeile `#2` angehängt, in der Reihenfolge des Berichts.

Diese Maßnahmen tragen `temporary_finve_number = true`, und `upsert_finve`
matcht sie beim nächsten Jahrgang über `finve_key`, nicht über die Nummer.

Ihre `finve.id` kommt **nicht** aus der Datenbank-Sequenz, sondern aus einem
reservierten Band ab `900_000` (`_KEYED_FINVE_ID_BASE`). Grund: FinVe-Nummern
sind der Primärschlüssel und werden vom Importer explizit eingefügt — die
Sequenz erfährt davon nichts und steht danach weit unterhalb der vergebenen
Nummern. Die erste automatisch vergebene ID kollidierte deshalb mit einer
gedruckten FinVe-Nummer (`duplicate key value violates unique constraint
"finve_pkey"`). Das Band liegt weit über jeder Nummer, die der Bericht je
druckt (höchste 2027: 5108).

> **Grenze:** Die `#2`-Nummerierung hängt an der Reihenfolge im Bericht. Käme in
> einem künftigen Jahrgang eine weitere Zeile mit derselben Kennung *davor*
> hinzu, verschiebt sich die Zuordnung. Betroffen sind nur echte Doubletten
> (2027: eine).

### Textgewinnung: pdfplumber oder Mistral OCR (`HAUSHALT_EXTRACTION`)

Die Evaluation sieht vor, dass der Haushalt seine Texte langfristig über
dieselbe OCR-Stufe bezieht wie VIB und Fulda — aber erst, wenn ein Vergleich
belegt, dass dabei dieselben Zahlen herauskommen (Schritte 4 und 6 der
empfohlenen Reihenfolge). Genau das steuert eine einzige Einstellung:

| Wert | Was passiert |
|---|---|
| `pdfplumber` (Default) | Der verifizierte Weg, kein OCR-Aufruf, keine Kosten |
| `compare` | Beide Wege laufen über dasselbe PDF. **Die Werte kommen aus pdfplumber**; der Zeilen- und Wertevergleich wird im Parse-Ergebnis gespeichert und im Review angezeigt |
| `ocr` | Die OCR-Stufe liefert die Werte, pdfplumber ist Rückfallebene (Schritt 6 — erst nach einem sauberen `compare`-Lauf) |

Beide Wege übergeben **dieselbe Zeilenform** an Stufe 2: pdfplumber liefert
Zellen aus dem Linienraster, die OCR-Stufe dieselben Zellen aus ihren Tabellen
(`tasks/haushalt_markdown.py`, `OcrResult.tables`). Dadurch sind Segmentierung,
Spaltenzuordnung und Werteübertragung auf beiden Wegen identisch — der Vergleich
misst wirklich nur die Texterkennung.

Der Haushalt fordert die Tabellen dabei als **HTML** an
(`extract_document_text(..., table_format="html")`), nicht als Markdown wie VIB
und Fulda. Ein Haushalts-Datensatz ist eine Zeile mit gestapelten
`davon:`-Titelzeilen darunter, und Markdown kann keinen Zeilenumbruch innerhalb
einer Zelle ausdrücken: das Modell klebt die Zeilen mit Leerzeichen zusammen und
die Zuordnung Wert → Titelzeile ist weg. HTML liefert `<br>` und drückt eine
verbundene Kopfzelle als `colspan`/`rowspan` aus — dieselbe Form, die pdfplumber
zurückgibt.

Auch die drei Identitätsspalten kommen auf beiden Wegen unterschiedlich an:
pdfplumber gibt Lfd. Nr., FinVe-Nummer und Bedarfsplan-Nummer im 2026+-Layout in
*einer* Zelle zurück (`"B0080 275 N19"`), die OCR-Stufe in den drei Spalten, die
der Tabellenkopf deklariert. Die Zeilenerkennung liest beides über die
Spaltenzuordnung (`tests/unit/test_haushalt_id_columns.py`) — die Identität
einer Zeile hängt damit nicht mehr daran, wie ein Jahrgang seine Zellen
verbindet.

Fällt die OCR-Stufe aus oder findet sie keine Zeilen, trägt pdfplumber den
Import; der Fehlschlag wird im Vergleich vermerkt statt verschluckt. Ein Import
scheitert nie an einem fremden Dienst.

### Den Vergleich fahren

```bash
cd apps/backend
OCR_API_KEY=… .venv/bin/python scripts/compare_haushalt_extraction.py EP12_Teil_B.pdf 2027
```

Exit-Code 0 heißt: gleiche Zeilen, gleiche Werte — die Bedingung, um
`HAUSHALT_EXTRACTION=ocr` zu setzen. Exit-Code 1 listet jede abweichende Zeile
und jedes abweichende Feld. Ohne gültigen Schlüssel bricht das Skript ab, statt
einen Vergleich gegen den pymupdf-Notnagel zu berichten (der keine Tabellen
erkennt und die Zahlen wertlos machen würde).

**Stand (2026-09-10): der Vergleich ist gelaufen und rot — `pdfplumber` bleibt
die Quelle der Zahlen.** Gegen den EP-12-Bericht Teil B 2027 und
`mistral-ocr-latest`: Exit-Code 1, 141 Zeilen aus pdfplumber gegen 107 aus der
OCR-Stufe, 79 Wertabweichungen. Drei Ursachen, keine davon auf unserer Seite
behebbar:

- Das Modell lässt den Identitätsmarker `YYY` auf den Seiten der Tabellen 2–4
  weg. Damit fehlen 34 Zeilen — die Tabellen 2, 3 und 4 vollständig.
- ~29 von 5.568 Zahl-Token werden anders gelesen, als der Bericht sie druckt
  (`1.843.520 → 1.043.520`, `98.205 → 58.205`). Kein Reviewer findet das.
- Das Minus eines negativen Deltas kommt als eigene Tabellenzelle zurück; der
  Betrag rutscht dann in die Prozentspalte (5 Zeilen).

In den Geldspalten selbst (`cost_estimate_*`, `spent_two_years_previous`,
`allowed_previous_year`, `spending_residues`, `year_planned`) gibt es über alle
107 gemeinsamen Zeilen **null** Abweichung — das Modell liest die Tabelle im
Kern richtig und scheitert an den Rändern. Die vollständige Auswertung steht in
`feature-pdf-import-unification.md` → *Schritt 6: Vergleich gelaufen*.

Der Umschalter bleibt als Messinstrument für die nächste Modellgeneration.
Abgesichert ist weiterhin, dass der OCR-Pfad aus *originalgetreuen* Tabellen
dieselben Zeilen und Werte erzeugt wie pdfplumber
(`tests/unit/test_haushalt_ocr_path.py` fährt den Round-Trip über die
aufgezeichneten Seiten, in **beiden** Tabellenformaten).

### Mittelherkunft: der Wert gehört zu der Titelzeile, neben der er steht

Eine Maßnahme führt unter `davon:` die Haushaltstitel auf, aus denen sie
finanziert wird, und der Bericht druckt je Titel eine Zeile. `extract_table`
stapelt diese Unterzeilen in mehrzeiligen Zellen — und behält je Spalte **nur
die nicht-leeren Zeilen**. Damit ist nicht mehr ableitbar, auf welcher
gedruckten Zeile ein Wert stand. Beispiel B0092 (2027, Tabelle 5):

```
B0092  Mitteldeutsches Revier: …      aktuell  verausg  bewill  veransch   vorbeh
       (Summenzeile)                  253.333    9.203   7.077     5.634  231.419
       Kap. 1210, Titel 891 14          9.203    9.203       —         —        —
       Kap. 6002, Titel 893 45        244.130        —   7.077     5.634  231.419
```

„Bewilligt" steht auf der Summenzeile und auf der Kap.-6002-Zeile, sonst
nirgends — die Zelle kommt als einzeiliges `"7.077"` an, ununterscheidbar von
einer Maßnahme, deren Titel schlicht keinen Wert haben. Eine Paarung „i-ter
Titel ↔ Zeile i+1 der Wertespalte" gibt den Betrag deshalb keinem Titel; steht
ein Wert dagegen auf einer Zeile *zu viel*, rutscht alles darunter um eins hoch.

Deshalb führt `ExtractedPage.row_lines` **parallel zu `rows`** die gedruckten
Zeilen jeder Tabellenzeile mit, in denselben 16 Spalten: auf Seiten mit
Trennlinien aus den Wortkoordinaten und der Zeilen-Bounding-Box
(`_printed_lines_by_row`), auf den Seiten ohne Trennlinien aus der
zeilenweisen Extraktion, die es ohnehin schon gibt (`_regroup_text_rows`).
`_extract_inline_titel_entries`, `_extract_nachrichtlich_entries` und
`_extract_position_entries` lesen die Werte daraus.

Gemessen am EP-12-Bericht Teil B 2027, gegen die Wortkoordinaten als Wahrheit:
179 vergleichbare Titel-Zeilen, davor 28 mit mindestens einem falschen Wert,
danach **null**. Die Maßnahmen-Ebene war nie betroffen — die Summenzeile ist
immer die erste Zeile einer Tabellenzeile.

Ohne Koordinaten — also auf dem OCR-Pfad, wo `row_lines` leer bleibt — greift
weiter die Paarung über den Zeilenindex. Dort ist der Fehler nicht behebbar:
eine Markdown- oder HTML-Tabelle sagt nicht, auf welcher Druckzeile ein Wert
stand. Auf demselben Bericht gemessen kommt der OCR-Pfad auf 96 von 165
Titel-Zeilen mit falschem Wert; das ist einer der Gründe, warum pdfplumber die
Quelle der Zahlen bleibt (`feature-pdf-import-unification.md`).

### Zeilen ohne Trennlinien rekonstruieren

Die ERTMS-Seiten (2027: S. 27–31) und eine Seite der Kleinen und Mittleren
Maßnahmen (S. 34) drucken keine waagerechten Linien zwischen den Maßnahmen.
pdfplumber fasst dort einen ganzen Abschnitt in die erste Zelle zusammen —
erkennbar an einer ersten Spalte mit mehreren hundert Zeichen. Für solche Seiten
greift `_page_table_rows` auf eine zeilenbasierte Extraktion zurück und
gruppiert die Textzeilen wieder zu logischen Zeilen (`_regroup_text_rows`):
neue Zeile bei `YYY`/`B####` in Spalte 1 oder bei `Erläuterung:` /
`nachrichtlich:` in der Bezeichnungsspalte. Das Ergebnis hat exakt die Zellform
der linienbasierten Extraktion (mehrzeilige Zellen mit gestapelten
Unterpositionen) — auf einer Seite mit Linien geprüft, wo beide Wege dasselbe
liefern müssen.

Dabei wird das Spaltenraster um **einen Punkt nach rechts** verschoben
(`_COLUMN_EDGE_SHIFT`): Der Bericht setzt die Zellen rechtsbündig, und ein
Gedankenstrich als Platzhalter ragt minimal über die Spaltenlinie hinaus (die
Ausgabereste-Linie liegt bei x = 708, der Strich bei x ≈ 708,6). Ohne die
Verschiebung liest pdfplumber ihn als Teil der nächsten Spalte, aus `33.186`
wird `- 33.186` und daraus **−33.186**. Da die Zellen rechtsbündig sind, kann
die Verschiebung nur einen solchen Überhang zurückholen, nie eine Zahl in die
falsche Spalte schieben.

### Spaltenzuordnung (`column_map`)

Jeder Jahrgang beschriftet dieselben 16 Spalten leicht anders („Vorhalten für
2027 ff." vs. „Vorbehalten für 2028 ff.", „Verausgabt bis 2024" vs. „bis 2025").
Statt pro Jahrgang neue Indizes zu pflegen, wird die Kopfzeile gemappt:

1. **`header`** — deterministischer Abgleich der Überschriften gegen Muster je
   Zielfeld. Deckt alle bisher gesehenen Layouts ab, braucht keinen externen Dienst.
2. **`llm`** — ein LLM-Call pro Dokument, nur mit den Überschriftstexten.
3. **`fallback`** — das feste 2026-Layout, damit ein PDF ohne lesbare Kopfzeile
   weiterhin so geparst wird wie bisher.

Die Zuordnung wird **je Tabelle** bestimmt; die des ersten Abschnitts steht im
Parse-Ergebnis (`column_map`) und in `haushalts_parse_result.column_map_json`,
die Quelle jeder weiteren in `sections[].column_map_source`. Das Review zeigt sie
oberhalb der Tabelle an und warnt sichtbar, wenn `fallback` gegriffen hat, eine
Tabelle nicht über die Kopfzeile gemappt werden konnte oder ein Zielfeld ohne
Spalte geblieben ist.

---

## PDF-Spalten-Mapping

Das kanonische Zielschema. Welche PDF-Spalte je Zielfeld tatsächlich gelesen
wird, entscheidet die `column_map` des Dokuments — die Spaltennummern unten sind
die Reihenfolge der Berichte 2026/2027 und zugleich die Fallback-Zuordnung.
Werte in €1.000, außer %-Spalten.

| Spalte | Header | Kanonisches Feld | Ziel-Feld |
|--------|--------|------------------|-----------|
| 1 | Lfd. Nr. | `lfd_nr` | `Budget.lfd_nr` (z.B. "B0080") |
| 2 | Nr. FinVe | `finve_nr` | `Finve.id` (Integer, Matching-Schlüssel) |
| 3 | Nr. Bedarfsplan Schiene | `bedarfsplan` | `Budget.bedarfsplan_number` |
| 4 | Bezeichnung der Investitionsmaßnahme | `name` | `Finve.name` |
| 5 | Aufnahme Jahr | `starting_year` | `Finve.starting_year` |
| 6 | Gesamtausgaben ursprünglich | `cost_original` | `Budget.cost_estimate_original` |
| 7 | Gesamtausgaben Vorjahr | `cost_last_year` | `Budget.cost_estimate_last_year` |
| 8 | Gesamtausgaben aktuell | `cost_actual` | `Budget.cost_estimate_actual` |
| 9 | Δ zum Vorjahr (€1.000) | `delta_abs` | `Budget.delta_previous_year` |
| 10 | Δ zum Vorjahr (%) | `delta_rel` | `Budget.delta_previous_year_relativ` |
| 11 | Gründe | `delta_reasons` | `Budget.delta_previous_year_reasons` |
| 12 | Verausgabt bis Y-2 | `spent_two_years_previous` | `Budget.spent_two_years_previous` |
| 13 | Bewilligt Y-1 | `allowed_previous_year` | `Budget.allowed_previous_year` |
| 14 | Übertragene Ausgabereste | `ausgabereste` | `Budget.spending_residues` |
| 15 | Veranschlagt Y | `year_planned` | `Budget.year_planned` |
| 16 | Vorhalten Y+1 ff. | `next_years` | `Budget.next_years` |

Titelunterzeilen (Spalten 7, 8, 12–16) → `BudgetTitelEntry` verknüpft mit `HaushaltTitel`.
Nachrichtlich-Zeilen (kursiv) werden als `is_nachrichtlich=True` gespeichert.

---

## Haushaltstitel

Lookup-Tabelle `haushalt_titel` (auto-erweiterbar via `get_or_create`):

| Schlüssel | Beschreibung |
|-----------|--------------|
| `891_01` | Kap. 1202, Titel 891 01 |
| `891_03` | Kap. 1202, Titel 891 03 |
| `891_04` | Kap. 1202, Titel 891 04 |
| `891_52` | Kap. 1408, Titel 891 52 |
| `891_91` | Kap. 1202 (alt), Titel 891 91 – IIP Schiene |
| `891_11` | Kap. 1202 (alt), Titel 891 11 – LUFV (alt) |

Neue Titel in künftigen PDFs werden automatisch registriert.

---

## Parser-Besonderheiten (Format 2026/2027)

- Erste 3 Spalten zusammengeführt in einer Zelle: `B0080 275 N19`
- Kapitel/Titel als inline mehrzeilige Zellen (kein eigener Block)
- Key parser functions: `_parse_combined_id_cell`, `_extract_project_name`, `_extract_inline_titel_entries`, `_extract_nachrichtlich_entries`
- `_KAP_TITEL_RE` mit `(alt)`-Zusatz
- `_BHO_NOTE_RE` für Haushaltsnoten
- Kopf-, Einheiten- und Nummerierungszeilen werden über `haushalt_columns.is_header_row` erkannt (wiederholen sich auf jeder Seite)
- Die `TABELLENSUMMEN`-Zeile am Tabellenende ist keine FinVe-Zeile und wird übersprungen
- Zeilen mit Lfd. Nr., aber ohne FinVe-Nummer (z. B. `B0140 L 03`) gehen als `unmatched_rows` in die Nachbearbeitung

---

## Sammelfinanzierungsvereinbarungen (SV-FinVes)

- **Erkennung**: Regex `_SV_NAME_RE` auf Projektnamen; `YYY`-Prefix in Spalte 0 (statt `B<digits>`)
- **DB**: `is_sammel_finve` Boolean auf `Finve`-Modell
- **Parser-Architektur**: Flat-Table-Ansatz — alle Seiten werden zuerst gesammelt (`all_table_rows`), dann in einem einzigen Pass verarbeitet → löst Seitenumbruch-Artefakte
- **Seitenumbruch-Recovery**: `_build_sv_raw_lookup` scannt Raw-Text jeder Seite nach `^YYY <nr> <name> 20\d\d`-Pattern → `global_sv_lookup`; orphaned SV-Zeilen (col0='') werden darüber wiederhergestellt
- **Erläuterung-Continuation**: `_is_erlaeuterung_continuation` erkennt Folgeseiten langer Erläuterungen (keine "Erläuterung:"-Präfix, aber Bullet-Chars)
- **Fuzzy-Matching**: `suggest_per_erlaeuterung_project` (1:1 pro Unterzeile), `suggest_projects_for_sv_erlaeuterung` (dedup, für Parent-FinVe)
- **Jahrestracking**: `finve_to_project.haushalt_year` — `NULL` = permanent (reguläre FinVes), `<year>` = jahresspezifisch (SV-FinVes); historische Projektzu-/abgänge bleiben erhalten

---

## DB-Modelle

- `HaushaltTitel` — Lookup-Tabelle für Haushaltstitel
- `BudgetTitelEntry` — Titeluntereinträge je Budget-Zeile
- `Finve.finve_key` — Identität einer Maßnahme ohne FinVe-Nummer (Migration `20260908002`)
- `HaushaltsParseResult` — Zwischen-/Endergebnis des Parse-Tasks; speichert zusätzlich den Dokumenttext (`ocr_raw_text`/`ocr_status`/`ocr_model` aus `models.mixins.OcrSourceMixin`) und die verwendete Spaltenzuordnung (`column_map_json`, `column_map_source`)
- `FinveChangeLog`, `BudgetChangeLog` — Änderungshistorie
- `UnmatchedBudgetRow` — Zeilen ohne Projekt-Match zur Nachbearbeitung
- Migrationen: `20260308001_add_is_sammel_finve_to_finve.py`, `20260310001_add_haushalt_year_to_finve_to_project.py`, `20260908001_add_haushalt_parse_provenance.py`

---

## API-Endpunkte

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/v1/import/haushalt/parse` | Startet Parse-Task (Celery) |
| GET | `/api/v1/import/haushalt/parse-result` | Ergebnis abfragen (Polling) |
| POST | `/api/v1/import/haushalt/confirm` | Import bestätigen |
| GET/PATCH | `/api/v1/import/haushalt/unmatched` | Ungematchte Zeilen nachbearbeiten |

---

## Frontend-Features

- Upload-Flow mit Celery-Polling
- Review-Tabelle (neu / geändert / unmatched)
- Projektzuordnung per MultiSelect (FinVe → mehrere Projekte)
- Separate Sektion "Sammel-FinVes (Phase 2)" mit per-Projekt-Unterzeilen + Fuzzy-Vorschlägen
- Unmatched-Nachbearbeitung nach Confirm
- Import-Anleitung unter `/admin/haushalt-import/guide` (Schritt-für-Schritt für Endnutzer)
- Panel „Spaltenzuordnung“ über der Review-Tabelle: welche Tabellen mit wie vielen Zeilen eingelesen wurden, woher die Zuordnung stammt, und je Zielfeld die erkannte PDF-Spalte
- Review-Tabelle nach Tabellen von Teil B gruppiert (Überschrift je Tabelle); Zeilen ohne FinVe-Nummer zeigen statt der Nummer ihren `finve_key`
- Nach Bestätigung: automatische Weiterleitung zur Import-Übersicht

---

## Tests

| Test | Deckt ab |
|---|---|
| `tests/unit/test_haushalt_columns.py` | Kopfzeilen-Erkennung, Spaltenzuordnung (inkl. vertauschtem Layout und LLM-Rückfallebene), Tabellen-Segmentierung |
| `tests/unit/test_haushalt_parse_2027.py` | Golden-Lauf gegen den EP-12-Bericht Teil B 2027 — alle fünf Tabellen, Segmentierung, Spaltenzuordnung, Zeilen-Identität und exakte Werte gegen den gedruckten Bericht |
| `tests/unit/test_haushalt_keys.py` | Schlüssel-Bildung für Maßnahmen ohne FinVe-Nummer |
| `tests/unit/test_haushalt_markdown.py` | Tabellen der OCR-Stufe (Markdown **und** HTML) → Zeilenform des Parsers |
| `tests/unit/test_haushalt_id_columns.py` | Zeilenerkennung, egal ob die drei Identitätsspalten verbunden oder getrennt ankommen |
| `tests/unit/test_haushalt_ocr_path.py` | OCR-Pfad end-to-end (Round-Trip), Vergleichslogik und die drei `HAUSHALT_EXTRACTION`-Modi inkl. OCR-Ausfall |
| `tests/unit/test_haushalt_parser_blocks.py` | Titel-/Nachrichtlich-Blöcke und die Zuordnung der Mittelherkunft über die gedruckten Zeilen |
| `tests/unit/test_haushalt_upsert.py` | Upsert nach dem Bestätigen |

Die Fixture `tests/fixtures/haushalt_ep12_2027_pages.json` ist die aufgezeichnete
pdfplumber-Ausgabe (Seitentext + Tabellenzeilen) von neun repräsentativen Seiten
des Berichts — je mindestens eine aus jeder der fünf Tabellen, darunter die
rekonstruierten ERTMS- und KMM-Seiten — das PDF selbst wäre mit ~3,8 MB zu groß fürs Repo. Neue Seiten
lassen sich mit `_extract_pages` aus einem PDF nachziehen.
