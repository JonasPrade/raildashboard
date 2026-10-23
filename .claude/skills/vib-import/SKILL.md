---
name: vib-import
description: Liest einen Verkehrsinvestitionsbericht (VIB, Abschnitt B Schienenwege) per MCP ins Schienendashboard ein oder prüft einen vorhandenen Jahrgang — Bericht anlegen, jedes Vorhaben mit Abschnitten, Kenndaten und PFA-Tabelle erfassen, Projekten zuordnen (mit Begründung, auch mehreren), bestätigen. Verwenden, wenn ein VIB-PDF vorliegt oder der Nutzer sagt „VIB einlesen“, „VIB 20xx nachtragen“, „VIB-Zuordnungen prüfen“.
metadata:
  mcp: true
---

# VIB einlesen

Der Verkehrsinvestitionsbericht (Bundestagsdrucksache „Verkehrsinvestitionsbericht für
das Berichtsjahr XXXX“) beschreibt jährlich die Bedarfsplan-Vorhaben. Du liest das PDF
selbst und schreibst die Vorhaben über die MCP-Tools. Alles, was du schreibst, ist
**unbestätigt** und wirkt erst nach `confirm_vib_report` auf den Planungsstand.

**Grundregel:** Erfasse, was dasteht — Texte wörtlich, mit Fundstelle. Nichts erfinden,
nichts glätten, nichts aus einem anderen Vorhaben übernehmen. Bist du bei einer
Zuordnung unsicher, lass sie offen und sag es im Bericht.

Zwei Modi:
- **Einlesen** — ein neuer Jahrgang (Abschnitte 1–6).
- **Prüfen** — ein vorhandener Jahrgang soll korrigiert werden (Abschnitt 7).

## 1. Bericht anlegen

1. Vom Deckblatt: **Berichtsjahr** aus dem Titel (nicht das Erscheinungsjahr),
   **Drucksachennummer** (z. B. `20/12345`) und das **Datum der Drucksache** — das ist
   `report_date`; es gewichtet den VIB gegen spätere Quellen (z. B. Fulda-Runde).
2. `list_vib_reports` — gibt es das Jahr schon, nicht neu anlegen: mit dieser
   `report_id` weiterarbeiten (fehlende Vorhaben ergänzen) oder in den Prüfmodus gehen.
3. `create_vib_report(year, report_date, drucksache_nr)`.

## 2. Vorhaben finden

Nur **Abschnitt B (Schienenwege)**. Die Vorhaben stehen als nummerierte Blöcke
`B.4.x.y` (Gliederung im Inhaltsverzeichnis). Die Kategorie folgt der übergeordneten
Gliederungsüberschrift:

| Gliederung | `category` |
|---|---|
| B.4.1 — laufende und fest disponierte Vorhaben | `laufend` |
| B.4.2 — neue Vorhaben | `neu` |
| B.4.3 — Vorhaben des potenziellen Bedarfs | `potentiell` |
| abgeschlossene Vorhaben (eigene Gliederung oder Hinweis „abgeschlossen“) | `abgeschlossen` |

Lies die Überschrift des jeweiligen Jahrgangs; weicht die Nummerierung ab, gilt der
Wortlaut der Gliederungsüberschrift. Ein Vorhaben endet, wo das nächste `B.4.x.y`
beginnt — Tabellen und Fußnoten dazwischen gehören zum vorangehenden Vorhaben.

## 3. Ein Vorhaben erfassen

`add_vib_entries(report_id, entries)` — wenige Vorhaben (etwa 3–5) je Aufruf, die Texte
sind lang. Je Vorhaben:

- `vib_section`: `B.4.1.3`; `vib_name_raw`: die Überschrift wörtlich ohne Nummer
  (mit „Lfd. Vorhaben Nr. …“, „ABS/NBS“, „(VDE Nr. 1)“); `page`: Seite im PDF.
- **Textabschnitte** nach ihren Zwischenüberschriften, jeweils der ganze Absatz
  wörtlich:
  - „Verkehrliche Zielsetzung“ → `verkehrliche_zielsetzung`
  - „Durchgeführte (und geplante) Maßnahmen“ → `durchgefuehrte_massnahmen`
  - „Noch umzusetzende Maßnahmen“ → `noch_umzusetzende_massnahmen`
  - „Bauaktivitäten [Jahr]“ → `bauaktivitaeten`
  - „Teilinbetriebnahmen [Jahr]“ → `teilinbetriebnahmen` („Keine“ wörtlich)
  - „Projektstand“ / „Planungsstand“ → `planungsstand`
  - Fußnoten, Hinweise, Querverweise ohne eigene Überschrift → `sonstiges`

  Ein Wort wie „Termine“ oder „Planung“ **im Fließtext** ist keine Überschrift. Fehlt
  ein Abschnitt, Feld weglassen.
- **Kenndaten** (Kasten „Projektkenndaten“): `strecklaenge_km`, `gesamtkosten_mio_eur`
  (Mio. €, Dezimalpunkt), `entwurfsgeschwindigkeit` (z. B. `"160/230"`). Nur, was im
  Kasten steht.
- **Status** — drei Häkchen, gleichzeitig möglich:
  - `status_planung`: Teile sind in Vorplanung, Entwurfs-/Genehmigungsplanung oder im
    Planfeststellungsverfahren.
  - `status_bau`: Teile sind im Bau (Bauaktivitäten im Berichtsjahr, Baubeginn erfolgt).
  - `status_abgeschlossen`: das Vorhaben oder Teile sind in Betrieb genommen.

  Entscheide aus **Projektstand, Bauaktivitäten, Teilinbetriebnahmen** und den
  **Termin-Spalten** der PFA-Tabelle — **nie** aus dem Wort „abgeschlossen“ oder „offen“
  in der Spalte „Entwurfsplanung“ und nie aus dem Spaltenkopf.
- **PFA-Tabelle** (`pfa_entries`) zeilenweise, Zellen wörtlich (Daten wie `12/2019`
  so lassen):
  - Gruppenzeilen ohne Nummer („Lübeck–Bad Kleinen (a)“, „1. Baustufe“) sind keine
    eigene Zeile, sondern `abschnitt_label` der folgenden Zeilen.
  - Fortsetzungszeilen ohne „Nr. PFA“ gehören mit ihrer Örtlichkeit zur Nummer darüber.
  - Freitext in einer Zelle (z. B. „Teilmaßnahme wurde im Rahmen von … umgesetzt“)
    bleibt in der Zelle, in der er steht.
  - Spalten: Nr. PFA, Örtlichkeit, Entwurfsplanung, Abschluss FinVe, Datum PFB,
    Baubeginn, Inbetriebnahme.
  - Geht eine Tabelle über eine Seitengrenze, die Zeilen nahtlos fortsetzen.

## 4. Projekte zuordnen

`add_vib_entries` gibt je Vorhaben `suggestions` (Vorjahr → VDE-Nummer →
Namensähnlichkeit, mit Grund) zurück und ordnet höchstens den besten Vorschlag vor
(„Automatischer Vorschlag …, ungeprüft“). Prüfe **jedes** Vorhaben:

1. Vorschlag ansehen; ein Vorschlag „Vorjahr“ ist meist richtig, aber prüfe, ob sich das
   Vorhaben seither geteilt oder umbenannt hat.
2. Sonst suchen: `list_projects(search=…)` mit markanten Ortsnamen und der VDE- bzw.
   Bedarfsplannummer; Teilprojekte mit `list_projects(superior_project_id=…)`.
3. Das Vorhaben gehört an das **Oberprojekt**, das es als Ganzes beschreibt. Deckt ein
   VIB-Vorhaben **mehrere Dashboard-Projekte** ab (Sammelvorhaben, Projektbündel), ordne
   **alle** zu — eine Liste in `project_ids`.
4. `assign_vib_entry(entry_id, project_ids, note)` — `note` knapp für alle Projekte
   („Oberprojekt ABS Lübeck–Rostock: Name und VDE Nr. 1 stimmen, Vorjahr gleich“). Auch
   einen richtigen Vorschlag so bestätigen, damit „ungeprüft“ verschwindet.
5. Unklar (mehrere plausible Projekte, Projekt fehlt): `project_ids: []` mit Begründung,
   Vorhaben bleibt offen. Fehlende Projekte legst du nur an, wenn der Nutzer das will.

## 5. PFA-Abschnitte Teilprojekten zuordnen

Erst wenn das Vorhaben seinen Projekten zugeordnet ist (Schritt 4) — die Vorschläge kommen
aus dem **ganzen Teilbaum** unter diesen Projekten.

1. `get_vib_entry(entry_id)` zeigt je offener PFA-Zeile `suggested_project_id` mit
   `suggested_reason` und `suggestion_strong`, dazu `subprojects` (Teilbaum mit `depth`):
   - **stark**: „Vorjahr: VIB 20xx bestätigt“ oder „Abschnittsnummer 7.1 ↔ 7 in …“
     (Nummer in Name oder Projektnummer, z. B. `Abschnitt 7`, `PF 15-16`).
   - **schwach**: „Namensähnlichkeit …“ — nur ein Hinweis, immer selbst prüfen.
2. `apply_vib_pfa_suggestions(report_id)` übernimmt alle starken Vorschläge (auch nur für
   einzelne Vorhaben mit `entry_ids`). Sieh dir das Ergebnis an: Eine falsch gelesene
   Nummer (z. B. Fortsetzungszeilen, die alle `nr_pfa` „1“ tragen) landet sonst im falschen
   Abschnitt — korrigieren mit `assign_vib_pfa`.
3. Übrige Zeilen selbst zuordnen: mehrere auf einmal mit `assign_vib_pfas(entry_id,
   items)`, einzeln mit `assign_vib_pfa`. Ein Blatt (Teilprojekt ohne eigene Kinder) ist
   besser als ein Zwischenknoten. Zeilen ohne passendes Teilprojekt bleiben am Vorhaben —
   das ist richtig und kein Fehler.
4. **Fehlende Teilprojekte nur auf Wunsch des Nutzers anlegen**:
   `create_vib_pfa_subprojects(entry_id, items)`, je **Abschnitt** ein Item (alle Zeilen
   derselben Nummer bzw. derselben Gruppenzeile zusammen, z. B. NBS- und ABS-Zeile von 7.1),
   `parent_id` = Projekt des Vorhabens oder ein Projekt darunter, `name` sprechend
   („PFA 7.1 Appenweier–Hohberg“). Das Tool legt **Entwürfe ohne Geometrie** an. Lohnt nur,
   wo Abschnitte desselben Vorhabens **unterschiedlich weit** sind und noch laufen oder
   geplant sind; vollständig in Betrieb genommene Altabschnitte bleiben am Vorhaben.
   Geometrie danach, wenn gewünscht, mit `route_project_geometry`.
5. Meldet ein Item `parent_was_leaf: true`, war das Elternprojekt bisher ein Blatt: Sein
   eigener Stand zählt ab jetzt nicht mehr, nur die Spanne seiner Teilprojekte. Dann:
   - die übrigen PFA-Zeilen desselben Vorhabens ebenfalls zuordnen oder anlegen, damit kein
     Abschnitt unsichtbar wird;
   - `get_project_progress(parent_id)` ansehen — eigene Beobachtungen (FinVe, Fulda,
     manuell) am Elternprojekt, die nun nicht mehr zählen, dem Nutzer nennen;
   - im Bericht unter „Selbst entschieden“ aufführen.

6. **Ersetzte Teilprojekte archivieren, nicht auf Entwurf setzen.** Ersetzen neue
   PFA-Abschnitts-Teilprojekte alte Teilmaßnahmen (andere Schnitte als im Vorjahr), mit
   dem Nutzer klären und dann je altes Teilprojekt
   `archive_project(project_id, reason)` — `reason` nennt Bericht, Abschnitt und die
   neuen Teilprojekte („Ersetzt durch PFA-Abschnitte laut VIB 2024 (B.4.2.14), neue
   Teilprojekte …“). Ein archiviertes Projekt behält seine VIB-Historie und Geometrie,
   zählt aber nirgends mehr (Elternkarte, Stand-Spanne, Summen, Listen) — Geometrie also
   **nicht** leeren. Abgelehnt wird es, solange FinVe- oder GVFG-Zuordnungen oder nicht
   archivierte Teilprojekte daran hängen: die Meldung nennt sie, erst umhängen. Ein
   wirklich abgebrochenes Vorhaben (Lebenszyklus ABGEBROCHEN) wird nie archiviert.
   Dubletten dagegen mit `merge_projects` zusammenführen. Im Bericht unter „Selbst
   entschieden“ aufführen.

Sobald eine Zeile einem Teilprojekt gehört, bekommt das Oberprojekt seinen Stand über die
Teilprojekte. Jede Zuordnung macht das Vorhaben unbestätigt — am Ende `confirm_vib_report`.

## 6. Bestätigen und berichten

1. `list_vib_entries(report_id, only_open=true)` — kein „ungeprüft“ darf übrig sein,
   das du nicht angesehen hast.
2. `confirm_vib_report(report_id)` — bestätigt alle offenen Vorhaben mit Projekt;
   offene ohne Projekt bleiben offen (sie erscheinen im Dashboard unter „Offene
   Zuordnungen“).
3. Bericht an den Nutzer:
   - **Bericht:** Jahr, Drucksache, Datum, Anzahl Vorhaben je Kategorie.
   - **Übernommen:** zugeordnet und bestätigt.
   - **Selbst entschieden:** abweichende Zuordnungen, Mehrfachzuordnungen,
     PFA→Teilprojekt, angelegte Teilprojekt-Entwürfe — je mit Begründung.
   - **Offen:** Vorhaben ohne Projekt und warum; Stellen, die du nicht lesen konntest.

## 7. Prüfmodus: vorhandenen Jahrgang korrigieren

Für Jahrgänge, die über den alten Upload kamen und Fehler haben.

1. `list_vib_reports` → `report_id`; `report_date` mit dem Datum der Drucksache
   vergleichen, falsch → `update_vib_report(report_id, {"report_date": …})`.
2. `list_vib_entries(report_id)` durchgehen. Je Vorhaben `get_vib_entry` und mit dem
   PDF vergleichen:
   - Zuordnung falsch oder unvollständig → `assign_vib_entry` mit Begründung.
   - Text im falschen Feld, Status-Häkchen falsch (typisch beim alten Upload: alle drei
     gesetzt), Kenndaten falsch → `update_vib_entry(entry_id, changes)`.
   - PFA-Tabelle verstümmelt → `set_vib_pfa_entries` (vorhandene `project_id` der
     Zeilen mitgeben, sonst geht die Teilprojekt-Zuordnung verloren).
   - PFA-Zeilen ohne Teilprojekt → wie in Schritt 5: `apply_vib_pfa_suggestions`
     (starke Vorschläge), Rest prüfen; Teilprojekte nur auf Wunsch des Nutzers anlegen.
   - Doppeltes oder falsch erkanntes Vorhaben → `delete_vib_entry`.
   - Fehlendes Vorhaben → `add_vib_entries`.
3. Jede Korrektur macht das Vorhaben unbestätigt. Am Ende `confirm_vib_report` —
   bis dahin fehlen die Daten dieser Vorhaben im Planungsstand, also nicht mitten im
   Jahrgang aufhören, ohne zu bestätigen oder es dem Nutzer zu sagen.
4. Bericht wie in 6, zusätzlich: was korrigiert wurde (Zuordnung / Felder / Tabelle).
