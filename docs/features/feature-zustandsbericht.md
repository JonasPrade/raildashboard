# Feature: InfraGO-Zustandsbericht — Netzzustand über MCP + Skill

> **Status: umgesetzt** (2026-10-30, #330) — Stufen 1–4. Stufe 5 (Altjahrgänge 2021–2024) und das
> Einlesen des Jahrgangs 2025 sind Datenarbeit nach dem Deploy (Agent + Skill, Freigabe durch einen
> Menschen). Entscheidungen EK 1–4 siehe [Entscheidungen](#entscheidungen).
> Prototyp der Darstellung: `docs/features/zustandsbericht/prototyp.html`
> (veröffentlicht als Artefakt https://claude.ai/artifact/6xqhcvrA65hb8B1TJMHyBE), gefüllt mit
> den echten Werten des Berichts 2025.

## Kontext / Ziel

Die DB InfraGO veröffentlicht jährlich den **InfraGO-Zustandsbericht** (bis 2023
„Netzzustandsbericht“, seit 2024 mit Personenbahnhöfen). Er bewertet den Zustand von Fahrweg
und Personenbahnhöfen mit Noten von 1 (neuwertig) bis 6 (einschränkend), gewichtet nach
Wiederbeschaffungswert (WBW), und leitet daraus den zustandsbasierten Erneuerungs- bzw.
Nachholbedarf ab. Ziel: alle Kennzahlen des Berichts als Zeitreihe ins Dashboard holen und auf
einer öffentlichen Seite **„Netzzustand“** zeigen.

Quelle 2025: https://www.dbinfrago.com/resource/blob/13867300/20add12224f2c4eb00394670fc5f8be8/InfraGO-Zustandsbericht_2025-data.pdf
(31 PDF-Seiten = Druckseiten 1–58, Textebene vorhanden).

## Was der Bericht enthält (Jahrgang 2025)

| Ort | Inhalt | Form | Wert für uns |
|---|---|---|---|
| S. 6, Kennzahlenvergleich | Netzzustandsnote, Note HLN, Note FLN, Erneuerungsbedarf (Mrd. €), Note Personenbahnhöfe, Note Empfangsgebäude, Nachholbedarf (Mrd. €) — je 2024 und 2025 | Tabelle (Text) | Kopfkennzahlen |
| S. 8–11, Abb. 1–3 | Anlagenportfolio, WBW im Erneuerungsbedarf je Anlagenklasse, Netzzustandsnote 2021–2025 mit Notenverteilung | Diagramme | Verlauf |
| S. 14–17, Abb. 4–8 | Note und Verteilung HLN, FLN, Serviceeinrichtungen (SE); je Anlagenklasse für FLN und SE | Diagramme (Werte als Beschriftung im Text) | FLN/SE je Klasse (nur Note + WBW) |
| **S. 52–53, Tab. 5/6** | **Schlüsselkennzahlen Fahrweg — Gesamtnetz und Hochleistungsnetz**: je Anlagenklasse WBW, bewerteter WBW, Anteil WBW, Note, Notenverteilung 1–6 in % (WBW) und in Mengen, bewertete Menge, Gesamtmenge, Einheit, zustandsbasierter Erneuerungsbedarf (Menge) | Tabelle (Text) | Kern |
| **S. 54–55, Tab. 7** | **Schlüsselkennzahlen Personenbahnhöfe**: je Anlagenklasse WBW, Anteil, Note, Verteilung % und Mengen, Nachholbedarf (Mrd. €) | Tabelle (Text) | Kern |
| **S. 56–57, Abb. 31–33** | **Zustandsnote Fahrweg und Personenbahnhöfe je Bundesland**; Notenverteilung je Land | Karte + Balken (Bild; Noten als Text lesbar, Verteilungen nur im Bild) | Länder |

Anlagenklassen Fahrweg (11, in vier Gewerken): KIB — Brücken, Tunnel, Stützbauwerke,
Durchlässe, Lärmschutzbauwerke · OB — Gleise, Weichen · LST — Bahnübergänge, Stellwerke ·
ET — Oberleitung, Weichenheizanlagen. Personenbahnhöfe (9 + Empfangsgebäude): Bahnsteige,
Personenunterführungen, unterirdische Personenverkehrsanlagen, Treppen/Rampen/Wetterschutz,
Bahnsteigdächer, Bahnsteighallen, Personenaufzüge, ITK-Anlagen, Fahrtreppen.

Ältere Jahrgänge (2021–2024) haben ein anderes Layout und teils andere Klassen (Lärmschutz,
Durchlässe, Weichenheizanlagen erst „seit 2024 integriert“; SE erst 2025 eigenes Segment).
Werte, die es in einem Jahrgang nicht gibt, bleiben leer — keine Rückrechnung.

## Scope

**In scope (Phase 1):**

1. Datenmodell für Bericht, Anlagenklassen und Werte (Langformat, siehe unten).
2. MCP-Tools + Skill `zustandsbericht-import` (EK 1): Agent liest PDF und Seitenbilder,
   schreibt Werte, Server prüft Summen, Status `UNGEPRUEFT` bis zur Freigabe.
3. Jahrgang 2025 vollständig: Kennzahlenvergleich, Tab. 5–7, FLN/SE je Klasse (Note + WBW),
   Bundesländer (Noten Fahrweg und Personenbahnhöfe) (EK 2).
4. Altjahrgänge 2021–2024 nachtragen (EK 2), soweit die Berichte die Werte enthalten.
5. Öffentliche Seite `/netzzustand` mit eigenem Navigationspunkt (EK 3), wie im Prototyp.
6. Admin-Ansicht zur Freigabe (Werte neben Seitenbild, „Jahrgang freigeben“).

**Out of scope:** Bezug auf einzelne Projekte (der Bericht nennt keine Strecken); Landesnote
auf Wahlkreis-/Abgeordnetenseiten (später möglich, EK 3 verworfen für Phase 1);
Korridorsanierungs-/Generalsanierungs-Texte; Upload-Parser (EK 1 verworfen).

## Datenmodell

**`condition_report`** — ein Jahrgang
- `year` (unique), `title`, `source_url`, `published_at`, `pdf_path` (gespeicherte Datei,
  analog `INFRAPLAN_PDF_DIR`), `price_basis` (z. B. „Preisstand 2024“), `note`,
  `status` (`ENTWURF` | `FREIGEGEBEN`), `created_at`, `released_at`, `released_by_snapshot`

**`condition_asset_class`** — Anlagenklasse, jahrgangsübergreifend
- `key` (stabil, z. B. `fw_stellwerke`, `pb_bahnsteige`), `domain` (`FAHRWEG` | `PERSONENBAHNHOF`),
  `trade` (`KIB` | `OB` | `LST` | `ET` | NULL), `name`, `unit` (`Stk.` | `km`), `sort_order`,
  `description`, `first_year`
- Seed aus `services/condition_classes.py`; neue Klassen legt der Agent nur über ein Tool mit
  Begründung an.

**`condition_value`** — ein Wert (Langformat, wie `infraplan_kpi_value`)
- `report_id` (FK, CASCADE), `domain`, `scope` (`GESAMT` | `HLN` | `FLN` | `SE` | `LAND`),
  `region` (Länderkürzel bei `LAND`, sonst NULL), `asset_class_id` (NULL = Summe des Scopes),
  `metric` (siehe unten), `grade` (1–6 bei Verteilungen, sonst NULL), `value` (Numeric),
  `reference_year` (Bezugsjahr; Vorjahreswerte aus dem Kennzahlenvergleich tragen das Vorjahr),
  `source_page`, `source_ref` („Tab. 5“, „Abb. 31“), `status` (`UNGEPRUEFT` | `GEPRUEFT`),
  `entered_by_snapshot`, `created_at`
- Unique `(report_id, domain, scope, region, asset_class_id, metric, grade, reference_year)`
  (NULL-sicher über `COALESCE`-Index)

`metric`-Werte: `WBW` (Mrd. €), `WBW_BEWERTET`, `WBW_ANTEIL` (%), `NOTE`, `VERTEILUNG_WBW`
(% je `grade`), `VERTEILUNG_MENGE` (je `grade`), `MENGE_BEWERTET`, `MENGE_GESAMT`,
`ERNEUERUNGSBEDARF_MENGE`, `ERNEUERUNGSBEDARF_MRD` (Fahrweg) bzw. `NACHHOLBEDARF_MRD`
(Personenbahnhöfe).

Warum ein eigenes Modell statt `infraplan_kpi`: Der Zustandsbericht hat fünf Achsen
(Bereich × Netz/Land × Anlagenklasse × Kennzahl × Note), die Infraplan-Kennzahl nur zwei
(Kennzahl × Teilreihe). Die Teilreihe als zusammengesetzter String würde Abfragen und die
Summenprüfung unlesbar machen. Das Muster (Langformat, Status, Freigabe) übernehmen wir.

## Import über MCP + Skill

### Ablauf (Skill `.claude/skills/zustandsbericht-import/SKILL.md`, `metadata: mcp: true`)

1. Nutzer lädt das PDF im Admin hoch (`POST /import/condition/report`, speichert nur die Datei
   und erzeugt Seitenbilder bei Bedarf) **oder** nennt dem Agenten die URL; der Agent legt den
   Jahrgang mit `create_condition_report` an (gleiches Jahr → Fehler mit Verweis).
2. Agent liest Seitentext (`get_condition_page_text`) und bei Diagrammen das Seitenbild
   (`get_condition_page_image`), Muster `get_infraplan_page_*`.
3. Je Tabelle ein Aufruf `set_condition_values(report_id, domain, scope, values[])` — eine
   Tabelle auf einmal, damit der Server die Summen prüfen kann.
4. Server prüft je Anlagenklasse und Scope und lehnt den ganzen Aufruf mit Fehlerliste ab:
   - Notenverteilung in % summiert auf 100 ± 0,2;
   - Notenverteilung in Mengen summiert auf `MENGE_BEWERTET` (± 0);
   - Summe der Klassen-WBW = Gesamt-WBW ± 0,3 Mrd. €;
   - `MENGE_BEWERTET` ≤ `MENGE_GESAMT`; Note in [1, 6];
   - Noten 4–6 (Mengen) = `ERNEUERUNGSBEDARF_MENGE`;
   - kein Abgleich Note ↔ gewichtetes Mittel der Verteilung: die DB rechnet auf
     Einzelanlagenebene mit stetigen Noten, die Abweichung ist groß (Brücken 2025: 2,64
     gegen 2,16).
   Toleranzen: Prozent ± 0,3, Mengen ± max(2; 0,2 %), Mrd. € ± max(0,3; 0,2 %).
   Empfangsgebäude zählen nicht in die Summen (Tab. 7 schließt sie aus).
   **Der Bericht 2025 selbst geht an einer Stelle nicht auf:** Stellwerke im Gesamtnetz
   (Tab. 5) — Mengen je Note 45 + 348 + 1.042 + 1.280 + 707 + 39 = 3.461, bewertete Menge
   3.686. Diese Tabelle geht nur mit `override_reason` durch.
5. Bundesländer: Noten aus Abb. 31 (Text), Verteilungen je Land aus Abb. 32/33 nur, wenn
   ablesbar — sonst weglassen (kein Schätzen).
6. Agent meldet: geschrieben / Warnungen / nicht ablesbar. **Kein Freigeben durch den Agenten**
   — die Freigabe macht ein Mensch in der Admin-Ansicht (wie Infraplan-Kennzahlen, Grundsatz
   „KI-Werte öffentlich erst nach Freigabe“).

Zahlen laufen hier durch ein LLM, obwohl `feature-pdf-import-unification.md` für den Haushalt
davon abrät. Der Unterschied: ~700 Werte statt ~11.000, jede Tabelle hat innere Summen, die der
Server prüft, und der Mensch gibt neben dem Seitenbild frei. Für die Altjahrgänge mit wechselndem
Layout wäre ein Parser je Jahrgang teurer als der Prüfaufwand (EK 1).

### MCP-Tools

Modul `mcp/tools/condition.py`; Recht `condition.import` (Gruppe „Inhalte“), an die
Editor-Systemrolle vergeben. Die Tools adressieren den Jahrgang über `year`.

| Tool | Art | Zweck |
|---|---|---|
| `list_condition_reports` | lesend | Jahrgänge mit Status, Zählern (Werte gesamt/ungeprüft) |
| `create_condition_report(year, title, source_url, …)` | schreibend | Jahrgang anlegen |
| `get_condition_page_text(year, page)` / `get_condition_page_image(year, page)` | lesend | Seite als Text (Layout wie beim Infraplan) bzw. Bild |
| `list_condition_classes(domain?)` | lesend | Anlagenklassen mit Schlüssel, Einheit, Gewerk |
| `create_condition_class(key, domain, …, reason)` | schreibend | neue Klasse (nur mit Begründung) |
| `set_condition_values(year, domain, scope, values[], region?, override_reason?)` | schreibend | Werte einer Tabelle setzen (ersetzt gleiche Schlüssel, `value: null` entfernt), Summenprüfung zusammen mit dem Gespeicherten; schlägt sie fehl, wird nichts geschrieben — außer mit `override_reason`, wenn der gedruckte Bericht selbst nicht aufgeht (steht dann in `accepted_mismatches` am Jahrgang) |
| `get_condition_values(year, domain?, scope?, metric?)` | lesend | Werte lesen, z. B. für den Abgleich mit dem Vorjahr |
| `check_condition_report(year)` | lesend | alle Prüfungen über den Jahrgang, angenommene Abweichungen, Lücken |

### REST-API

- öffentlich, Prefix `/api/v1/condition`: `GET /reports` (nur freigegebene),
  `GET /reports/{year}` (Bericht, Anlagenklassen, Werte mit `GEPRUEFT`), `GET /series`
  (Noten, Erneuerungs-/Nachholbedarf und bewerteter WBW aller freigegebenen Jahrgänge; je
  Bezugsjahr gewinnt der neueste Bericht)
- `condition.import`, Prefix `/api/v1/import/condition`: `GET|POST /reports`,
  `POST /reports/{year}/pdf`, `GET /reports/{year}/page/{page}.png`,
  `GET /reports/{year}/values`, `GET /reports/{year}/check`, `GET /classes`,
  `PATCH|DELETE /values/{id}` (Korrektur gilt als geprüft; gebrochene Summen kommen als
  Warnung zurück), `POST /reports/{year}/release`, `DELETE /reports/{year}`

Admin-Ansichten: `/admin/zustandsbericht` (Jahrgang anlegen, PDF hochladen) und
`/admin/zustandsbericht/{year}` (Prüfung, angenommene Abweichungen, Lücken; Werte je Tabelle
neben dem Seitenbild, korrigieren, freigeben, löschen).

`CONDITION_PDF_DIR` (Standard `/app/uploads/zustandsbericht`, im `uploads`-Volume) ist neue
harte Abhängigkeit und wird von `/healthz` auf Schreibbarkeit geprüft.

## Darstellung `/netzzustand` (EK 3)

Aufbau wie im Prototyp:

1. **Kopf:** Titel „Netzzustand“ mit Info-Symbol, Jahrgang-Auswahl (ab zwei Jahrgängen,
   `?jahr=`), Umschalter **Fahrweg | Personenbahnhöfe** (in der URL, `?bereich=bahnhoefe`).
2. **Kennzahlband** (4 Kacheln): Fahrweg — Netzzustandsnote (einzige Hervorhebungszahl),
   Erneuerungsbedarf Mrd. €, Note HLN, Note FLN; Personenbahnhöfe — Note, Nachholbedarf,
   Note Empfangsgebäude, bewertete Anlagen. Jeweils Vorjahreswert und Differenz.
3. **Entwicklung:** Linien der Netzzustandsnote (ab 2021) und Personenbahnhöfe (ab 2023);
   daneben Notenverteilung je Netz als 100-%-Balken.
4. **Anlagenklassen:** Netz-Umschalter Gesamtnetz | HLN | FLN | SE; je Klasse Zeile mit
   Gewerk, Note, Verteilungsbalken (nach WBW), WBW mit Mengenbalken, Erneuerungsbedarf
   (Menge + Einheit) bzw. Nachholbedarf (Mrd. €). Sortierbar (Note, WBW, Name). Klick →
   Detail mit Mengen je Note und Bestand/bewertet. FLN/SE ohne Verteilung (nicht im Anhang)
   mit Hinweis. Ab dem zweiten Jahrgang nennt das Detail die Vorjahresnote der Klasse
   mit Differenz (aus `/series`); ein Verlaufsdiagramm je Klasse kommt mit Stufe 5, wenn die
   Altjahrgänge eingelesen sind.
5. **Bundesländer:** Kachelkarte (16 Kacheln in geografischer Lage) gefärbt nach Abstand zum
   Bundesschnitt, daneben Rangliste mit Schnitt-Markierung; Umschalter Fahrweg |
   Personenbahnhöfe. Mobil untereinander.
6. **Quellenzeile:** Bericht, Tabellen, Seiten; nur freigegebene Werte.

Mobil (360 px): Zeilen der Anlagenklassen stapeln (Name + Note, Balken, WBW + Bedarf),
Kennzahlband zweispaltig, Detailtabelle scrollt in sich (`ResponsiveTable`).

**Notenfarben (EK 4):** Noten 1–6 in der Abweichungsskala der Datenviz-Palette
(`diverge-pos` → `diverge-mid` → `diverge-neg`, Note 6 dunkler als 5), festgelegt in
`semanticColors.ts` als `conditionGrade`. Ausnahme zu `docs/DESIGN.md` Regel 4 („Rot nur für
Versäumnis“): Noten sind Abweichung von gut nach schlecht, keine Status — als Ausnahme in
DESIGN.md eingetragen. Diagramme mit `@mantine/charts`/`recharts` (vorhanden), Kachelkarte als
eigene kleine Komponente ohne Kartenbibliothek.

## Umsetzung in Stufen

| Stufe | Inhalt |
|---|---|
| 1 | Modell + Migration (Expand), Seed der Anlagenklassen, CRUD, Prüfungen als reine Funktionen mit Tests (Werte 2025 als Testfall) |
| 2 | MCP-Tools + Skill, Upload/Seitenbild-Endpunkte, Recht `condition.import`; Jahrgang 2025 einlesen |
| 3 | Admin-Ansicht Freigabe (Werte neben Seitenbild, Werte korrigieren, freigeben) |
| 4 | Öffentliche Seite `/netzzustand` + Navigation + In-App-Doku (`DocumentationPage.tsx`) |
| 5 | Altjahrgänge 2021–2024 einlesen (Skill-Abschnitt „Ältere Layouts“), Verlauf je Anlagenklasse und Land |

## Offene Punkte

- Rechtegruppe: entschieden bei der Umsetzung — „Inhalte“ (der Bericht ist keine Finanzierung).
- Altberichte 2021–2023: Quelle und Umfang prüfen (Netzzustandsbericht der DB Netz; enthalten
  sie Länderwerte?). Klassen ohne Vorjahreswert werden markiert, nicht gefüllt.

## Entscheidungen

| # | Datum | Entscheidung | Verworfen |
|---|---|---|---|
| EK 1 | 2026-10-30 | Import per **MCP + Skill** mit serverseitiger Summenprüfung und menschlicher Freigabe | Upload-Parser; Hybrid (Parser für Anhang, MCP für Bilder) |
| EK 2 | 2026-10-30 | Umfang: **2025 vollständig** (Anhang, FLN/SE, Bundesländer) **und Altjahrgänge 2021–2024** | nur 2025; nur Anhang 2025 |
| EK 3 | 2026-10-30 | **Eigene öffentliche Seite `/netzzustand`** mit Navigationspunkt | Reiter in `/infraplan`; zusätzlich Länderbezug auf Wahlkreisseiten (später) |
| EK 4 | 2026-10-30 | Notenfarben in der **Abweichungsskala** (grün → grau → rot), Ausnahme in DESIGN.md | Teal-Rampe streng nach DESIGN.md |

## Akzeptanzkriterien

- [ ] Ein Agent liest den Bericht 2025 über die MCP-Tools vollständig ein; jede Tabelle besteht
      die Summenprüfung; der Bericht der Agenten nennt nicht Ablesbares.
- [ ] Ein falsch abgelesener Wert (z. B. Verteilung 99 %) wird vom Server mit klarer Meldung
      abgelehnt.
- [ ] Vor der Freigabe zeigt `/netzzustand` den Jahrgang nicht; nach der Freigabe alle Werte.
- [ ] Die Seite zeigt Kennzahlband, Verlauf, Anlagenklassen je Netz mit Detail und
      Bundesländer; Werte stimmen mit Tab. 5–7 und Abb. 31 überein.
- [ ] 360 px ohne horizontales Scrollen der Seite.
- [ ] Dunkelfassung lesbar; Notenfarben aus `semanticColors.ts`.
