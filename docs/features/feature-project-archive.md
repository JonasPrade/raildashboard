# Feature: Projekte archivieren

**Status: in Umsetzung (2026-10-23)** — Issue #264. Folge-Issue #265 („Entwürfe aus
Eltern-Aggregation ausnehmen?").

## Ziel

Ein Projekt, das durch andere Projekte **ersetzt** oder **überholt** wurde, soll aus
allen Listen, Karten und Summen verschwinden, ohne gelöscht zu werden: Es behält seine
eigene Historie (VIB-Jahrgänge, Infraplan-Zeilen, Änderungsprotokoll, Geometrie) und
bleibt per URL erreichbar. Dafür bekommt das Projekt ein eigenes Kennzeichen
**Archiviert** mit Pflicht-Begründung.

Anlass: Beim Einlesen des VIB 2024 wurden die alten Teilmaßnahmen von ABS/NBS
Hamburg–Lübeck–Puttgarden (Projekt 1461) durch PFA-Abschnitts-Teilprojekte ersetzt.
Die alten (1716, 1717, 1718, 1719, 1720, 1722, 1691, 1693) wurden behelfsweise auf
Entwurf gesetzt und ihre Geometrie geleert, weil Entwürfe in die Elternkarte
einfließen. Sie tauchen dadurch fälschlich unter `/admin/drafts` auf.

## Entscheidungen (Widerspruchs-Check 2026-10-23, vom Nutzer entschieden)

| # | Widerspruch | Entscheidung |
|---|---|---|
| W1 | `docs/architecture.md` → „Parent projects always aggregate" | Grundsatz ergänzt: **Ein archiviertes Projekt ist kein Teilprojekt** — es zählt nirgends (Summen, Geometrie-Aggregation, Stand-Spanne, Kinderlisten, `is_superior`). |
| W2 | Entwürfe fließen heute in die Eltern-Aggregation ein | Nur **archivierte** Projekte werden aus der Aggregation genommen; Entwürfe bleiben wie heute. Eigenes Folge-Issue #265 „Entwürfe aus Eltern-Aggregation ausnehmen?". |
| W3 | `feature-project-merge.md` lehnt ein filter-überall-„Geister-Projekt" ab | Archivieren ist eine **bewusst dokumentierte Ausnahme**: Zusammenführen bleibt für Dubletten (ein Projekt geht im anderen auf); Archivieren ist für ersetzte/überholte Projekte, die ihre eigene Historie behalten. Beide Docs verweisen aufeinander. |
| W4 | `lifecycle_status` (AKTIV/PAUSIERT/ABGEBROCHEN) hängt am `project_progress` | Eigenes Kennzeichen **am Projekt** (`is_archived`), nicht im Lebenszyklus. Ein real **abgebrochenes** Projekt (ABGEBROCHEN) wird **nie** archiviert, es bleibt sichtbar. UI-Wort „Archiviert", nicht „Status" (das Wort ist für den Lebenszyklus belegt). |
| W5 | Summen aus FinVe/GVFG würden beim Elternprojekt fehlen | Archivieren wird **abgelehnt**, solange FinVe- oder GVFG-Zuordnungen am Projekt hängen; die Fehlermeldung nennt die Verknüpfungen (erst umhängen). |
| W6 | Berechtigung | Wie Löschen: `project.delete`. |

### Folgeentscheidungen (bei der Umsetzung getroffen, 2026-10-23)

| # | Frage | Entscheidung | Begründung |
|---|---|---|---|
| F1 | Weitere Quellen mit Summen (W5 prüfen) | **Haushalt** hängt an der FinVe → durch W5 abgedeckt. **VIB-Vorhaben, VIB-PFA-Zeilen, Infraplan-Zeilen, Fulda-Ankündigungen, Bauportal, Medien** bleiben **erlaubt**: Sie sind die Historie des ersetzten Projekts (genau die will man behalten). Die Antwort beim Archivieren nennt sie als `kept_links` (Hinweis, kein Fehler). | Sie zählen beim Elternprojekt ohnehin nicht mehr, weil `subtree_ids` archivierte Projekte auslässt (Infraplan-Kostenprognose aus Teilprojekten). Ein Block würde genau den Anlassfall (Puttgarden, VIB-Historie) verhindern. |
| F2 | Projekt mit Teilprojekten archivieren | **Abgelehnt**, solange es nicht archivierte Teilprojekte hat (Meldung nennt sie: erst umhängen oder zuerst archivieren). | Sonst hingen aktive Projekte unter einem Projekt, das nirgends zählt. |
| F3 | Archiviertes Projekt als übergeordnetes Projekt wählen | **Abgelehnt** (`validate_superior_project`), Picker zeigen archivierte ohnehin nicht. | Ein neues Kind würde unsichtbar. |
| F4 | Entwurf + Archiv | Unabhängige Kennzeichen. Archivieren ändert `is_draft` nicht; die Entwurfsliste blendet archivierte Projekte aus. | Keine versteckte Nebenwirkung; nach dem Wiederherstellen ist ein Entwurf wieder ein Entwurf. |
| F5 | Geometrie des archivierten Projekts | Bleibt am Projekt (Historie, Detailseite), fließt aber nicht mehr in die Elternkarte. | Kein Leeren mehr nötig. |
| F6 | Änderungsprotokoll | Ein Eintrag `action="ARCHIVE"` bzw. `"UNARCHIVE"` mit `is_archived`, `archived_reason` (beim Wiederherstellen: Begründung, falls angegeben, sonst die alte bleibt im Protokoll). REST und MCP gleich. Nicht per „Zurücksetzen" umkehrbar — dafür gibt es „Wiederherstellen". | Die Lücke von `finalize` (protokolliert nicht) wird nicht kopiert. |
| F7 | Ablehnungen am Archiv-Projekt selbst | Ein bereits archiviertes Projekt erneut zu archivieren bzw. ein nicht archiviertes wiederherzustellen ist ein 400/ToolError. | Eindeutige Protokolleinträge. |
| F8 | Liste archivierter Projekte | `GET /projects/archived` mit `project.delete` (wie die Aktionen). | Die Seite ist eine Admin-Seite. |
| F9 | Wiederherstellen unter archiviertem Elternprojekt | **Abgelehnt** — erst das Elternprojekt wiederherstellen oder umhängen. | Folgt aus F2/F3: unter einem archivierten Projekt hängt nichts Aktives. |
| F10 | Matching-Kandidaten | Archivierte Projekte sind in keinem Import Kandidat (Haushalt, VIB inkl. PFA-Teilbaum, Infraplan, GVFG, Fulda, Bauportal, Medien). Bereits bestehende Zuordnungen bleiben. | Ersetzte Projekte sollen keine neuen Daten mehr anziehen. |

## Datenmodell

`project` (Expand-only-Migration `20261023001_project_archive`):

| Spalte | Typ | Bedeutung |
|---|---|---|
| `is_archived` | Boolean NOT NULL, `server_default false` | Archiviert |
| `archived_reason` | Text, NULL | Pflicht-Begründung (beim Archivieren nicht leer) |
| `archived_at` | DateTime, NULL | Zeitpunkt des Archivierens |

Wiederherstellen setzt `is_archived = false`, `archived_at = NULL`; `archived_reason`
wird geleert (die Begründung steht im Änderungsprotokoll).

## Wirkung

Archivierte Projekte fehlen überall dort, wo Entwürfe heute fehlen:

- Projektliste und Karte (`GET /projects/`), Projektgruppen (Liste, Geometrien),
  Picker (`GET /projects/options`), Teilprojekte (`GET /projects/{id}/subprojects`),
  Zeitleiste der Gruppen, Parlaments-Listen (Abgeordnete/Wahlkreise),
- MCP `list_projects`, `list_project_groups` (Anzahl), `list_data_gaps`,
  `check_project_data`, `get_project` (Teilprojekte),
- Kandidaten der Import-Zuordnung (Haushalt, VIB, Infraplan, GVFG, Fulda, Bauportal, Medien).

Zusätzlich (anders als Entwürfe, W1/W2):

- **Geometrie-Aggregation** (`recompute_geojson_for_parent`) und `has_subprojects`,
- **Stand-Aggregation** (`_load_subtree`, `is_superior`) und `list_progress_conflicts`,
- **Summen über Teilprojekte** (`subtree_ids`: FinVe-, Infraplan-Übersicht; GVFG-Förderung in Teilprojekten),
- **Entwurfsliste** (`GET /projects/drafts`, Badge in der Admin-Übersicht).

Archivieren und Wiederherstellen berechnen die Geometrie und den Stand des
Elternprojekts (und seiner Vorfahren) neu.

`GET /projects/{id}` liefert archivierte Projekte weiter; die Detailseite zeigt ein
Hinweis-Banner „Archiviert" mit Begründung und Datum.

## Schnittstellen

- `POST /api/v1/projects/{id}/archive` `{reason}` → `ProjectArchiveResult`
  (`project`, `kept_links`) — `project.delete`; 400 mit Liste der Verknüpfungen bei
  FinVe/GVFG/Teilprojekten/ABGEBROCHEN.
- `POST /api/v1/projects/{id}/unarchive` `{reason?}` → `ProjectSchema` — `project.delete`.
- `GET /api/v1/projects/archived` → `ArchivedProjectSchema[]` (Name, Begründung, Datum,
  Elternprojekt) — `project.delete`.
- MCP `archive_project(project_id, reason)`, `unarchive_project(project_id, reason=None)`
  (gleiche Regeln, Recht `project.delete`, im Änderungsprotokoll).
- `ProjectSchema` trägt `is_archived`, `archived_reason`, `archived_at`.
- `merge_projects`: die drei Felder gehören zu `_KEEP_FIELDS` (das bleibende Projekt
  behält seinen Archiv-Zustand).

## Oberfläche

- **Detailseite:** Banner (Farbe über `semanticColors.ts` → `ARCHIVE_COLOR`) mit
  Begründung und Datum; Aktion „Archivieren" (Begründung als Pflichtfeld) im
  Projekt-Menü neben „Löschen", für archivierte „Wiederherstellen".
- **Admin-Seite „Archiv"** (`/admin/archive`): Liste mit Name, Begründung, Datum,
  Elternprojekt, Aktion „Wiederherstellen"; verlinkt aus der Admin-Übersicht;
  360-px-tauglich (Karten statt Tabelle).

## Akzeptanzkriterien

- [ ] Archivieren verlangt eine nicht leere Begründung und `project.delete`.
- [ ] Mit FinVe-/GVFG-Zuordnung, nicht archivierten Teilprojekten oder ABGEBROCHEN
      wird abgelehnt; die Meldung nennt die Verknüpfungen.
- [ ] Ein archiviertes Teilprojekt fehlt in Liste, Karte, Gruppen, Picker,
      Teilprojekten, Zeitleiste, MCP-Listen und Import-Kandidaten.
- [ ] Die Elterngeometrie enthält die Geometrie des archivierten Teilprojekts nicht
      mehr; nach dem Wiederherstellen wieder.
- [ ] Die Stand-Spanne des Elternprojekts ignoriert das archivierte Teilprojekt;
      ein Elternprojekt nur mit archivierten Kindern ist kein `is_superior`.
- [ ] Archivierte Projekte stehen nicht unter `/admin/drafts`, aber unter `/admin/archive`.
- [ ] Detailseite per URL erreichbar, mit Banner.
- [ ] Beide Wege (REST, MCP) schreiben einen ARCHIVE/UNARCHIVE-Eintrag ins Änderungsprotokoll.
- [ ] Migration nur additiv.

## Nacharbeit nach dem Deploy

Die 8 Puttgarden-Teilmaßnahmen 1716, 1717, 1718, 1719, 1720, 1722, 1691, 1693
archivieren (Begründung „Ersetzt durch PFA-Abschnitte laut VIB 2024 (B.4.2.14), neue
Teilprojekte 2964–2970, 1715, 1721") und ihren Entwurfs-Status zurücknehmen — als
Checkliste im Issue #264, erst nach dem Deploy.
