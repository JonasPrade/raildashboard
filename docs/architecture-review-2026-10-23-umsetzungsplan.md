# Umsetzungsplan zur Architekturanalyse vom 2026-10-23

Dieser Plan überführt alle Vorschläge aus `architecture-review-2026-10-23.md` (Abschnitt 6) in Arbeitspakete. Jedes Paket ist ein GitHub-Issue nach `docs/github-projects.md` (Aufgabe, Akzeptanzkriterien, Konzept-Verweis, Abhängigkeiten, Labels `area:`/`type:`). Die Priorität steht als Label `prio:hoch`, `prio:mittel`, `prio:niedrig` am Issue; die Stufe (Sofort, Kurzfristig, Mittelfristig, Langfristig) im Issue-Text. Milestones sind nicht gesetzt, die Versionszuordnung trifft der User. Erstellt am 2026-10-30.

Was damit angestoßen ist:
- Die Sofortmaßnahmen (#295) laufen in einer eigenen Claude-Code-Session (Modell Opus 5.5) auf Branch `fix/295-sofortmassnahmen-sicherheit`; Ergebnis ist ein PR gegen `master` mit `Closes #295`, danach Status `Needs User Test` mit Test-Checkliste.
- Alle übrigen 33 Pakete liegen als Issues #296 bis #328 vor. Die Board-Spalte `Stage` konnte aus der Cloud-Session nicht gesetzt werden (GraphQL gesperrt); die Issues müssen auf dem Board einmal auf `Backlog` bzw. `Ready` gezogen werden.

## 1. Reihenfolge und Abhängigkeiten

```
Stufe 1 Sofort          #295 ──────────────┐
                                           ├─▶ #308 Service-Schicht ──▶ (Parität REST/MCP)
Stufe 2 Kurzfristig     #301 Regeln→CRUD ──┘
                        #297 Haushalt-Links ──▶ #299 Confirm liest Server ◀── #296 VIB-CRUD
                        #298, #300, #303, #304 (unabhängig)
                        #305 Test-Setup ──▶ #328 Testabdeckung
                        #306 Migrations-Lint ──▶ #325 Rollback-Vertrag
                        #302 Postgres-CI ──▶ #323, #324, #325, #327
                        #307 Restore-Test (User)
Stufe 3 Mittelfristig   #309 Teilbaum-Helper ──▶ #310 Aggregation, #316 Planungsstand-Folgen
                        #311 Import-Baukasten ──▶ #312 Modulschnitt ──▶ #326 Jahrgangs-Hacks
                        #295 ──▶ #314 Session-Härtung, #318 Import-Robustheit
                        #313, #315, #317, #319, #320, #321 (unabhängig)
Stufe 4 Langfristig     #322 Blobs, #323 Schema, #324 PostGIS, #325, #326, #327, #328
```

Entscheidungen, die der User vor der Umsetzung treffen muss (als Konzept-Lücken in den Issues markiert):
- #265 / #309: Zählen Entwürfe in der Eltern-Aggregation?
- #310: Folgt die Kosten-Headline „neuere Quelle gewinnt“ (Entscheidung 22) oder „Infraplan führt“ (GVFG-Doku)?
- #314: Bleiben `user.manage` und `role.manage` de facto Super-Admin (dokumentieren) oder werden Admin-Anlage und Admin-Passwort auf Admins beschränkt?
- #326: Welche Einmalskripte sind in Produktion bereits gelaufen und können entfernt werden?

## 2. Stufe Sofort (prio:hoch, läuft in eigener Session)

| Issue | Paket | Inhalt |
|---|---|---|
| #295 | Sofortmaßnahmen Sicherheit und Betrieb | Capability an `POST /projects/{id}/routes`; Principal mit effektiven Rechten statt `has_permission`; Nutzernamen nicht mehr auf öffentlichen GETs; SSRF-Schutz im Medien-Importer; `cancel-in-progress: false`; Celery `acks_late`/Zeitlimits; README-Tag-Deploy-Abschnitt löschen |

## 3. Stufe Kurzfristig (prio:hoch, 1 bis 2 Wochen)

| Issue | Bereich | Paket | Abhängigkeit |
|---|---|---|---|
| #296 | vib-import | VIB-REST auf `vib_agent`-CRUD, Neuberechnung, `confirmed`-Semantik, Waisen | keine |
| #297 | haushalt-import | Haushalt-Confirm über `change_finve_links` (Changelog, Archiv, Neuberechnung) | keine |
| #298 | projects | `delete_project` kaskadiert; Sammel-FinVe-Phasen berechnen neu | keine |
| #299 | haushalt-import | Haushalt-/VIB-Confirm lesen das gespeicherte Parse-Ergebnis; VIB-Draft behalten | #297, #296 |
| #300 | progress | PFA-Leaf-Termine in Prognose und Listen-Cache; Archiv-Filter bei PFAs | keine |
| #301 | projects | Geschäftsregeln aus MCP in CRUD/Schemas | keine |
| #302 | tests | Postgres/PostGIS-Stufe in CI, `alembic check`, Zero-Drift-Migration | keine (löst #31) |
| #303 | projects (UI) | Cache-Invalidierung nach Mutationen vervollständigen | keine |
| #304 | auth (UI) | `ApiError` als Error, 401-Behandlung, App ohne Warten rendern | keine |
| #305 | tests | Test-Setup: ENVIRONMENT, SQLite-FKs, tote Suite, Leerdatei | keine |
| #306 | ops | Migrations-Lint mit Freigabemarker, Rollback-Grenze in DEPLOY.md | keine |
| #307 | ops (human-task) | Restore-Kommando auf dem Server verifizieren | keine |

## 4. Stufe Mittelfristig (prio:mittel, 1 bis 2 Monate)

| Issue | Bereich | Paket | Abhängigkeit |
|---|---|---|---|
| #308 | projects | Service-Schicht für Projektoperationen, MCP-Modulschnitt, SQL-Zwillinge mit Äquivalenztest | #295, #301 |
| #309 | projects | Ein Teilbaum-Helper `services/hierarchy.py`, Entwurfs-Entscheidung (#265) | Entscheidung User |
| #310 | finve | Aggregation als Backend-Vertrag (GVFG Teilbaum, Länge, Kosten-Headline) | #309, Entscheidung User |
| #311 | haushalt-import | Import-Baukasten: Matcher, Task-Basis, Upload-Validierung, Fehlercodes, Progress-Meta | keine |
| #312 | projects | Schichtinversion crud→tasks auflösen, Parser nach `services/pdf`, große Module teilen, toter Code | #311 |
| #313 | progress | Datumspräzision vervollständigen (PFB/Parl./Lebenszyklus, Sortierwerte, Infraplan „bis“) | keine |
| #314 | auth | Session-Härtung, Rate-Limit, `/healthz` nach außen, Vertrauensgrenze, nginx-Header, Redis-Passwort | #295 |
| #315 | docs | Dokumentation konsolidieren (Steuerdateien, Deploy-Docs, Roadmap-Tooling, Ports, Widersprüche) | keine |
| #316 | progress | Infraplan/GVFG-Rivalität je Projekt, Merge-Guard, `recompute_all`, Doppelarbeit, Lph-9, `list_finves` | #309 |
| #317 | projects | Listen-Endpunkte ohne `geojson_representation` | keine |
| #318 | vib-import | Import-Robustheit: `report_date`, LLM-Client, Haushalt-Re-Import, Infraplan-Confirm per MCP, Draft-Persistenz | #295 |
| #319 | ops | GraphHopper ohne URL, `/healthz`-Umfang, Migrations-Gate, `make test` hostunabhängig, nginx-Resolver, Makefile | keine |
| #320 | projects (UI) | Feld `aliases`, Rechte-Gating, Filter in URL, atomares Speichern | keine |
| #321 | design (UI) | ESLint-Regeln, Breakpoint, `window.confirm`, Gelb/Orange, tsconfig, `as any`, tote Hooks | keine |

## 5. Stufe Langfristig (prio:niedrig)

| Issue | Bereich | Paket | Abhängigkeit |
|---|---|---|---|
| #322 | vib-import | OCR-Bilder und Blobs auf das Upload-Volume, `deferred()` | keine (verwandt #23) |
| #323 | ops | Schema-Hygiene: TimestampMixin, `project_text`, `now_utc`, Indizes, `finve.id`, nullable FKs | #302 (löst #16) |
| #324 | routing | Projektgeometrie als PostGIS-Spalte | #302 |
| #325 | ops | Rollback-Vertrag zweistufig, älteste sichere SHA | #306, #302 |
| #326 | infraplan-import | Jahrgangs-Hacks konfigurierbar, Einmalskripte und Legacy-Import entfernen | #312, Auskunft User |
| #327 | ops | Abhängigkeiten mit Major-Sprung heben | #302 |
| #328 | tests | Testabdeckung: Factories, Frontend-Features, MCP-Rechte, Skill-Toolnamen, Längen-Parität | #305 (verwandt #13) |

## 6. Bestehende Issues, die davon berührt sind

| Issue | Bezug |
|---|---|
| #31 CI: Tests in GitHub Actions | #302 löst den Postgres-Anteil; danach schließen oder auf Coverage-Artifact reduzieren |
| #16 Datenbankstruktur aufräumen | #323 liefert die konkreten Schritte; danach schließen |
| #265 Entwürfe aus Eltern-Aggregation ausnehmen? | Entscheidung wird in #309 umgesetzt |
| #243 bis #248 Datumsqualifikation | #313 schließt die verbliebenen Lücken |
| #23 VIB-Review: OCR-Bilder anzeigen | #322 ändert den Speicherort |
| #13 Parser-Fixture-Tests | #328 ergänzt |
| #30 Matching aus manuellen Zuordnungen lernen | profitiert vom einen Matcher aus #311 |
| #48 Medien-Importer | #295 schließt die SSRF-Lücke |

Auffällig: viele offene Issues sind laut Code längst umgesetzt (#138, #139, #130 bis #134, #179 bis #184, #198, #264, #261, #268). Das Board bildet den Stand nicht ab; ein Aufräumen gehört in #315.

## 7. Arbeitsweise je Paket

1. Issue auf dem Board auf `In Progress`, Branch `feat/<nr>-…` bzw. `fix/<nr>-…` von `master`.
2. Umsetzung mit Tests; `make test` vor dem Push (Docker), sonst mindestens `pytest` im venv und `tsc`/`lint`/`vitest`.
3. PR mit `Closes #<nr>`; Auto-Merge nach grüner CI (CLAUDE.md), außer bei `Needs User Test`.
4. Verhaltens- oder UI-Änderung: Test-Checkliste als Issue-Kommentar, Status `Needs User Test`.
5. CHANGELOG unter `[Unreleased]`; bei Deploy-relevanten Änderungen DEPLOY.md und `docs/production_setup.md`.
6. Freigeschaltete Folge-Issues auf `Ready`.

Empfohlene Reihenfolge für die nächsten Sessions nach #295: #297 → #299 → #296 (Import-Integrität), parallel #303 und #304 (Frontend), dann #302 (Postgres-CI) vor allen Schema-Themen, dann #301 → #308.
