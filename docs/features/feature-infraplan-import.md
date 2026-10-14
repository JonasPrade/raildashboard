# Feature: Infraplan-Import

> **Status: geplant.** Grundlage ist der Infraplan 2026 (BMV, 6. Oktober 2026),
> abgelegt unter `docs/261002_Infraplan_2026_1.pdf`. Ein Prototyp-Parser
> (pdfplumber, ohne LLM) liest daraus 264 Maßnahmenzeilen; die Zahlen unten
> stammen aus diesem Lauf.

## Ziel

Der **Infraplan** ist der jährlich fortgeschriebene Fünfjahresplan des Bundes für
die Schieneninfrastruktur (Infraplan 2026 = 2026–2030). Er enthält je Maßnahme
Realisierungsstand/Leistungsphase, geplantes Inbetriebnahmejahr, Gesamtwertumfang
(GWU) bzw. Gesamtkosten und den Stand der parlamentarischen Befassung.

Der Import macht diese Angaben im Dashboard nutzbar:

1. **Planungsstand** — Realisierungsstand und parlamentarische Befassung fließen als
   neue Quelle `INFRAPLAN` in den Projektfortschritt.
2. **Zeitplan** — das geplante Inbetriebnahmejahr fließt in die Prognose.
3. **Kosten** — GWU/Gesamtkosten werden je Jahrgang gespeichert, sodass
   Kostensteigerungen und Terminverschiebungen zwischen Infraplan 2026, 2027, …
   sichtbar werden. Das ist der eigentliche Mehrwert gegenüber einem einmaligen
   Abtippen.

Nicht-Ziel (vorerst): die acht Steuerungskennzahlen und die Kennzahl-Maßnahmenlisten
im Anhang (siehe [Ausbaustufen](#ausbaustufen)).

---

## Entscheidung: deterministischer Importer statt MCP-Eintrag

Erwogen wurden (a) ein MCP-Server + Skill, mit dem ein Agent die Angaben je Projekt
einträgt, und (b) ein Importer nach dem Muster Haushalt/VIB.

Gewählt: **(b) Importer**, MCP nur für die Nacharbeit.

- Der Infraplan kommt **jährlich**; ein Importer ist wiederholbar, idempotent und
  hält die Herkunft je Wert und Jahrgang fest. Agent-Eintrag wäre bei ~260 Zeilen
  teuer, nicht reproduzierbar und ohne Jahrgangsbezug.
- Die Maßnahmenlisten sind **saubere Tabellen mit Textlayer** — anders als beim VIB
  braucht es weder OCR noch LLM. Das Muster ist das des Haushalts (pdfplumber,
  Zeilenrekonstruktion ohne Trennlinien).
- Der MCP-Server klammert Importe bewusst aus (`feature-mcp-server.md`). Was nach dem
  Import übrig bleibt (Maßnahmen ohne Projekt, fehlende Geometrie), erledigt ein
  Skill über die vorhandenen MCP-Tools plus ein neues Lese-Tool.

---

## Aufbau des Dokuments (Infraplan 2026)

160 Seiten: 77 Seiten Hauptteil, 83 Seiten Anhang. Relevant ist Kapitel 2.3
(S. 32–56):

| Abschnitt | Kennung | Zeilen | Realisierungsstand | Kostenspalte |
|---|---|---|---|---|
| Bedarfsplan, Teil A – im Bau und/oder mit durchgängigem Baurecht (Lph 4–9) | `BP_A` | 38 | `Bau` · `Lph 4 abgeschlossen – durchgängiges Baurecht vorliegend` | GWU in Mio. € |
| Bedarfsplan, Teil B – Entwurfs- und Genehmigungsplanung (Lph 3–4) | `BP_B` | 40 | `Lph 3-4` | GWU |
| Bedarfsplan, Teil C – Vorplanung (Lph 1–2) | `BP_C` | 69 | `Lph 1` · `Lph 1-2` | GWU |
| Bedarfsplan, Teil D – Grundlagenermittlung (noch keine Lph) | `BP_D` | 71 | leer | GWU |
| GVFG, Kat. A – endgültig ins Bundesprogramm aufgenommene DB-Vorhaben | `GVFG_A` | 35 | `Lph 5 - 9`, `Lph 3 - 4`, `offen`, … | Gesamtkosten in Mio. € |
| GVFG, Kat. C – bedingt aufgenommene DB-Vorhaben | `GVFG_C` | 42 | wie Kat. A | Gesamtkosten |
| InvKG – Maßnahmen im Bau | `INVKG` | 5 | `Bau` | GWU |

**Spalten Bedarfsplan:** `Laufende Nummer | Projektnummer` · `Bezeichnung` ·
`Maßnahme` · `Land` · `Realisierungsstand / Lph` · `Geplante Inbetriebnahme` ·
`GWU in Mio. €` · `Parlamentarische Befassung`.
**GVFG/InvKG:** ohne `Bezeichnung` und ohne `Parlamentarische Befassung`; GVFG
heißt die Terminspalte „Geplante oder tatsächliche Inbetriebnahme“.

Beispielzeile (Teil A, S. 34):

```
20 | E.1637290101 · PB 03: ABS Magdeburg – Stendal – Uelzen (Ostkorridor Nord)
   · 2gl. Einbindung Bf Stendal und Ausbau Str. bis Hohenwulsch und Salzwedel – Uelzen
   · Niedersachsen/Sachsen-Anhalt · Bau · 2030 · 1.720,48¹⁴ · nicht vereinbart
```

### Besonderheiten, die der Parser abdecken muss

| Fall | Beispiel | Behandlung |
|---|---|---|
| Mehrere Projektnummern | `E.1637230040 // X.016030472300201` | Liste; erste = Hauptnummer |
| Projektnummer-Formate | `E.16…` (DB InfraGO), `T.016…`/`G.016…`/`X.016…`, GVFG `07 D 2825_A`, InvKG `6)` bzw. „InvKG Nr. 6“ | als Rohtext speichern, nur `E.`- und GVFG-Nummern als Wiedererkennungs-Schlüssel |
| Hochgestellte Fußnoten kleben an Werten | `1.720,48` + ¹⁴ → Text `1.720,4814` | Wörter mit kleinerer Schriftgröße als die Zeile **vor** dem Zusammensetzen abtrennen → `footnote_refs` |
| Kostenverweis statt Zahl | `Ref. Teil B 20 \| E.1637290100` | `cost_mio = NULL`, `cost_ref` speichern und nach dem Parse auf den Zieleintrag auflösen |
| Sammel-GWU per Fußnote | Fn. 14: „GWU 1.720,48 Mio. € bezieht sich auf Teil A 20 und Teil A 33“ | Fußnotentext am Eintrag speichern; im Review anzeigen, nicht interpretieren |
| Inbetriebnahme nicht als Jahr | `offen`, `bis 2035`, `2029/2030`, `2023/2024`, `2022–2029` | `ibn_raw` + `ibn_year` (späteres Jahr) + `ibn_qualifier` (`OFFEN`/`BIS`/`SPANNE`) |
| GVFG-Termin in der Vergangenheit | `2019` (Restarbeiten laut Fn. 23) | speichern, **nicht** als Inbetriebnahme materialisieren |
| Silbentrennung über Zeilen | `Lehr- ter Stamm- bahn` | Trennstrich am Zeilenende entfernen |
| Seite ohne erkannte Kopfzeile | Teil D und GVFG Kat. A ab Folgeseite | Spaltengrenzen der letzten Kopfzeile desselben Abschnitts übernehmen |
| Fußnotenbereich am Seitenende | Fn. 12–14 unter der Tabelle | Bereich ab der ersten kleinen Fußnotenziffer am linken Rand abschneiden; Fußnotentexte separat einlesen |

**Plausibilitätsprüfung:** Die laufende Nummer ist je Abschnitt lückenlos `1..n`.
Der Parser meldet Lücken und Dubletten im Ergebnis (`warnings`). Das ist die
wichtigste Absicherung gegen Layoutänderungen in späteren Jahrgängen; im Prototyp
deckte sie die Fehler bei Teil D und GVFG Kat. A sofort auf.

---

## Pipeline

| Stufe | Was passiert | Wo (neu) |
|---|---|---|
| 1 Textgewinnung | pdfplumber, Wörter **mit Schriftgröße** (`extra_attrs=["size"]`); Spaltengrenzen aus der Kopfzeile (`find_tables()[0]`) | `tasks/infraplan.py` |
| 2 Segmentierung | Abschnitte über die Überschriften `Bedarfsplan, Teil A–D`, `GVFG, Kat. A/C`, `InvKG` erkennen; Zeilen an der laufenden Nummer in Spalte 1 trennen; Fußnotenzone abschneiden | `tasks/infraplan.py` |
| 3 Semantik | Kopfzeile → kanonisches Schema (deterministisch über Spaltentitel, Muster `haushalt_columns`); Werte normalisieren (Zahlen deutsch, Jahr, Lph, Befassung) | `tasks/infraplan_columns.py` |
| 4 Matching | Vorschläge je Zeile, siehe [Zuordnung](#zuordnung-zu-projekten) | `tasks/infraplan_matching.py` |

Ausführung als Celery-Task `parse_infraplan_pdf`, Status über das generische
`GET /tasks/{task_id}`. Ergebnis als Entwurf (`InfraplanParseResult.result_json`),
dann Prüfung im Review, dann Übernahme — wie beim Haushalt. OCR ist nicht nötig; fehlt
einem künftigen Jahrgang der Textlayer, kann die gemeinsame Stufe
`services/document_ocr.py` nachgerüstet werden.

---

## Datenmodell

Neue Tabellen (Migration via `make migrate-create`, rein additiv):

**`infraplan_parse_result`** — Entwurf je Upload (Muster `haushalts_parse_result`)
- `id`, `year` (Jahrgang, z. B. 2026), `status`, `result_json`, `warnings_json`,
  `error_message`, `file_name`, `created_at`, `confirmed_at`, `confirmed_by_snapshot`

**`infraplan_report`** — bestätigter Jahrgang
- `id`, `year` (unique), `title`, `published_on` (Date), `parse_result_id`, `created_at`

**`infraplan_entry`** — eine Tabellenzeile
- `report_id` (FK, CASCADE), `section` (`BP_A` … `INVKG`), `lfd_nr`, `page`
- `project_numbers` (JSON-Liste), `primary_number` (String, indiziert)
- `bezeichnung`, `massnahme`, `laender` (Rohtext)
- `state_raw`, `lph_from`, `lph_to` (Int, nullable), `under_construction` (Bool), `baurecht` (Bool)
- `ibn_raw`, `ibn_year` (Int, nullable), `ibn_qualifier`
- `cost_mio` (Numeric(12,2), nullable), `cost_kind` (`GWU` | `GESAMTKOSTEN`),
  `cost_ref_raw`, `cost_ref_entry_id` (FK self, nullable)
- `parl_raw`, `parl_state` (`ABGESCHLOSSEN` | `LAEUFT` | `VORGESEHEN` | `NICHT_VEREINBART` | NULL)
- `footnote_refs` (JSON), `footnotes` (JSON: `{nr: text}`)
- Unique `(report_id, section, lfd_nr)`

**`infraplan_entry_project`** — m:n-Zuordnung (Muster `vib_entry_project`)
- `entry_id`, `project_id`, `assigned_by_snapshot`, `created_at`

**`progress_observation`** — neue nullable Spalte `infraplan_entry_id` (FK, SET NULL)
als Herkunft. `SourceType` bekommt `INFRAPLAN`; `source_type` ist ein einfacher
String, also ohne Enum-Migration (wie bei `BAUPORTAL`/`FULDA_RUNDE`).

Eine eigene Projektnummer-Spalte am `Project` gibt es **nicht**: Die Wiedererkennung
im Folgejahr läuft über die bestätigten Zuordnungen (`primary_number` → Projekt), siehe
unten. Damit braucht es kein Pflegefeld, das ohnehin nur der Import befüllen würde.

---

## Zuordnung zu Projekten

Reihenfolge je Zeile:

1. **Projektnummer aus früheren Jahrgängen** — gibt es eine bestätigte Zuordnung für
   dieselbe `primary_number` (`E.…` oder GVFG-Nummer), wird sie mit Konfidenz 1.0
   vorgeschlagen. Ab dem Infraplan 2027 ist so der Großteil automatisch zugeordnet.
2. **Fuzzy-Matching** über `Bezeichnung + Maßnahme` mit den bestehenden Funktionen
   aus `tasks/vib_matching.py` (VDE-Nummer, `_score`, Schwelle 0.5). Präfixe wie
   `PB 07:` werden vorher entfernt.
3. **Kein Treffer** → Zeile bleibt unzugeordnet und erscheint in `/admin/unassigned`
   (neue Sektion „Infraplan“), mit „Projektentwurf anlegen“ wie beim VIB.

Mehrere Zeilen können auf dasselbe Projekt zeigen (Teil A 20 und Teil A 33 gehören zu
einem Vorhaben), eine Zeile kann mehreren Projekten zugeordnet werden (m:n).

---

## Übernahme in den Projektfortschritt

Neue Mapper-Funktion `infraplan_entry_to_specs` in
`services/progress_materialization.py`; die Rows sind `is_derived=True` und werden
über `sync_derived_observations` idempotent neu erzeugt. Default-Vertrauen
`INFRAPLAN = 0.8` in `SOURCE_TYPE_DEFAULT_TRUST` (amtliche Angabe des Bundes,
Stichtag aktuell; gleichauf mit Bauportal). `observed_date` = Veröffentlichungsdatum
des Jahrgangs.

**Track MAIN** (Untergrenze der Hauptphase):

| Realisierungsstand | MainPhase |
|---|---|
| `Bau` (BP_A, InvKG) | `BAU` |
| `Lph 4 abgeschlossen – durchgängiges Baurecht` | `GENEHMIGUNGSPLANUNG` + Track PF `ABGESCHLOSSEN` |
| `Lph 3-4` | `GENEHMIGUNGSPLANUNG` |
| `Lph 1`, `Lph 1-2` | `VORPLANUNG` |
| BP_D (keine Lph) | `NICHT_GESTARTET` |
| GVFG `Lph 5 - 9`, `Lph 5 - 7`, `Lph 5` | `BAU` (Konfidenz 0.6, Angaben der Länder, laut Fn. 23 unplausibilisiert) |
| GVFG `Lph 3 - 4`, `Lph 4` | `GENEHMIGUNGSPLANUNG` (0.6) |
| GVFG `Lph 1 - 2` | `VORPLANUNG` (0.6) |
| GVFG `Lph 1 - 4`, `Lph 1 - 9`, `offen` | keine Observation |

**Track PARL** (nur Bedarfsplan):

| Befassung | ParallelState |
|---|---|
| `abgeschlossen – Entschließung BT liegt vor` | `ABGESCHLOSSEN` |
| `Übergabe seitens DB InfraGO AG erfolgt – Verfahren läuft` | `LAEUFT` |
| `vorgesehen` | `OFFEN` |
| `nicht vereinbart` | keine Observation |

**Prognose:** `concrete_milestone_dates` (`services/progress_forecast.py`) bekommt einen
weiteren Eingang `infraplan: list[(MainPhase.IN_BETRIEB, date)]` mit Quelle
`"Infraplan"`. Datum = 31.12. des `ibn_year`, Anzeige nur als Jahr. Rangfolge: VIB-PFA
< Fulda-Runde < **Infraplan** < Manuell — der Infraplan ist jünger und amtlicher als der
VIB, manuelle Angaben gewinnen weiter. Bei `ibn_qualifier = OFFEN` oder einem Jahr vor
dem Jahrgang (GVFG-Altfälle) entfällt der Eingang. Mehrere Einträge je Projekt → spätestes
Jahr (letzter Abschnitt geht in Betrieb).

---

## Anzeige

**Projektdetail, neuer Abschnitt „Infraplan“** (nur wenn Einträge zugeordnet sind):
eine Zeile je Jahrgang und Eintrag mit Abschnitt, Realisierungsstand, geplanter
Inbetriebnahme, Kosten und Befassung; Fußnoten als Tooltip. Ab dem zweiten Jahrgang:
Delta-Spalten („GWU +12 %“, „IBN 2028 → 2030“). Kostenverweise zeigen auf den
Eintrag, der den Wert trägt. Mobil über `ResponsiveTable`.

**Projektliste:** optionale Spalte „geplante IBN (Infraplan)“ — erst in einer späteren
Stufe, wenn sich der Bedarf zeigt.

---

## API

Prefix `/import/infraplan`, Recht `infraplan.import` (neu, `GROUP_FINANCING`, in
`_EDITOR_PERMISSIONS`):

| Methode | Pfad | Zweck |
|---|---|---|
| POST | `/parse` | PDF hochladen, Task starten (`year` als Formularfeld) |
| GET | `/parse-result`, `/parse-result/{id}` | Entwürfe listen / laden |
| DELETE | `/parse-result/{id}` | Entwurf verwerfen |
| PATCH | `/parse-result/{id}/rows/{row}` | Zuordnung/Werte einer Zeile im Entwurf ändern |
| POST | `/confirm` | Entwurf übernehmen; 409, wenn der Jahrgang schon existiert |
| DELETE | `/report/{year}` | Jahrgang löschen (für Neuimport) |

Lesend (öffentlich wie die übrigen Projektdaten):
`GET /projects/{id}/infraplan` → Einträge aller Jahrgänge mit Deltas.

Admin: `GET /admin/unassigned-infraplan-entries`,
`PATCH /admin/unassigned-infraplan-entries/{id}/assign` (Recht `assignment.manage`).

---

## Frontend

`src/features/infraplan-import/`: `InfraplanImportPage` (Upload + Entwurfsliste),
`InfraplanReviewPage` (Tabelle je Abschnitt, Warnungen oben, Zuordnungs-MultiSelect,
Filter „ohne Zuordnung“), Anleitung als Guide in `guides/guideContent.ts`
(Slug `infraplan`). Routen `admin/infraplan-import`, `…/review/:parseResultId`.
Sektion in `features/admin/UnassignedPage.tsx`. Projektdetail-Abschnitt in
`features/projects/`. Hooks in `shared/api/queries.ts`, danach `make gen-api`.
In-App-Doku (`documentationData.ts`) um den Import ergänzen.

---

## MCP & Skill (Nacharbeit)

- Neues Lese-Tool `get_project_infraplan(project_id)` in `mcp/tools/projects.py`
  (gleiche Daten wie der Endpoint).
- `list_data_gaps` bekommt die Lücke `infraplan_unassigned` (Einträge des neuesten
  Jahrgangs ohne Projekt).
- Zuordnen bleibt außerhalb des MCP (Importe sind ausgeklammert) **oder** bekommt ein
  schreibendes Tool `assign_infraplan_entry` — **offene Entscheidung**, siehe unten.
- Skill `infraplan-nacharbeit` (Repo, `.claude/skills/`): Lücken holen → je Eintrag
  Projekt suchen oder als Entwurf anlegen → Geometrie mit `route_project_geometry`
  routen → zuordnen.

---

## Tests

- Fixture `tests/fixtures/infraplan_2026_pages.json`: Wortlisten (Text, Position,
  Schriftgröße) der Seiten 33–56, erzeugt per Skript aus dem PDF — das PDF selbst
  liegt außerhalb des Docker-Kontexts `apps/backend` (Muster
  `haushalt_ep12_2027_pages.json`).
- Parser: Zeilenzahl je Abschnitt (38/40/69/71/35/42/5), lückenlose laufende
  Nummern, Fußnote abgetrennt (`1.720,48` + `[14]`), Kostenverweis erkannt,
  `bis 2035` → (2035, `BIS`).
- Mapper: Tabellen oben als parametrisierte Unit-Tests.
- Confirm: zweiter Confirm desselben Jahrgangs → 409; erneute Materialisierung erzeugt
  keine Dubletten.
- Matching: bestätigte Zuordnung aus Jahrgang N wird in N+1 über die Projektnummer
  vorgeschlagen.

---

## Ausbaustufen

| Stufe | Inhalt | Issue-Code |
|---|---|---|
| 1 | Parser + Datenmodell + Entwurf (Backend) | Infraplan – Stufe 1 |
| 2 | Review-UI, Übernahme, Matching, Offene Zuordnungen | Infraplan – Stufe 2 |
| 3 | Fortschritt/Prognose (`INFRAPLAN`), Projektdetail mit Kosten-/Terminverlauf | Infraplan – Stufe 3 |
| 4 | MCP-Lese-Tool, Datenlücke, Skill Nacharbeit | Infraplan – Stufe 4 |
| später | Kennzahl-Maßnahmenlisten im Anhang (Elektrifizierung, Lärmsanierung, KMM, Bahnhöfe, ETCS; nur Name + Jahr, ohne Nummer) und die acht Steuerungskennzahlen (Soll/Ist je Jahr) als eigene Übersicht | — |

---

## Offene Entscheidungen

1. **`nicht vereinbart` bei der Befassung** — keine PARL-Observation (Vorschlag) oder
   `parl_relevant = false` setzen? Der Vorschlag ändert nichts an Projekten, die der
   Nutzer bereits als parlamentsrelevant markiert hat.
2. **Schreibendes MCP-Tool zum Zuordnen** — ja/nein (siehe oben).
3. **PDF im Repo** — `docs/261002_Infraplan_2026_1.pdf` (4,4 MB) bleibt als Quelle
   liegen oder wird nach Erzeugen der Fixture entfernt.

## Akzeptanzkriterien (gesamt)

- [ ] Upload des Infraplans 2026 liefert 300 Zeilen (38+40+69+71+35+42+5) ohne
      Lücken-Warnung.
- [ ] Nach Bestätigung zeigt z. B. „ABS Magdeburg – Stendal – Uelzen“ im Projektdetail
      Teil A, Bau, IBN 2030, GWU 1.720,48 Mio. € mit Fußnote.
- [ ] Der Fortschritt dieses Projekts enthält eine `INFRAPLAN`-Observation `BAU`; die
      Prognose nennt Inbetriebnahme 2030 mit Quelle „Infraplan“.
- [ ] Unzugeordnete Einträge erscheinen unter `/admin/unassigned` und lassen sich dort
      zuordnen.
- [ ] Ein zweiter Import desselben Jahrgangs wird abgewiesen; nach Löschen des
      Jahrgangs funktioniert er wieder, ohne doppelte Observations.
- [ ] Die Ansicht funktioniert bei 360 px Breite.
