# Feature: Haushaltsberichte-Import

## Ziel

Jährlicher Import der Anlage VWIB, Teil B (Bundeshaushalt) als PDF.
Die Tabelle enthält alle Bedarfsplanmaßnahmen des Schienenwegeinvestitionsprogramms
mit FinVe-Nummern, Kostenschätzungen und Jahresansätzen je Haushaltskonto.

**Status: vollständig implementiert**

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
| Debug-Script | `apps/backend/scripts/dump_parse_result.py` |

---

## Pipeline

Die drei Stufen aus [`feature-pdf-import-unification.md`](feature-pdf-import-unification.md):

| Stufe | Was passiert | Wo |
|---|---|---|
| 1 Textgewinnung | `pdfplumber` liest Tabellenstruktur **und** Seitentext. Optional läuft zusätzlich die gemeinsame OCR-Stufe (`HAUSHALT_OCR_ENABLED`), deren Text mit dem Lauf gespeichert wird | `_extract_pages`, `services/document_ocr.py` |
| 2 Segmentierung | Teil B besteht aus mehreren Tabellen; nur die Bedarfsplan-Tabelle wird verarbeitet | `_detect_table_sections`, `_select_import_section` |
| 3 Semantik | Die Kopfzeile wird **einmal pro Dokument** auf das kanonische Schema gemappt, danach werden alle Werte deterministisch übertragen | `haushalt_columns.resolve_column_map` |

**Zahlenwerte laufen nie durch ein Modell.** Ein LLM wird ausschließlich für die
Zuordnung der 16 Spaltenüberschriften benutzt — und auch das nur, wenn die
deterministische Erkennung an der Kopfzeile scheitert.

### Tabellen von Teil B

Der Bericht enthält (Stand HH-Entwurf 2027) fünf Tabellen. Nur die erste liefert
FinVe-Zeilen; die übrigen listen Positionen ohne FinVe-Nummer und werden erkannt,
protokolliert und übersprungen — vor der Segmentierung landeten ihre Zeilen als
Titel- und Erläuterungs-Untereinträge an der letzten Sammel-FinVe von Tabelle 1.

| Tabelle | Inhalt | Import |
|---|---|---|
| 1 | Bedarfsplanmaßnahmen | ja |
| 2 | Lärmsanierung | nein |
| 3 | ERTMS | nein |
| 4 | Kleine und Mittlere Maßnahmen der Bundesschienenwege | nein |
| 5 | Maßnahmen nach InvKG | nein |

Erkennung über die Seitenüberschrift `Tabelle <N> - <Titel>`. Ein Bericht ohne
solche Überschriften wird wie bisher als eine einzige Tabelle behandelt.

### Spaltenzuordnung (`column_map`)

Jeder Jahrgang beschriftet dieselben 16 Spalten leicht anders („Vorhalten für
2027 ff." vs. „Vorbehalten für 2028 ff.", „Verausgabt bis 2024" vs. „bis 2025").
Statt pro Jahrgang neue Indizes zu pflegen, wird die Kopfzeile gemappt:

1. **`header`** — deterministischer Abgleich der Überschriften gegen Muster je
   Zielfeld. Deckt alle bisher gesehenen Layouts ab, braucht keinen externen Dienst.
2. **`llm`** — ein LLM-Call pro Dokument, nur mit den Überschriftstexten.
3. **`fallback`** — das feste 2026-Layout, damit ein PDF ohne lesbare Kopfzeile
   weiterhin so geparst wird wie bisher.

Die gewählte Zuordnung steht im Parse-Ergebnis (`column_map`) und in
`haushalts_parse_result.column_map_json`; das Review zeigt sie oberhalb der
Tabelle an und warnt sichtbar, wenn `fallback` gegriffen hat oder ein Zielfeld
ohne Spalte geblieben ist.

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
- Panel „Spaltenzuordnung" über der Review-Tabelle: welche Tabelle(n) eingelesen bzw. übersprungen wurden, woher die Zuordnung stammt, und je Zielfeld die erkannte PDF-Spalte
- Nach Bestätigung: automatische Weiterleitung zur Import-Übersicht

---

## Tests

| Test | Deckt ab |
|---|---|
| `tests/unit/test_haushalt_columns.py` | Kopfzeilen-Erkennung, Spaltenzuordnung (inkl. vertauschtem Layout und LLM-Rückfallebene), Tabellen-Segmentierung |
| `tests/unit/test_haushalt_parse_2027.py` | Golden-Lauf gegen den EP-12-Bericht Teil B 2027 — Segmentierung, Spaltenzuordnung und exakte Werte gegen den gedruckten Bericht |
| `tests/unit/test_haushalt_parser_blocks.py` | Titel-/Nachrichtlich-Blöcke |
| `tests/unit/test_haushalt_upsert.py` | Upsert nach dem Bestätigen |

Die Fixture `tests/fixtures/haushalt_ep12_2027_pages.json` ist die aufgezeichnete
pdfplumber-Ausgabe (Seitentext + Tabellenzeilen) von sechs repräsentativen Seiten
des Berichts — das PDF selbst wäre mit ~3,8 MB zu groß fürs Repo. Neue Seiten
lassen sich mit `_extract_pages` aus einem PDF nachziehen.
