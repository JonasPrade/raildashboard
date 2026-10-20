---
name: infraplan-import
description: Führt einen im Frontend hochgeladenen Infraplan (Fünfjahresplan des Bundes für die Schiene) per MCP bis zur Bestätigung — sichere Vorschläge übernehmen, offene Zeilen begründet Projekten oder neuen Teilprojekten zuordnen, Jahrgang bestätigen, Kennzahlen aus den Diagrammen ablesen. Verwenden, wenn der Nutzer sagt „Infraplan einlesen“, „Infraplan 20xx zuordnen“, „Infraplan-Kennzahlen eintragen“.
metadata:
  mcp: true
---

# Infraplan einlesen

Der Infraplan erscheint jährlich (Infraplan 2026 = 2026–2030). Seine Maßnahmentabellen
(Kap. 2.3: Bedarfsplan Teil A–D, GVFG Kat. A/C, InvKG) liefern je Zeile
Realisierungsstand, geplante Inbetriebnahme, Kosten und parlamentarische Befassung. Das
Dashboard hat das PDF schon ausgelesen; du ordnest die Zeilen Projekten zu, bestätigst
den Jahrgang und trägst die Kennzahlen ein. Alle Tools brauchen das Recht
`infraplan.import`.

**Grundregel:** Zuordnen nur mit Begründung, im Zweifel offen lassen. Eine offene Zeile
kostet nichts — sie landet unter „Offene Zuordnungen“. Eine falsche Zuordnung verfälscht
Planungsstand, Prognose und Kosten des Projekts.

## 1. Entwurf holen

1. `list_infraplan_drafts` — den neuesten Entwurf des gewünschten Jahrgangs nehmen
   (`status` = `SUCCESS`). Steht `status` auf `PENDING`/`RUNNING`, kurz warten und neu
   abfragen; bei `FAILURE` den `error` berichten und aufhören.
2. **Hat der Entwurf `warnings`: anhalten.** Melde jede Warnung (Lücke oder Dublette in
   den laufenden Nummern, unaufgelöster Kostenverweis, fehlender Abschnitt, unlesbare
   Zeichen, nicht lesbare Kostenangabe) und frag,
   wie es weitergehen soll. Bestätigen kann ihn dann nur ein Mensch im Frontend.
   `start_infraplan_parse` liest das PDF neu aus, wenn der Nutzer das will.
3. Ist der Jahrgang unter `years` schon übernommen, nicht neu bestätigen — nur offene
   Zeilen nachtragen (siehe 4) und die Kennzahlen prüfen.

## 2. Sichere Vorschläge übernehmen

`apply_infraplan_suggestions(draft_id)` mit der Voreinstellung 0.85. Das übernimmt
Treffer über die Projektnummer aus dem Vorjahr (`NUMBER`), über den GVFG-Schlüssel
(`GVFG_KEY`) und sehr ähnliche Namen (`FUZZY` ≥ 0.85). Die Schwelle nur senken, wenn der
Nutzer es sagt.

## 3. Vorjahresabgleich

`get_infraplan_draft(draft_id)` liefert `missing_from_previous`: Projekte, die im
Vorjahr eine Zeile hatten und jetzt keine. Meist ist die Maßnahme umbenannt oder
zusammengelegt — such die neue Zeile (Strecke, Bundesland, Projektnummer) und ordne sie
dem Projekt zu. Ist sie wirklich entfallen, im Bericht nennen.

## 4. Offene Zeilen einzeln zuordnen

`get_infraplan_draft(draft_id, only_open=true, section=…)` abschnittsweise
durchgehen. Für jede Zeile:

1. Kandidaten: die `suggestions` der Zeile, dann `list_projects` mit Begriffen aus
   `bezeichnung` und `massnahme` (Orte, Strecke, „PB 07“ ohne Präfix), Bundesland aus
   `laender`. Bei GVFG-Zeilen den Schlüssel (`primary_number`, z. B. `07 D 2825_A`) in
   `project_number` suchen.
2. **Teilprojekt vor Elternprojekt:** Beschreibt die Zeile einen Abschnitt
   („Abschnitt 9.2“, „2gl. Einbindung Bf Stendal“) und gibt es dafür ein Teilprojekt,
   das Teilprojekt nehmen. `get_project` zeigt die Teilprojekte.
3. Fehlt das Teilprojekt, aber das Elternprojekt ist eindeutig:
   `create_infraplan_subproject(draft_id, row_key, parent_id)` — legt es als Entwurf
   ohne Geometrie an und ordnet zu.
4. Sonst `assign_infraplan_row(draft_id, row_key, project_ids, note)`. Die `note` sagt
   in einem Satz, warum (z. B. „Name und Strecke stimmen, Teilprojekt Abschnitt 2“).
   Eine Zeile darf mehreren Projekten gehören (Sammel-GWU, Fußnote „bezieht sich auf
   Teil A 20 und Teil A 33“), mehrere Zeilen einem Projekt.
5. Wirklich unklar → offen lassen und im Bericht aufführen.

Kostenverweise (`cost_ref_raw`, „Ref. Teil B 20“) und Fußnoten brauchen nichts — das
Dashboard zählt Sammelkosten nur einmal.

## 5. Bestätigen

`confirm_infraplan_import(draft_id, published_on)` mit dem Veröffentlichungsdatum vom
Titelblatt (Infraplan 2026: 2026-10-06). Es datiert die Aussagen zum Planungsstand.
Danach fließen die Zeilen in Phase, Planfeststellung, parlamentarische Befassung,
Prognose (geplante Inbetriebnahme) und Kosten ein. Korrekturen nach der Bestätigung
gehen mit demselben `assign_infraplan_row`.

## 6. Kennzahlen

`list_infraplan_drafts` nennt unter `kpi_pages` die Seiten mit Kennzahl-Diagrammen,
`list_infraplan_kpis` die Kennzahlen mit stabilem `key`.

1. Je Seite `get_infraplan_page_image(draft_id, page)`; bei kleiner Schrift `dpi=160`.
2. Ablesen: je Balken/Punkt Jahr, Art (`IST` = Rückschau, `ZIEL` = Zielwert), Wert;
   gestapelte Balken (z. B. KMM nach Teilprogrammen) als `series` je Teil. **Nullwerte
   sind im Diagramm nicht beschriftet** — eine fehlende Beschriftung bei sichtbarem
   leeren Balken ist 0, ohne Balken lässt du den Wert weg.
3. Gegenprobe mit den Summen im Begleittext („Zwischen 2020 und 2025 wurden in Summe
   266 Gleis-km in Betrieb genommen“). Geht die Summe nicht auf, noch einmal ablesen;
   bleibt die Abweichung, Werte trotzdem schreiben und im Bericht nennen.
4. `set_infraplan_kpi_values(year, values)` mit `source_page`. Eine Kennzahl, die die
   Liste nicht kennt, nur mit `definitions` (neuer snake_case-`key`, Name, Einheit,
   `STEUERUNG`/`INFORMATION`) anlegen.

Die Werte sind danach **ungeprüft** und erscheinen erst öffentlich, wenn ein Mensch den
Jahrgang in der Admin-Ansicht freigibt.

## 7. Bericht

Kurz und in dieser Gliederung:

- **Übernommen:** Anzahl Vorschläge (Schritt 2).
- **Selbst entschieden:** je Zeile `row_key` → Projekt mit Begründung, angelegte
  Teilprojekte.
- **Offen:** Zeilen ohne Zuordnung mit dem Grund; Projekte aus dem Vorjahr ohne neue
  Zeile.
- **Kennzahlen zur Freigabe:** welche Kennzahlen/Jahre geschrieben, Abweichungen bei der
  Gegenprobe, Link-Hinweis „Admin → Infraplan → Kennzahlen {Jahr}“.
