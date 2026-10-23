---
name: fulda-runde
description: Liest eine Antwort der Bundesregierung auf eine Kleine Anfrage zu den „Ergebnissen der Fulda-Runde“ (PDF) ins Schienendashboard ein — Dokument anlegen, jede Projektzeile mit Kategorie, Fundstelle und Wortlaut erfassen, Projekten zuordnen, bestätigen. Verwenden, wenn ein Fulda-Runde-PDF vorliegt oder der Nutzer sagt „Fulda-Runde einlesen“, „Fulda-Antwort einarbeiten“, „Fulda 20xx nachtragen“.
metadata:
  mcp: true
---

# Fulda-Runde einlesen

Die Fulda-Runde (BMV, EBA, DB InfraGO, DB Energie) legt jährlich fest, welche
Bedarfsplan-Vorhaben in die nächste Leistungsphase gehen. Öffentlich wird das nur über
Antworten der Bundesregierung auf Kleine Anfragen. Du liest das PDF selbst und schreibst
die Aussagen über die MCP-Tools des Schienendashboards. Das Dashboard behandelt die
Fulda-Runde als Vorankündigung mit etwas geringerer Glaubwürdigkeit als die Berichte.

**Grundregel:** Erfasse, was dasteht — wörtlich, mit Fundstelle. Nichts erfinden, nichts
glätten. Wenn du unsicher bist, lass die Zuordnung offen und sag es im Bericht.

## 1. Dokument anlegen

1. Aus dem Anschreiben: Drucksache (z. B. `21/5855`), Datum der Antwort, Titel. Das
   **Jahr** ist das Fulda-Jahr aus dem Titel („Ergebnisse der Fulda-Runde 2026“ → 2026).
2. `list_fulda_documents(year)` — gibt es die Drucksache schon, nicht neu anlegen,
   sondern mit dieser `document_id` weiterarbeiten (nur offene Einträge ergänzen).
3. `create_fulda_document` mit `answer_status`:
   - `VOLLSTAENDIG` — alle Fragen mit Projektlisten beantwortet,
   - `TEILWEISE` — einzelne Fragen ohne Liste („bleibt abzuwarten“, „abhängig vom
     Haushalt“, Verweis auf Haushaltsanlage),
   - `OHNE_ERGEBNIS` — gar keine Projektlisten (z. B. 2025: „Fulda-Prozess nicht
     abgeschlossen“).
   In `note` kurz: welche Fragen unbeantwortet sind und mit welcher Begründung.
   DIP-Link (`dip_url`), wenn bekannt.

## 2. Fragen einer Kategorie zuordnen

`list_fulda_categories` liefert die Liste. Ordne jede Projektliste nach dem **Wortlaut
der Frage und des Antwortsatzes** zu — **nie nach der Frage-Nummer**, die wechselt jedes
Jahr.

| Formulierung (Beispiele) | Kategorie |
|---|---|
| „sind aktuell in der Sammelfinanzierungsvereinbarung Lph 1/2 enthalten“ | `IN_LPH_1_2` |
| „… Sammelfinanzierungsvereinbarung Lph 3/4 enthalten“ | `IN_LPH_3_4` |
| „haben aktuell eine Baufinanzierungsvereinbarung“ (mit Liste) | `HAS_BAUFINVE` |
| „haben Lph 1 und 2 abgeschlossen und erhalten keine Aufnahme in Lph 3/4“ | `COMPLETED_LPH_1_2_NO_FOLLOWUP` |
| „haben Lph 3/4 abgeschlossen und erhalten keine Baufinanzierungsvereinbarung“ | `COMPLETED_LPH_3_4_NO_FOLLOWUP` |
| „Abschluss Lph. 1“ (eigene Liste) | `COMPLETES_LPH_1` |
| „Abschluss Lph. 2“ oder „schließen … die Leistungsphasen 1/2 ab“ | `COMPLETES_LPH_2` |
| „werden die Leistungsphasen 3 und 4 … abgeschlossen“ | `COMPLETES_LPH_3_4` |
| „sollen neu in die Sammelvereinbarung Lph 1/2 aufgenommen werden“ | `NEW_LPH_1_2` |
| „erfolgt nach Abschluss Lph 1/2 die Aufnahme in Lph 3/4“ | `NEW_LPH_3_4` |
| „sollen eine Baufinanzierungsvereinbarung erhalten“ | `NEW_BAUFINVE` |

Wichtig:
- **Ist oder Prognose?** „sind enthalten“, „haben“ = Ist. „werden abgeschlossen“,
  „sollen erhalten“, „voraussichtlich“ = Prognose bzw. Neuaufnahme. Prognosen ändern im
  Dashboard nicht die Phase, sondern erscheinen als erwarteter Termin.
- **Termin bei Prognosen** (`expected_date`): „im Laufe des Jahres 2026“, „bis Ende 2026“
  → `2026-12-31`. Ein konkreteres Datum nur, wenn es dasteht.
- **Urheberschaft** (`attributed_to`): „nach Angaben/Auskunft der Deutschen Bahn AG“ →
  `DB`, sonst `BMV`.
- Fragen ohne Projektliste, Finanztabellen (Mittelbedarf, Planungsmittel) und Fragen zu
  Ausschreibungen erzeugen **keine** Einträge.
- Passt eine Liste in keine Kategorie: nicht erfassen, im Bericht nennen.

## 3. Einträge schreiben

`add_fulda_entries(document_id, entries)` — gern alle Zeilen einer Liste in einem Aufruf.
Je Eintrag:

- `raw_name`: Spalte „Projekt“ bzw. der Teil **vor** dem Doppelpunkt, wörtlich (Kürzel
  ABS/NBS, Gedankenstriche, „Projektbündel 3:“ so lassen).
- `abschnitt`: Spalte „Abschnitt“ bzw. Teil **nach** dem Doppelpunkt; fehlt er:
  `Gesamtstrecke`.
- `raw_text`: die Zeile oder Zelle **wörtlich**, wie sie im PDF steht (Tabellen als
  `Projekt | Abschnitt`).
- `question_ref` („Frage 3“), `page` (Seite im PDF).

**Sammelzellen aufteilen:** Nennt eine Abschnitt-Zelle mehrere eigenständige Maßnahmen
(z. B. „Großknoten Hamburg“: „Kreuzungsbauwerk Wilhelmsburg, Verbindungskurve Harburg,
zusätzlicher Bahnsteig im Hbf, …“), lege **je Maßnahme einen Eintrag** an — gleicher
`raw_name`, gleicher `raw_text`, je eigener `abschnitt`. Eine Aufzählung von
Planfeststellungsabschnitten („PFA 2.0, PFA 3.1 bis 3.2a“) bleibt dagegen ein Eintrag,
außer es gibt im Dashboard getrennte Teilprojekte dafür.

**Fußnoten** auflösen: „Kombinierter Verkehr *)“ mit „*) Umfasst die Standorte …“ → je
Standort ein Eintrag, wenn es Teilprojekte gibt, sonst ein Eintrag mit der Fußnote im
`raw_text`.

Jede Aussage genau **einmal** — die gleiche Zeile nie unter zwei Kategorien.

## 4. Projekte zuordnen

`add_fulda_entries` liefert je Eintrag einen automatischen Vorschlag (`project_ids`,
`assignment_note` = „Automatischer Vorschlag …, ungeprüft“). Prüfe **jeden**:

1. Projekt suchen mit `list_projects(search=…)`; bei Projektbündeln und Großknoten die
   Teilprojekte mit `list_projects(superior_project_id=…)` ansehen.
2. **Teilprojekt bevorzugen**, wenn der Abschnitt einem Teilprojekt entspricht; sonst
   das Oberprojekt. Eine Aussage über die „Gesamtstrecke“ gehört ans Oberprojekt.
3. `assign_fulda_entry(entry_id, project_ids, note)` — `note` sagt knapp, warum
   („Teilprojekt ‚Lehrte‘, Name und Abschnitt stimmen überein“). Auch einen richtigen
   Vorschlag so bestätigen, damit die Notiz nicht mehr „ungeprüft“ sagt.
4. Fehlt ein Teilprojekt und ist der Abschnitt klar abgegrenzt: mit `create_project`
   (`superior_project_id`) anlegen und zuordnen — im Bericht nennen.
5. Wirklich unklar (mehrere plausible Projekte, Projekt fehlt ganz): `project_ids: []`
   mit Begründung in `note`, Eintrag bleibt offen.

**Ersetzte Projekte:** Ein Vorschlag auf ein ersetztes Projekt ist schon auf den Nachfolger
umgelenkt (Grund bzw. Hinweis „umgelenkt von … (ersetzt)“). Die Zuordnungs-Tools melden in
`warnings`, wenn du trotzdem ein ersetztes Projekt zuordnest — dann gehört die Meldung meist
zum Nachfolger (`replaced_by_project_id`). `list_projects` zeigt ersetzte Projekte nur mit
`include_ended=true`.

Fehler im Eintrag korrigierst du mit `update_fulda_entry`, Fehleinträge entfernst du mit
`delete_fulda_entry`.

## 5. Bestätigen

`list_fulda_entries(document_id, only_open=true)` — keine „ungeprüft“-Notiz darf übrig
sein, die du nicht angesehen hast. Dann `confirm_fulda_document(document_id)`. Bestätigt
werden nur Einträge mit Projekt; offene bleiben offen.

## 6. Bericht an den Nutzer

Kurz, in dieser Gliederung:

- **Dokument:** Drucksache, Datum, Antwortstand, unbeantwortete Fragen.
- **Übernommen:** Anzahl je Kategorie.
- **Selbst entschieden:** angelegte Teilprojekte, aufgeteilte Sammelzellen, abweichende
  Zuordnungen — je mit Begründung.
- **Offen:** Einträge ohne Projekt und warum; Listen, die in keine Kategorie passten.

Die Freigabe-Ansicht im Dashboard: Admin → Fulda-Runde → Jahr.
