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
| CRUD | `apps/backend/dashboard_backend/crud/haushalt_import.py` |
| API-Endpoints | `apps/backend/dashboard_backend/api/v1/endpoints/haushalt_import.py` |
| Frontend | `apps/frontend/src/features/haushalt-import/` |
| Fuzzy-Matching | `apps/backend/dashboard_backend/tasks/finve_matching.py` |
| Debug-Script | `apps/backend/scripts/dump_parse_result.py` |

---

## PDF-Spalten-Mapping

Werte in €1.000, außer %-Spalten.

| Spalte | Header | Ziel-Feld |
|--------|--------|-----------|
| 1 | Lfd. Nr. | `Budget.lfd_nr` (z.B. "B0080") |
| 2 | Nr. FinVe | `Finve.id` (Integer, Matching-Schlüssel) |
| 3 | Nr. Bedarfsplan Schiene | `Budget.bedarfsplan_number` |
| 4 | Bezeichnung der Investitionsmaßnahme | `Finve.name` |
| 5 | Aufnahme Jahr | `Finve.starting_year` |
| 6 | Gesamtausgaben ursprünglich | `Budget.cost_estimate_original` |
| 7 | Gesamtausgaben Vorjahr | `Budget.cost_estimate_last_year` |
| 8 | Gesamtausgaben aktuell | `Budget.cost_estimate_actual` |
| 9 | Δ zum Vorjahr (€1.000) | `Budget.delta_previous_year` |
| 10 | Δ zum Vorjahr (%) | `Budget.delta_previous_year_relativ` |
| 11 | Gründe | `Budget.delta_previous_year_reasons` |
| 12 | Verausgabt bis Y-2 | `Budget.spent_two_years_previous` |
| 13 | Bewilligt Y-1 | `Budget.allowed_previous_year` |
| 14 | Übertragene Ausgabereste | `Budget.spending_residues` |
| 15 | Veranschlagt Y | `Budget.year_planned` |
| 16 | Vorhalten Y+1 ff. | `Budget.next_years` |

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

## Parser-Besonderheiten (2026-Format)

- Erste 3 Spalten zusammengeführt in einer Zelle: `B0080 275 N19`
- Kapitel/Titel als inline mehrzeilige Zellen (kein eigener Block)
- Key parser functions: `_parse_combined_id_cell`, `_extract_project_name`, `_extract_inline_titel_entries`, `_extract_nachrichtlich_entries`
- `_KAP_TITEL_RE` mit `(alt)`-Zusatz
- `_BHO_NOTE_RE` für Haushaltsnoten

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
- `HaushaltsParseResult` — Zwischen-/Endergebnis des Parse-Tasks
- `FinveChangeLog`, `BudgetChangeLog` — Änderungshistorie
- `UnmatchedBudgetRow` — Zeilen ohne Projekt-Match zur Nachbearbeitung
- Migration: `20260308001_add_is_sammel_finve_to_finve.py`, `20260310001_add_haushalt_year_to_finve_to_project.py`

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
- Nach Bestätigung: automatische Weiterleitung zur Import-Übersicht
