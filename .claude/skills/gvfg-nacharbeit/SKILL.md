---
name: gvfg-nacharbeit
description: Arbeitet eine im Frontend importierte Ausgabe des GVFG-Bundesprogramms per MCP nach — offene Vorhaben Projekten zuordnen, Mehrfachzuordnungen und Dubletten bereinigen, vom Import angelegte Entwürfe prüfen, Zuordnungen über alle Ausgaben angleichen. Verwenden, wenn der Nutzer sagt „GVFG-Import nacharbeiten“, „GVFG aufräumen“, „GVFG-Vorhaben zuordnen“, „GVFG 20xx prüfen“.
metadata:
  mcp: true
---

# GVFG-Import nacharbeiten

Das GVFG-Bundesprogramm (Vorhaben des ÖPNV nach § 6 Abs. 1 GVFG) wird **im Frontend**
importiert (PDF hochladen → Review → Bestätigen). Der Import ordnet jedes Vorhaben per
Schlüssel, Schlüssel ohne Suffix oder Namen einem Projekt zu und legt fehlende Projekte
als **Entwurf** an. Übrig bleiben Vorhaben ohne Projekt, Vorhaben mit mehreren Projekten
(meist Dubletten) und Entwürfe. Diesen Rest arbeitest du hier per MCP ab. Den Import
selbst kann der MCP nicht.

**Grundregel:** Ein Vorhaben gehört zu dem Projekt, dessen `project_number` sein
Schlüssel ist (Schreibweise egal, `02 G 509 _ A` = `02G509_A`). Zuordnungen wirken
sofort und stehen im Änderungsprotokoll. Bist du unsicher, lass das Vorhaben offen und
sag es im Bericht. Projekte zusammenführen, anlegen oder fertigstellen nur, wenn der
Nutzer das für diesen Lauf will — frag einmal vorab, nicht je Vorhaben.

Rechte: `assignment.manage` (Zuordnen), für Bereinigung zusätzlich `project.merge`,
`project.create`, `project.edit`.

## 1. Lage erfassen

1. `list_gvfg_programs` — je Ausgabe `program_id`, `entries` und
   `entries_without_project`. Die neueste Ausgabe zuerst, ältere danach (dort sind
   offene Vorhaben meist schon in einer jüngeren Ausgabe gelöst).
2. Je Ausgabe die Arbeitslisten holen (`limit` hoch, mit `offset` blättern):
   - **offen:** `list_gvfg_entries(program_id, has_project=false)`
   - **mehrfach:** alle Vorhaben mit mehr als einem Eintrag in `projects`
   - **Entwurf:** Vorhaben, deren Projekt `is_draft: true` ist
3. Dem Nutzer die Zahlen nennen und fragen, ob auch zusammengeführt bzw. angelegt
   werden darf.

## 2. Offene Vorhaben zuordnen

Je Vorhaben ohne Projekt:

1. `get_gvfg_entry(entry_id)` → `history`: Hat derselbe Schlüssel in einer anderen
   Ausgabe ein Projekt, ist das der erste Kandidat.
2. Sonst suchen: `list_projects(search=<Schlüssel>, drafts="include")`, dann mit
   markanten Wörtern aus Name und Stadt; bei Teilmaßnahmen das Oberprojekt
   (`list_projects(superior_project_id=…)`).
3. Prüfen: `project_number` = Schlüssel? Passen Name, Stadt/Region und Land? Ein
   Schlüssel ohne passendes Suffix (`_A` statt `_B`) ist ein anderes Vorhaben, wenn
   beide in derselben Ausgabe stehen.
4. `assign_gvfg_entry(entry_id, [project_id], all_editions=true)` — `all_editions`,
   damit der Schlüssel in allen Ausgaben auf dasselbe Projekt zeigt. Nur ohne
   `all_editions`, wenn sich das Vorhaben zwischen den Ausgaben wirklich geändert hat
   (Aufteilung, z. B. `03 D 2807_A` 2023 → 2807/2842/2843 2025).
5. Kein Projekt gefunden: mit Erlaubnis `create_project(name, project_number=<Schlüssel>,
   project_groups=["GVFG"], superior_project_id=…)` — bleibt Entwurf — und zuordnen;
   sonst offen lassen.

Ein Vorhaben mit mehreren echten Projekten (Sammelvorhaben) bekommt alle in
`project_ids`; das ist die Ausnahme, nicht die Regel.

## 3. Mehrfachzuordnungen und Dubletten

Zeigt ein Vorhaben auf zwei Projekte, ist eines meist eine Dublette (gleicher
Schlüssel, andere Schreibweise oder vom Import neu angelegt).

1. Beide mit `get_project` ansehen. Echte Dublette oder zwei verschiedene Vorhaben?
   Ein Indiz ist die Geometrie: `check_geometry(project_id=…)` meldet unter `overlaps`
   Projekte auf derselben Strecke; `possible_duplicate` heißt, beide Linien decken sich
   fast vollständig. Allein kein Beweis — Ausbau und Elektrifizierung derselben Strecke
   überlappen zu Recht.
2. Bleibendes Projekt wählen, in dieser Reihenfolge: kein Entwurf und in Gruppe GVFG →
   manuell gepflegte Daten → bessere Geometrie → Beschreibung mit Fördersatz.
3. `merge_projects(survivor_id, merged_id)` **ohne** `apply`, Plan lesen (Felder,
   verschobene Verknüpfungen, Warnungen), dann mit `apply=true`.
4. `assign_gvfg_entry(entry_id, [survivor_id], all_editions=true)` — ersetzt die
   bisherigen Verknüpfungen, damit das Vorhaben nicht doppelt zählt.
5. Ohne Erlaubnis zum Zusammenführen: nur die falsche Zuordnung mit
   `assign_gvfg_entry` entfernen, die Dublette im Bericht nennen.

## 4. Entwürfe aus dem Import

`list_projects(project_group="GVFG", drafts="only")` zeigt, was der Import angelegt hat.
Je Entwurf:

- Gibt es ein gepflegtes Projekt zum selben Vorhaben → wie in 3 zusammenführen
  (Entwurf ist `merged_id`).
- Gehört er unter ein Oberprojekt (Stadtbahnnetz, S-Bahn-Ausbau) →
  `update_project` mit `superior_project_id`, nur bei eindeutigem Fall.
- Sonst bleibt er Entwurf. Fertigstellen (`set_project_draft(id, false)`) nur, wenn der
  Nutzer es will und das Projekt Daten hat (mindestens Beschreibung; Geometrie per
  `route_project_geometry`/`edit_project_geometry` ist ein eigener Schritt).
- Ein Projekt, das durch **andere** Projekte ersetzt wurde (keine Dublette), wird nicht
  als Entwurf geparkt, sondern mit `archive_project(id, reason, replaced_by_project_id)` (Nachfolger, wenn genau ein Projekt das alte ersetzt) archiviert — erst
  nachdem seine GVFG-Zuordnung umgehängt ist (`assign_gvfg_entry`), sonst lehnt das Tool
  ab. Nur auf Wunsch des Nutzers.

Gruppen setzt `assign_gvfg_entry` selbst („GVFG“, Land 08 auch „GVFG BW“) und entfernt
nie welche — keine Gruppen von Hand nachziehen.

**Archivierte Projekte mit Nachfolger:** Eine Vorjahres-Zuordnung auf ein archiviertes,
ersetztes Projekt ist schon auf den Nachfolger umgelenkt (Hinweis „umgelenkt …“ bzw.
`redirected_from`). Ordnest du trotzdem ein archiviertes Projekt zu, meldet das Tool es in
`warnings` samt Nachfolger. `get_project` zeigt `replaced_by` / `replaces`.

## 5. Gegenprobe und Bericht

1. `list_gvfg_programs` erneut: `entries_without_project` je Ausgabe.
2. Stichprobe Mehrfachzuordnungen in der neuesten Ausgabe: keine übrig, die du nicht
   bewusst so gelassen hast.
3. Bericht an den Nutzer:
   - **Stand:** je Ausgabe zugeordnet / gesamt, vorher → nachher offen.
   - **Zugeordnet:** Anzahl, Auffälliges mit Begründung (Zuordnung ohne
     Schlüsselgleichheit, abweichende Ausgabe, Sammelvorhaben).
   - **Bereinigt:** zusammengeführte Projekte (bleibend ← entfernt), angelegte Projekte.
   - **Offen:** Vorhaben ohne Projekt und warum; Entwürfe, die noch Pflege brauchen.
