---
name: infraplan-import
description: Führt einen im Frontend hochgeladenen Infraplan (Fünfjahresplan des Bundes für die Schiene) per MCP bis zur Bestätigung — sichere Vorschläge übernehmen, offene Zeilen gesammelt und begründet Projekten oder neuen Teilprojekten zuordnen, Jahrgang bestätigen, Kennzahlen aus dem Seitentext der Diagramme ablesen. Verwenden, wenn der Nutzer sagt „Infraplan einlesen“, „Infraplan 20xx zuordnen“, „Infraplan-Kennzahlen eintragen“.
metadata:
  mcp: true
---

# Infraplan einlesen

Der Infraplan erscheint jährlich (Infraplan 2026 = 2026–2030). Seine Maßnahmentabellen
(Kap. 2.3: Bedarfsplan Teil A–D, GVFG Kat. A/C, InvKG) liefern je Zeile
Realisierungsstand, geplante Inbetriebnahme, Kosten und parlamentarische Befassung. Das
Dashboard hat das PDF schon ausgelesen und Vorschläge gerechnet; du ordnest die Zeilen
Projekten zu, bestätigst den Jahrgang und trägst die Kennzahlen ein. Alle Tools brauchen
das Recht `infraplan.import`.

**Grundregel:** Zuordnen nur mit Begründung, im Zweifel offen lassen und auf die
Prüfliste setzen. Eine offene Zeile kostet nichts — sie landet unter „Offene
Zuordnungen“. Eine falsche Zuordnung verfälscht Planungsstand, Prognose und Kosten.

**Sammeln statt einzeln:** Schreibe mit `assign_infraplan_rows` und
`create_infraplan_subprojects` (viele Zeilen je Aufruf, Ergebnis je Zeile). Die
Einzel-Tools nur für eine einzelne Korrektur.

## 1. Entwurf holen

1. `list_infraplan_drafts` — den neuesten Entwurf des gewünschten Jahrgangs nehmen
   (`status` = `SUCCESS`). Steht `status` auf `PENDING`/`RUNNING`, kurz warten und neu
   abfragen; bei `FAILURE` den `error` berichten und aufhören.
2. **Hat der Entwurf `warnings`: anhalten.** Melde jede Warnung (Lücke oder Dublette in
   den laufenden Nummern, unaufgelöster Kostenverweis, fehlender Abschnitt) und frag,
   wie es weitergehen soll. Bestätigen kann ihn dann nur ein Mensch im Frontend.
   `start_infraplan_parse` liest das PDF neu aus, wenn der Nutzer das will.
3. Ist der Jahrgang unter `years` schon übernommen, nicht neu bestätigen — nur offene
   Zeilen nachtragen (die Sammel-Tools wirken auch auf bestätigte Jahrgänge) und die
   Kennzahlen prüfen.

## 2. Sichere Vorschläge übernehmen

`apply_infraplan_suggestions(draft_id)` mit der Voreinstellung 0.85. Das übernimmt:

| Grund | Bedeutung | Konfidenz |
|---|---|---|
| `NUMBER` | Projektnummer des Vorjahres oder `project_number` des Projekts | 1.0 |
| `GVFG_KEY` | GVFG-Schlüssel in `project_number` | 1.0 |
| `PREVIOUS_YEAR` | gleiche Bezeichnung + Maßnahme im Vorjahr (Zeilen ohne Nummer) | 0.95 |
| `ALIAS` | Deutschlandtakt-Kennung „DT nn“ = Alias des Projekts; nur ein Teil der Zeile („… inkl. DT 2“): 0.8 | 1.0 |
| `CONTEXT` | Teilprojekt des Elternprojekts aus der Bezeichnung, Abschnittsnummer passt (0.9) oder Name eindeutig | bis 0.9 |
| `FUZZY` | ähnlicher Name | Wert |

Vorjahreszuordnungen bringen ihre Notiz mit („Vorjahr 2026: …“). Die Schwelle nur
senken, wenn der Nutzer es sagt.

## 3. Überblick und Arbeitsteilung

`get_infraplan_draft(draft_id, compact=true, only_open=true)` liefert alle offenen
Zeilen aller Abschnitte in einer Antwort: `row_key`, Bezeichnung, Maßnahme, Länder und
den besten Vorschlag (Projekt, Konfidenz, Grund, `detail`). `missing_from_previous` nennt
Projekte des Vorjahres ohne Zeile im neuen Jahrgang — meist umbenannt oder
zusammengelegt.

**In Claude Code mit Subagenten:** Je Abschnittsgruppe ein Subagent (BP_A–B, BP_C,
BP_D, GVFG, InvKG; Kennzahlen getrennt, siehe 6). Ein Subagent **schreibt nichts**,
sondern liefert eine Vorschlagstabelle: `row_key` · Projekt-ID(s) · Begründung ·
Sicherheit (sicher / wahrscheinlich / unklar) · ggf. „Teilprojekt anlegen unter …“. Der
Hauptagent prüft die Tabellen gegen die Regeln unten, vereinheitlicht sie und schreibt
dann gesammelt. In anderen Clients die Abschnitte nacheinander genauso abarbeiten.

## 4. Offene Zeilen zuordnen

Kandidaten finden:

1. Der beste Vorschlag (`best`) und `detail`. `CONTEXT` unter 0.85 mit „daneben
   Teilmaßnahmen ohne Namen“ heißt: Es gibt Teilprojekte, die nur „Teilmaßnahme n“
   heißen — erst deren Beschreibungen ansehen.
2. `list_projects(superior_project_id=…, with_description=true)` zeigt die Teilprojekte
   eines Elternprojekts mit dem ersten Satz der Beschreibung und den Aliasen — ohne
   `get_project` je Teilprojekt.
3. `list_projects(search=…)` sucht in Name, Nummer, Beschreibung und Aliasen: Orte,
   Strecke, „PB 07“ ohne Präfix, „DT 38“; Bundesland aus `laender`. Bei GVFG-Zeilen den
   Schlüssel (z. B. `07 D 2825_A`) suchen.

Regeln für Grenzfälle:

- **Teilprojekt vor Elternprojekt:** Beschreibt die Zeile einen Abschnitt („PFA 9.2“,
  „2gl. Einbindung Bf Stendal“) und gibt es dafür ein Teilprojekt, das Teilprojekt.
- **Sammelzeile → Elternprojekt:** Umfasst die Zeile die ganze Maßnahme („ABS Köln –
  Aachen“, Restmaßnahmen eines Projekts), das Elternprojekt.
- **Zeile mit mehreren benannten Teilmaßnahmen → alle Teilprojekte**
  („Knoten Riesa inkl. Röderau – Zeithain“, „DT 157 Wustermark, DT 158 Rathenow“).
- **Teilprojekt anlegen nur bei eindeutigem Elternprojekt:**
  `create_infraplan_subprojects` mit `parent_id`. Ohne passendes Elternprojekt (z. B.
  GVFG-Vorhaben eines Landes, InvKG-Vorhaben) ohne `parent_id` — dann entsteht ein
  eigenständiges Entwurfsprojekt, das die Nummer der Zeile übernimmt.
- **Kein Raten:** Was nach diesen Regeln nicht eindeutig ist, kommt auf die Prüfliste
  im Bericht und bleibt offen.
- Eine Zeile darf mehreren Projekten gehören (Sammel-GWU, Fußnote „bezieht sich auf
  Teil A 20 und Teil A 33“), mehrere Zeilen einem Projekt.
- Kostenverweise (`cost_ref_raw`, „Ref. Teil B 20“) und Fußnoten brauchen nichts — das
  Dashboard zählt Sammelkosten nur einmal.

Schreiben: `assign_infraplan_rows(draft_id, rows=[{row_key, project_ids, note}, …])`.
Die `note` sagt in einem Satz, warum („Teilprojekt Abschnitt 9.2, Name und Strecke
stimmen“). Fehler kommen je Zeile zurück — nur die fehlgeschlagenen neu senden.

**Aliase pflegen:** Zeigt eine Zeile eine Deutschlandtakt-Nummer („DT 38“) und hast du
das Projekt sicher gefunden, das Alias mit `update_project(id, {"aliases": [...]})`
ergänzen (bestehende Aliase mitsenden, die Liste wird ersetzt) — im nächsten Jahr ist
der Treffer dann sicher. D-Nummern des Dashboards sind nicht die DT-Nummern des
Infraplans; nie aus der Nummer allein schließen.

## 5. Bestätigen

`confirm_infraplan_import(draft_id, published_on)` mit dem Veröffentlichungsdatum vom
Titelblatt (Infraplan 2026: 2026-10-06). Es datiert die Aussagen zum Planungsstand.
Danach fließen die Zeilen in Phase, Planfeststellung, parlamentarische Befassung,
Prognose (geplante Inbetriebnahme) und Kosten ein. Nacharbeiten nach der Bestätigung
gehen mit denselben Sammel-Tools.

## 6. Kennzahlen

`list_infraplan_drafts` nennt unter `kpi_pages` die Seiten mit Kennzahl-Diagrammen,
`list_infraplan_kpis` die Kennzahlen mit stabilem `key`.

1. **Zuerst der Text:** `suggest_infraplan_kpi_values(draft_id, page)` ordnet die
   beschrifteten Werte über die x-Position den Jahren der Achse zu (`values`). Zum
   Nachsehen gibt `get_infraplan_page_text(draft_id, page)` die Zeilen mit
   Positionen (`"<top>: wert@x …"`) — ein Wert steht über seinem Jahr.
2. `kind_guess` ist geraten (vor dem Planjahr IST, ab dann ZIEL) — mit der Legende im
   Text prüfen. **Nullwerte sind nicht beschriftet:** `missing` sind Jahre ohne
   Beschriftung — bei sichtbarem leeren Balken 0, ohne Balken weglassen.
3. **Bild nur, wenn der Text nicht reicht:** gestapelte Balken (`stacked`), keine
   Jahresachse im Text, Farben. Dann `get_infraplan_page_image(draft_id, page)`, bei
   kleiner Schrift `dpi=160`; gestapelte Balken als `series` je Teil.
4. **Gegenprobe** mit den Summen im Begleittext („Zwischen 2020 und 2025 wurden in
   Summe 266 Gleis-km in Betrieb genommen“). Geht die Summe nicht auf, noch einmal
   ablesen; bleibt die Abweichung, Werte trotzdem schreiben und im Bericht nennen.
5. Diagramme mit km und % sind zwei Kennzahlen (`elektrifizierungsgrad` +
   `elektrifizierungsgrad_prozent`, `etcs_strecken_km` + `etcs_ausruestungsgrad`).
6. `set_infraplan_kpi_values(year, values)` mit `source_page`. Eine Kennzahl, die die
   Liste nicht kennt, nur mit `definitions` (neuer snake_case-`key`, Name, Einheit,
   `STEUERUNG`/`INFORMATION`) anlegen.

Die Werte sind danach **ungeprüft** und erscheinen erst öffentlich, wenn ein Mensch den
Jahrgang in der Admin-Ansicht freigibt.

## 7. Bericht

Kurz und in dieser Gliederung:

- **Übernommen:** Anzahl Vorschläge (Schritt 2), davon aus dem Vorjahr.
- **Selbst entschieden:** je Zeile `row_key` → Projekt mit Begründung, angelegte
  Teilprojekte und eigenständige Projekte, ergänzte Aliase.
- **Prüfliste / offen:** Zeilen ohne Zuordnung mit dem Grund; Projekte aus dem Vorjahr
  ohne neue Zeile; Auffälligkeiten aus `check_project_data` (doppelte Nummern,
  namensgleiche Teilprojekte, GVFG-Ländercode, Teilmaßnahmen ohne Namen), soweit sie
  die Zuordnung betrafen.
- **Kennzahlen zur Freigabe:** welche Kennzahlen/Jahre geschrieben, Abweichungen bei der
  Gegenprobe, was aus dem Bild gelesen wurde, Hinweis „Admin → Infraplan → Kennzahlen
  {Jahr}“.
