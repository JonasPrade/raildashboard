# Feature: Fulda-Runde über MCP + Skill einlesen

> Löst den OCR+LLM-Upload des Fulda-Importers (#46) ab. Datenmodell, Ableitung und
> Freigabe-Seite bleiben die Basis; neu sind das Dokument-Objekt, feinere Kategorien,
> die Trennung Ist/Prognose und der Weg über MCP-Tools + Skill.
> Entschieden 2026-10-17 (Widerspruchs-Check W1–W6, siehe [Entscheidungen](#entscheidungen)).

## Kontext / Ziel

In der **Fulda-Runde** stimmen BMV, EBA, DB InfraGO und DB Energie jährlich ab, welche
Bedarfsplan-Vorhaben im Folgejahr in die nächste Leistungsphase (Lph 1/2, Lph 3/4, Bau)
übergehen. Öffentlich wird das Ergebnis nur über **Antworten der Bundesregierung auf
Kleine Anfragen** („Ergebnisse der Fulda-Runde 20xx“). Diese Antworten unterscheiden
sich von Jahr zu Jahr stark:

- **2025 (Drs. 20/395):** fast leer — „Fulda-Prozess nicht abgeschlossen“; nur eine
  Aufzählung „schließen 2025 Lph 1/2 ab“.
- **2026 (Drs. 21/5855):** zwei Tabellen Projekt/Abschnitt (aktuell in Sammel-FinVe
  Lph 1/2 bzw. Lph 3/4), Aufzählungen getrennt nach „Abschluss Lph. 1“, „Abschluss
  Lph. 2“, „Abschluss Lph 3/4“; Neuaufnahmen und Bau-FinVe „abhängig vom Haushalt 2027“.
- Die Frage-Nummern wechseln, Sammelzellen nennen mehrere Teilmaßnahmen („Großknoten
  Hamburg“: sechs), Fußnoten listen Standorte (KV), viele Aussagen sind DB-Prognosen
  („nach Angaben der DB AG voraussichtlich bis Ende 2026“).

Ein fester LLM-Prompt mit fünf Kategorien hat diese Vielfalt nicht getragen. Ziel: Ein
Agent (Claude) liest das PDF selbst, der **Skill** gibt ihm die Leseregeln, die
**MCP-Tools** geben die Datenfelder vor und prüfen sie, der Mensch gibt in der
bestehenden Jahres-Ansicht frei.

**Glaubwürdigkeit:** Die Fulda-Runde ist eine Vorankündigung auf Arbeitsebene, ihre
Glaubwürdigkeit liegt etwas unter den Berichten: Vertrauen **0.55** (VIB 0.6, Medien 0.4).

## Scope

**In scope:**

1. Neues Dokument-Objekt `fulda_document`; Einträge hängen daran.
2. Feinere Kategorien mit fester Aussage-Art (Ist / Prognose / Neuaufnahme / ohne
   Folgephase) und Herkunftsfeldern je Eintrag.
3. Ableitung: Ist-Aussagen setzen die Phase, Prognosen nur einen erwarteten Termin.
4. Prognose-Panel und Zeitstrahl: Termine nach Glaubwürdigkeit × Aktualität statt fester
   Rangfolge (VIB-PFA vs. Fulda).
5. MCP-Tools für den ganzen Ablauf, Recht `fulda.import`.
6. Skill `.claude/skills/fulda-runde/SKILL.md` (Ordner aller Dashboard-Skills, siehe `AGENT.md` → „Skills“).
7. Abbau: OCR+LLM-Upload, Celery-Task, Upload-UI; „Fulda-Runde“ verschwindet aus den
   manuellen Quellen.
8. Migration löscht die alten Fulda-Daten (Neu-Einlesen ab 2019 macht der User).

**Out of scope:** Finanzzahlen aus den Antworten (Planungsmittel, Mittelbedarf) — gehören,
wenn überhaupt, zu den Infraplan-Kennzahlen. Anbindung des Skills an claude.ai (macht
der User).

## Datenmodell

**`fulda_document`** (neu, eine Zeile je ausgewerteter Antwort):

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | int PK | |
| `year` | int, indiziert | Fulda-Runde-Jahr |
| `drucksache` | str(50), unique | z. B. „21/5855“ |
| `title` | str(500)? | Titel der Kleinen Anfrage |
| `document_date` | date, Pflicht | Datum der Antwort; Beobachtungsdatum der Ist-Aussagen und Basis der Aktualität |
| `dip_url` | str(500)? | Link auf DIP |
| `answer_status` | str(20) | `VOLLSTAENDIG` · `TEILWEISE` · `OHNE_ERGEBNIS` |
| `note` | text? | z. B. unbeantwortete Fragen und Begründung |
| `created_at`, `created_by_user_id`, `username_snapshot` | | Provenienz |

**`fulda_announcement`** (bestehend, erweitert):

- neu: `document_id` (FK → `fulda_document`, CASCADE, indiziert), `question_ref`
  (str(100), z. B. „Frage 3“), `page` (int), `raw_text` (text, Zeile wörtlich),
  `attributed_to` (str(20): `BMV` · `DB`), `assignment_note` (text, Begründung der
  Zuordnung).
- bleibt: `announcement_year` (= `document.year`, für Filter), `raw_name`, `abschnitt`,
  `category`, `expected_date`, `confirmed`, m:n `projects`, Provenienz.
- `source_label`, `document_date`, `announced_phase` bleiben als Spalten stehen
  (Expand/Contract), werden aber nicht mehr geschrieben oder gelesen. Entfernen in einer
  späteren Migration.

**Sammelzellen:** Eine Tabellenzelle mit mehreren Teilmaßnahmen darf in mehrere Einträge
aufgeteilt werden (gleicher `raw_text`, je Eintrag eigener `abschnitt`). Dedupliziert
wird nicht mehr automatisch; der Agent legt jede Aussage genau einmal an.

### Kategorien

Kategorie bestimmt Aussage-Art und Phase fest (`services/fulda_categories.py`):

| Kategorie | Bedeutung | Art | Wirkung |
|---|---|---|---|
| `IN_LPH_1_2` | aktuell in der Sammel-FinVe Lph 1/2 | IST | Phase Vorplanung |
| `IN_LPH_3_4` | aktuell in der Sammel-FinVe Lph 3/4 | IST | Phase Genehmigungsplanung |
| `HAS_BAUFINVE` | hat eine Baufinanzierungsvereinbarung | IST | Phase Bau |
| `COMPLETED_LPH_1_2_NO_FOLLOWUP` | Lph 1/2 abgeschlossen, keine Aufnahme in Lph 3/4 | OHNE_FOLGEPHASE | Phase Vorplanung |
| `COMPLETED_LPH_3_4_NO_FOLLOWUP` | Lph 3/4 abgeschlossen, keine Bau-FinVe | OHNE_FOLGEPHASE | Phase Genehmigungsplanung |
| `COMPLETES_LPH_1` | Lph 1 wird abgeschlossen | PROGNOSE | nur Hinweis (keine Beobachtung) |
| `COMPLETES_LPH_2` | Lph 2 bzw. Lph 1/2 wird abgeschlossen | PROGNOSE | Termin Genehmigungsplanung |
| `COMPLETES_LPH_3_4` | Lph 3/4 wird abgeschlossen | PROGNOSE | Termin Bau |
| `NEW_LPH_1_2` | soll neu in die Sammel-FinVe Lph 1/2 | NEUAUFNAHME | Termin Vorplanung |
| `NEW_LPH_3_4` | soll neu in die Sammel-FinVe Lph 3/4 | NEUAUFNAHME | Termin Genehmigungsplanung |
| `NEW_BAUFINVE` | soll eine Baufinanzierungsvereinbarung erhalten | NEUAUFNAHME | Termin Bau |

`COMPLETES_LPH_1` erzeugt keine Beobachtung: Die Hauptspur kennt Lph 1 und Lph 2 nicht
getrennt; der Eintrag bleibt als Hinweis in der Jahres-Ansicht sichtbar.

## Ableitung

- **IST / OHNE_FOLGEPHASE** → abgeleitete MAIN-Beobachtung, Quelle `FULDA_RUNDE`,
  `observed_date = document.document_date`, Vertrauen 0.55 × Aktualität. Liefert **keinen**
  Termin für Prognose-Panel oder Zeitstrahl (nur Beleg).
- **PROGNOSE / NEUAUFNAHME** → abgeleitete MAIN-Beobachtung mit `is_expected = True`,
  `observed_date = expected_date` (fehlt es: 31.12. des Dokumentjahres). Sie hebt die
  Phase **nicht** (bestehende `is_expected`-Regel in `derive_headline`) und erscheint im
  Prognose-Panel und im Zeitstrahl mit der Quelle „Fulda-Runde“ — **nicht** als „Manuell“.
  Ein angekündigter Abschluss ist der **frühestmögliche** Beginn der Folgephase, nicht
  ihr sicherer Start.
- Nur bestätigte Einträge (`confirmed`) mit mindestens einem Projekt materialisieren;
  Provenienz bleibt `progress_observation.fulda_announcement_id`.

## Termine im Prognose-Panel und Zeitstrahl

Bisher galt eine feste Rangfolge: VIB-PFA als Basis, Fulda überschreibt, wenn früher.
**Neu (W1):** Je Phase gewinnt der Termin mit der **höchsten Glaubwürdigkeit ×
Aktualität** — Vertrauen der Quelle (`SOURCE_TYPE_DEFAULT_TRUST`) × `recency_decay` des
**Berichtsstands** (VIB: `vib_report.report_date`, sonst 31.12. des Berichtsjahres;
Fulda: `fulda_document.document_date`). Gleichstand → der frühere Termin. Ein neuer
Fulda-Jahrgang schlägt so einen älteren VIB, ein frischer VIB einen alten Fulda-Jahrgang.
Manuelle erwartete Termine gewinnen weiterhin immer (Grundsatz „manuelle Eingaben
übersteuern abgeleitete“); als „manuell“ zählen alle **nicht abgeleiteten**
`is_expected`-Beobachtungen, Fulda-Prognosen sind abgeleitet (`is_derived`) und laufen nie
über diesen Weg. Umsetzung: `split_expected` / `fulda_report_dates` in
`crud/projects/progress.py`, `concrete_milestone_dates` in `services/progress_forecast.py`.

## MCP-Tools

Neues Modul `mcp/tools/fulda.py`; alle Tools prüfen `fulda.import`.

| Tool | Art | Zweck |
|---|---|---|
| `list_fulda_documents` | lesend | Dokumente mit Jahr, Drucksache, Antwortstand, Zählern (gesamt / zugeordnet / bestätigt) |
| `create_fulda_document(year, drucksache, document_date, …)` | schreibend | Dokument anlegen; gleiche Drucksache → Fehler mit Verweis auf die vorhandene id |
| `update_fulda_document(document_id, changes)` | schreibend | Metadaten, Antwortstand, Notiz |
| `list_fulda_categories` | lesend | Kategorien mit Bedeutung, Art und Wirkung (die Tabelle oben) |
| `add_fulda_entries(document_id, entries[])` | schreibend | Einträge anlegen; prüft Kategorie, verlangt `raw_text`; liefert je Eintrag Zuordnungsvorschläge (Fuzzy-Match Oberprojekt → Teilprojekt) |
| `list_fulda_entries(document_id, only_open?)` | lesend | Einträge mit Zuordnung und Vorschlägen |
| `assign_fulda_entry(entry_id, project_ids, note)` | schreibend | Zuordnung mit Begründung (`assignment_note`) |
| `update_fulda_entry(entry_id, changes)` | schreibend | Kategorie, Abschnitt, Termin, … korrigieren |
| `delete_fulda_entry(entry_id)` | löschend | Fehleintrag entfernen |
| `confirm_fulda_document(document_id)` | schreibend | alle zugeordneten offenen Einträge bestätigen → Beobachtungen entstehen |

Fehlende Teilprojekte legt der Agent mit dem bestehenden `create_project` an.
Bestätigen bleibt bewusst ein eigener Schritt; der Skill bestätigt nur, was eindeutig ist,
und meldet den Rest.

## Skill

`.claude/skills/fulda-runde/SKILL.md` — wie alle Dashboard-Skills in `.claude/skills/`,
gelistet in `.claude/skills/README.md`, von dort von Hand nach claude.ai hochgeladen.
Inhalt kurz:

1. Dokument erkennen (Jahr, Drucksache, Datum), prüfen, ob es schon existiert.
2. Fragen nach ihrem **Wortlaut** einer Kategorie zuordnen, nie nach der Nummer.
3. Ist vs. Prognose unterscheiden („befinden sich“, „sind enthalten“ vs. „werden …
   abgeschlossen“, „sollen … erhalten“); `attributed_to` aus „nach Angaben der DB AG“.
4. Sammelzellen aufteilen, Wortlaut in `raw_text` erhalten; Fußnoten auflösen.
5. Unbeantwortete Fragen nicht als Einträge, sondern als Notiz am Dokument; Antwortstand
   setzen.
6. Projekte zuordnen: Teilprojekt bevorzugen, Begründung schreiben, Unklares offen lassen.
7. Bestätigen, Bericht: übernommen / selbst entschieden / offen.

## REST-API und Oberfläche

- Entfällt: `POST /import/fulda/parse`, `tasks/fulda.py`, `tasks/fulda_extraction.py`,
  Upload-Formular und Task-Polling in `FuldaImportPage`, `useParseFulda`.
- Bleibt (Recht `fulda.import` statt `progress.edit`): Jahres-Übersicht, Jahres-Detail mit
  Zuordnen/Übernehmen, „Alle übernehmen“, Eintrag/Jahr löschen. Die Jahres-Ansicht zeigt
  die neuen Kategorien in fester Reihenfolge sowie Dokument, Frage, Seite und Wortlaut.
- Neu: `GET /import/fulda/documents` für die Übersicht (Dokumente statt nur Jahre).
- Die Übersicht erklärt, dass Fulda-Antworten über Claude + Skill eingelesen werden.
- „Fulda-Runde“ ist keine manuelle Quelle mehr (Bearbeiten-Drawer, Schema
  `ProgressObservationCreate`, MCP `add_progress_observation`). Bestehende manuelle
  Fulda-Beobachtungen bleiben unverändert stehen.

## Migration

- Tabelle `fulda_document`, neue Spalten an `fulda_announcement`.
- **Löscht** alle `fulda_announcement`-Zeilen (Links per CASCADE) und die daraus
  abgeleiteten Beobachtungen (`progress_observation` mit `fulda_announcement_id` bzw.
  `is_derived` + `FULDA_RUNDE`). Entscheidung W6: Der User liest alle Jahrgänge ab 2019
  neu ein.
- Vergibt `fulda.import` an die Editor-Systemrolle.
- Rückwärtskompatibel: alte Spalten bleiben; älterer Code sieht leere Fulda-Daten.

## Entscheidungen

| # | Datum | Entscheidung |
|---|---|---|
| — | 2026-10-17 | Vertrauen `FULDA_RUNDE` 0.55 (vorher 0.7). |
| — | 2026-10-17 | Prognosen setzen keine Phase, nur einen erwarteten Termin („Nur Termin“). |
| — | 2026-10-17 | MCP-Tools für Importe sind allgemein erlaubt (`feature-mcp-server.md`). |
| — | 2026-10-17 | OCR+LLM-Upload für Fulda entfällt. |
| W1 | 2026-10-17 | Termine je Phase nach Glaubwürdigkeit × Aktualität, keine feste Überschreib-Rangfolge VIB-PFA/Fulda. |
| W2 | 2026-10-17 | Fulda-Prognosen sind abgeleitete Beobachtungen (Quelle Fulda), nie „Manuell“. |
| W3 | 2026-10-17 | „Fulda-Runde“ aus den manuellen Quellen entfernt. |
| W4 | 2026-10-17 | Eigenes Recht `fulda.import`. |
| W5 | 2026-10-17 | Skill im Projekt-Skill-Ordner `.claude/skills/` (gemeinsame Regel aller Dashboard-Skills, `AGENT.md`); claude.ai-Anbindung macht der User. |
| W6 | 2026-10-17 | Alte Fulda-Daten werden gelöscht, Neu-Einlesen ab 2019. |

## Akzeptanzkriterien

- [ ] Über MCP lässt sich die Antwort 21/5855 vollständig erfassen: Dokument,
      Einträge aller Projekt-Listen, Zuordnung, Bestätigung.
- [ ] Ein Projekt aus „Abschluss Lph 3/4 im Laufe 2026“ bleibt in seiner Phase und zeigt
      im Prognose-Panel „Bau ab 31.12.2026 (Fulda-Runde)“.
- [ ] Ein Projekt aus der Tabelle Sammel-FinVe Lph 3/4 bekommt eine Fulda-Beobachtung
      „Genehmigungsplanung“ mit dem Dokumentdatum und Vertrauen 0.55 × Aktualität.
- [ ] Ein Fulda-Termin von 2026 schlägt im Prognose-Panel einen VIB-PFA-Termin aus einem
      Bericht von 2023; ein manueller erwarteter Termin schlägt beide.
- [ ] Ohne `fulda.import` verweigern REST und MCP den Zugriff.
- [ ] Der Upload-Weg ist entfernt; „Fulda-Runde“ fehlt in den manuellen Quellen.
- [ ] Nach der Migration gibt es keine Fulda-Einträge und keine daraus abgeleiteten
      Beobachtungen mehr.
