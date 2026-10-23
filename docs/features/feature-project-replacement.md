# Feature: Projekt ersetzt durch ein anderes

**Status: in Umsetzung (2026-10-23).** Gehört zum Planungsstand
([`feature-project-progress.md`](feature-project-progress.md) → Lebenszyklus-Overlay).

## Ziel

Festhalten, dass ein Projekt durch ein anderes **ersetzt** wurde, mit Verweis auf
das Nachfolgeprojekt, sichtbar beim Projektstatus. Beide Projekte bleiben bestehen;
das alte behält seine Historie (Quellen, FinVe, VIB-Jahrgänge) und bleibt
erreichbar, zählt aber nicht mehr als laufendes Vorhaben.

Anlass: 1477 „ABS/NBS Hannover – Bielefeld (BVWP)“ (2-016-V01) wird durch
1535 „NBS/ABS Bielefeld – Seelze“ (D-14) ersetzt. Bisher nur über Projekttexte
abgebildet (Warnung an 1477, Info an 1535, je mit Weblink).

### Abgrenzung zum Zusammenführen

[`feature-project-merge.md`](feature-project-merge.md) bereinigt **Dubletten**: Das
verworfene Projekt wird gelöscht, alte Links leiten um, bewusst ohne
„Geister-Projekt mit `merged_into_id`“. Das Ersetzen ist etwas anderes: Es sind zwei
fachlich verschiedene Vorhaben, das alte hat eine eigene, weiterhin gültige Historie.
Deshalb gibt es hier genau das Muster, das die Zusammenführung vermeidet — ein
Projekt mit Verweis auf den Nachfolger, das Listen, Karte und Summen ausfiltern
(Entscheidung W1, 2026-10-23).

## Datenmodell

- `LifecycleStatus` bekommt den Wert **`ERSETZT`** (neben `AKTIV`, `PAUSIERT`,
  `ABGEBROCHEN`). Gespeichert wie bisher als String in `project_progress.lifecycle_status`.
- Neue Spalten auf `project_progress` (Expand, alle nullable):
  - `replaced_by_project_id` — FK `project.id`, `ondelete SET NULL`. Pflicht bei
    `ERSETZT`, sonst immer leer.
  - `lifecycle_note` (Text) — Begründung, für **jeden** Status außer `AKTIV`
    (Entscheidung W7).
  - `lifecycle_date` (Date) — seit wann der Status gilt, ebenfalls für jeden Status.
- Wechsel zurück auf `AKTIV` leert Nachfolger, Begründung und Datum.
- Regeln beim Setzen (Fehler 422 bzw. MCP-Fehlermeldung):
  - Nachfolger ≠ das Projekt selbst, existiert, ist kein Entwurf.
  - Keine Ringe: Folgt man den Nachfolgern ab dem Nachfolger, darf man nicht beim
    Projekt ankommen. Ketten (A → B → C) sind erlaubt.
  - Nachfolger nur zusammen mit `ERSETZT`.
- Alle Felder stehen im Änderungsprotokoll (`progress.*`).

## Anzeige

- **Altes Projekt:** Banner im Planungsstand (`LifecycleOverlay`) „Projekt ersetzt“,
  Text „Ersetzt durch <Name (Nummer)>“ mit Link, darunter Begründung und Datum.
  Der zuletzt bekannte Planungsstand bleibt abgeblendet sichtbar (Overlay-Regel).
- **Nachfolger:** Hinweis „Ersetzt <Name (Nummer)>“ mit Link (Rückverweis, auch
  mehrere), im Planungsstand oberhalb des Steppers.
- **Pausiert / abgebrochen:** Banner zeigt zusätzlich Begründung und Datum, wenn erfasst.
- **Bearbeitung** im `ProgressEditDrawer`, Abschnitt „Lebenszyklus“: Status, bei
  `ERSETZT` eine Projektsuche für den Nachfolger, Begründung, Datum.
- Badges in Liste, Teilprojekt-Tabelle, Zeitstrahl: „Ersetzt“ grau wie die anderen
  Lebenszyklus-Badges.
- Die Projekttexte 55/56 sind danach redundant; ob sie bleiben, entscheidet die
  Redaktion (keine automatische Löschung).

## Listen, Karte, Filter (Entscheidung W2, 2026-10-23)

Ersetzt die frühere Regel „Lebenszyklus filtert nie“ aus
`feature-project-progress.md` → Phasenfilter.

- Neuer Filter **„Beendete Projekte einblenden“** (URL `?beendet=1`) in Liste und
  Karte, neben Phase und Zeitraum. **Voreinstellung: aus** — `ERSETZT` und
  `ABGEBROCHEN` sind ausgeblendet. `PAUSIERT` bleibt sichtbar.
- Eingeblendet werden sie wie bisher nach ihrer Headline-Phase gefiltert und grau
  markiert.
- Der Zähler „x von y“ zählt die ausgeblendeten Projekte nicht mit, solange der
  Schalter aus ist; eine aktive Einblendung erscheint als Filtermarke.
- MCP `list_projects`: ohne `lifecycle_status` gilt dieselbe Voreinstellung
  (beendete ausgeblendet); `lifecycle_status` gesetzt → genau dieser Status;
  `include_ended=true` → alle.
- Direkter Aufruf `/projects/{id}` und die Suche über die URL funktionieren immer.

## Oberprojekte (Entscheidung W3, 2026-10-23)

Ausnahme vom Grundsatz „Parent projects always aggregate“ (`docs/architecture.md`):

- Ein **ersetztes** Teilprojekt (samt seinen eigenen Teilprojekten) fällt aus allem
  heraus, was ein Oberprojekt über seine Teilprojekte bildet: Phasenspanne,
  Phasenverteilung der Teilprojekt-Tabelle, Zeitstrahl, Summen und Listen aus
  Teilprojekten (FinVe, Infraplan-Kostenprognose, GVFG-Förderung in Teilprojekten).
  Grund: Der Nachfolger trägt dasselbe Vorhaben, sonst wird doppelt gezählt.
- In der Teilprojekt-Tabelle bleibt es als Zeile mit Badge „Ersetzt“ sichtbar.
- `ABGEBROCHEN` zählt weiter mit (ausgegebenes Geld ist real ausgegeben).
- Die Geometrie eines Oberprojekts (`geojson_from_subprojects`) bleibt unverändert.

## Importe (Entscheidung W5, 2026-10-23)

- Gemeinsame Helfer in `crud/projects/projects.py` (dort, weil auch `crud/gvfg.py` sie
  ohne Importzyklus braucht): `successor_map` (folgt Ketten), `redirect_replaced` und
  `replacement_warnings`.
- **Vorschläge** (VIB per PDF und per MCP, Fulda-Runde, Infraplan, GVFG), auch die
  Übernahme aus dem Vorjahr, werden auf den Nachfolger umgelenkt. Hinweis: VIB im Grund
  („… · umgelenkt von „X“ (ersetzt)“), Fulda in der `assignment_note`, GVFG als Flag,
  Infraplan im Feld `redirected_from` des Vorschlags. PFA-Teilprojekt-Vorschläge der VIB
  werden nicht umgelenkt (sie zeigen auf Teilprojekte des zugeordneten Vorhabens).
- **Bestätigte Zuordnungen** bleiben unangetastet — das Setzen von `ERSETZT` hängt
  nichts um.
- Eine Zuordnung von Hand auf ein ersetztes Projekt bleibt erlaubt. MCP-Tools für
  Zuordnungen melden dann eine Warnung mit dem Nachfolger.

## MCP

- Neues Tool **`set_lifecycle_status`** (`progress.edit`): `project_id`, `status`,
  `replaced_by_project_id`, `note`, `date`. Wirkt sofort, Änderungsprotokoll.
- `get_project_progress` liefert `replaced_by`, `replaces`, `lifecycle_note`,
  `lifecycle_date`.
- Skill `schienendashboard` (und die Import-Skills) beschreiben Ersetzen,
  Umlenken und die Abgrenzung zum Zusammenführen.

## Zusammenführen und Löschen (Entscheidung W6, 2026-10-23)

- `project_progress` ist bei der Zusammenführung Sondertabelle. Deshalb eigene
  Behandlung: Verweise anderer Projekte auf das verworfene Projekt
  (`replaced_by_project_id`) werden auf das bleibende umgebogen. Lebenszyklus,
  Nachfolger, Begründung und Datum des verworfenen Projekts füllen das bleibende,
  wenn dort AKTIV steht. Würde das bleibende sein eigener Nachfolger, wird der
  Verweis geleert (Warnung in der Vorschau).
- Löschen eines Nachfolgers leert den Verweis (`SET NULL`); der Status bleibt
  `ERSETZT` ohne Nachfolger.

## Deploy und Rollback (Entscheidung W4, 2026-10-23)

Zwei Schritte, damit ein Rollback trägt:

1. Vorab-Änderung: Die Antwortschemas lesen unbekannte Lebenszyklus-Werte als
   `AKTIV` (statt Validierungsfehler). Muss **vor** Schritt 2 ausgerollt sein.
2. Das Feature selbst (Migration nur Expand: drei neue nullable Spalten).

Nach einem Rollback auf einen Stand ab Schritt 1 erscheinen ersetzte Projekte als
aktiv, sonst bricht nichts.

## Akzeptanzkriterien

- [ ] Status `ERSETZT` mit Nachfolger, Begründung und Datum lässt sich im Drawer
      und per MCP setzen und wieder auf `AKTIV` zurücknehmen.
- [ ] Begründung und Datum gibt es auch für `PAUSIERT` / `ABGEBROCHEN`.
- [ ] Altes Projekt zeigt „Ersetzt durch …“ mit Link, Nachfolger zeigt „Ersetzt …“.
- [ ] Liste und Karte blenden `ERSETZT`/`ABGEBROCHEN` standardmäßig aus, der
      Schalter „Beendete Projekte einblenden“ holt sie zurück (auch per URL).
- [ ] Oberprojekte zählen ersetzte Teilprojekte nicht in Spanne, Verteilung,
      Zeitstrahl und Summen.
- [ ] Importvorschläge auf ein ersetztes Projekt zeigen auf den Nachfolger, mit Hinweis.
- [ ] Zusammenführung biegt Nachfolger-Verweise um; Löschen leert sie.
- [ ] 1477 ist als ersetzt durch 1535 erfasst.

## Entscheidungen

| # | Datum | Entscheidung |
|---|---|---|
| W1 | 2026-10-23 | Ersetzen ist kein Zusammenführen; das Nachfolger-Muster ist hier gewollt, Begründung oben. |
| W2 | 2026-10-23 | Filter „Beendete Projekte einblenden“, Voreinstellung blendet `ERSETZT` und `ABGEBROCHEN` aus. |
| W3 | 2026-10-23 | Ersetzte Teilprojekte fallen aus Spanne, Verteilung, Zeitstrahl und Summen; `ABGEBROCHEN` zählt weiter. |
| W4 | 2026-10-23 | Zweistufiger Deploy: erst tolerantes Lesen unbekannter Werte, dann der neue Wert. |
| W5 | 2026-10-23 | Importvorschläge auf den Nachfolger umlenken (mit Hinweis), bestätigte Zuordnungen bleiben. |
| W6 | 2026-10-23 | Nachfolger auf `project_progress`, eigene Behandlung beim Zusammenführen, `SET NULL` beim Löschen. |
| W7 | 2026-10-23 | Begründung und Datum für jeden Lebenszyklus-Status außer `AKTIV`. |
