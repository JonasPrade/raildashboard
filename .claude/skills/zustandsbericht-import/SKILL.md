---
name: zustandsbericht-import
description: Liest einen InfraGO-Zustandsbericht (DB InfraGO, Netz und Personenbahnhöfe) per MCP ins Schienendashboard ein — Jahrgang anlegen, Anhangtabellen (Gesamtnetz, Hochleistungsnetz, Personenbahnhöfe), Flächennetz/Serviceeinrichtungen, Kennzahlenvergleich und Länderwerte tabellenweise schreiben, Prüfungen bestehen, Bericht für die Freigabe. Verwenden, wenn der Nutzer sagt „Zustandsbericht einlesen“, „Netzzustandsbericht 20xx nachtragen“, „Netzzustand aktualisieren“.
metadata:
  mcp: true
---

# InfraGO-Zustandsbericht einlesen

Die DB InfraGO bewertet jährlich den Zustand von Fahrweg und Personenbahnhöfen mit Noten
von 1 (neuwertig) bis 6 (einschränkend), gewichtet nach Wiederbeschaffungswert (WBW).
Bis 2023 hieß der Bericht „Netzzustandsbericht“ (DB Netz), seit 2024 „InfraGO-Zustandsbericht“
mit Personenbahnhöfen. Du überträgst seine Zahlen tabellenweise; der Server prüft jede
Tabelle, ein Mensch gibt den Jahrgang danach frei. Alle Tools brauchen `condition.import`.

**Grundregel:** Nur übertragen, was gedruckt dasteht. Nichts schätzen, nichts aus
Prozenten zurückrechnen, nichts aus einem anderen Jahrgang auffüllen. Was nicht ablesbar
ist, bleibt leer und kommt in deinen Bericht.

## 1. Jahrgang anlegen

1. `list_condition_reports` — gibt es den Jahrgang schon? Ist er `FREIGEGEBEN`, nichts
   schreiben; Korrekturen macht ein Mensch in der Admin-Ansicht.
2. Sonst `create_condition_report(year, title, source_url, price_basis)` — `price_basis`
   steht in den Fußnoten des Anhangs („Preisstand 2024“).
3. Ohne gespeichertes PDF (`has_pdf` false) gehen `get_condition_page_text`/`_image`
   nicht: den Nutzer bitten, das PDF unter Admin → Zustandsbericht hochzuladen, oder das
   PDF lesen, das er dir selbst gibt.
4. `list_condition_classes` — Schlüssel der Anlagenklassen, erlaubte Kennzahlen, Netze,
   Länderkürzel.

## 2. Wo was steht (Jahrgang 2025, PDF-Seiten)

Das PDF druckt zwei Berichtsseiten auf eine PDF-Seite; `page` ist immer die PDF-Seite.

| Tabelle | PDF-Seite | domain / scope |
|---|---|---|
| Kennzahlenvergleich (Vorjahr / Berichtsjahr) | 4 | Summen: Netzzustandsnote, Note HLN, Note FLN, Erneuerungsbedarf Mrd. €; Personenbahnhöfe: Note, Note Empfangsgebäude, Nachholbedarf |
| Netzzustandsnote seit 2021 (Abb. 3) | 7 | FAHRWEG GESAMT, NOTE je `reference_year` |
| Tab. 5 Gesamtnetz | 27 links | FAHRWEG GESAMT |
| Tab. 6 Hochleistungsnetz | 27 rechts | FAHRWEG HLN |
| Abb. 7 Flächennetz, Abb. 8 Serviceeinrichtungen | 9 | FAHRWEG FLN / SE: nur NOTE und WBW_BEWERTET je Klasse |
| Tab. 7 Personenbahnhöfe | 28 | PERSONENBAHNHOF GESAMT |
| Abb. 31 Länder | 29 | FAHRWEG LAND und PERSONENBAHNHOF LAND, NOTE je Land |

Ältere Jahrgänge haben ein anderes Layout und weniger Klassen (Lärmschutzbauwerke,
Durchlässe, Weichenheizanlagen erst seit 2024; Serviceeinrichtungen erst 2025). Erst das
Inhaltsverzeichnis lesen, dann die Tabellen suchen. Klassen, die fehlen, einfach weglassen.

## 3. Lesen

- Tabellen mit `get_condition_page_text`: jede Zeile `"<top>: wort@x …"`; Spalten stehen
  untereinander auf gleichem x. Erst die Kopfzeile den Klassen zuordnen, dann jede
  Kennzahlzeile Spalte für Spalte. Deutsche Zahlen: „1.434“ = 1434, „2,17“ = 2.17.
- Diagramme und Karte mit `get_condition_page_image` (dpi 150–200 bei kleiner Schrift).
- Zeilen der Anhangtabellen → Kennzahlen:

| Zeile im Bericht | metric | grade |
|---|---|---|
| WBW | `WBW` | – |
| Bewerteter WBW | `WBW_BEWERTET` | – |
| Bewertetes Anlagenportfolio nach WBW in Prozent | `WBW_ANTEIL` | – |
| Note | `NOTE` | – |
| Notenverteilung … [%] 1–6 | `VERTEILUNG_WBW` | 1–6 |
| Bewertetes Anlagenportfolio nach Mengen | `MENGE_BEWERTET` | – |
| Gesamtportfolio Mengen | `MENGE_GESAMT` | – |
| Notenverteilung (Mengen) 1–6 | `VERTEILUNG_MENGE` | 1–6 |
| Zustandsbasierter Erneuerungsbedarf (Mengen) | `ERNEUERUNGSBEDARF_MENGE` | – |
| Zustandsbasierter Erneuerungsbedarf Mrd. € (Summe) | `ERNEUERUNGSBEDARF_MRD` | – |
| Zustandsbasierter Nachholbedarf Mrd. € (Bahnhöfe) | `NACHHOLBEDARF_MRD` | – |

- Die Spalte „Gesamt“ ist die Summe: `class_key` weglassen.
- Die sechste Notenzeile ohne Beschriftung ist Note 6 (einschränkend).
- Vorjahreswerte (Kennzahlenvergleich, Abb. 3) mit `reference_year` des Vorjahres in
  dieselbe Tabelle schreiben.
- Empfangsgebäude stehen nicht in Tab. 7; ihre Note aus dem Kennzahlenvergleich mit
  `class_key` `pb_empfangsgebaeude`.

## 4. Schreiben

Eine Tabelle je Aufruf: `set_condition_values(year, domain, scope, values, region?)`,
`source_page` und `source_ref` („Tab. 5“) an jedem Wert. Länder: je Land und Bereich ein
Aufruf mit `scope` LAND und `region` (Kürzel aus `list_condition_classes`).

Der Server prüft die Tabelle zusammen mit dem, was schon gespeichert ist:
Notenverteilung = 100 %, Mengen je Note = bewertete Menge, Noten 4–6 = Erneuerungsbedarf,
Anlagenklassen = Summe. **Schlägt die Prüfung fehl, ist nichts geschrieben.** Dann:

1. Die genannte Klasse auf der Seite noch einmal lesen (Bild, wenn der Text mehrdeutig ist).
   Meist ist eine Spalte verrutscht oder eine Ziffer verlesen.
2. Steht die Zahl genau so im Bericht und der Bericht selbst geht nicht auf (Beispiel 2025:
   Stellwerke Gesamtnetz, Mengen je Note 3.461, bewertete Menge 3.686), denselben Aufruf mit
   `override_reason` wiederholen: Seite, Tabelle, welche Zahlen nicht zusammenpassen. Der
   Grund steht danach am Jahrgang und in der Freigabe-Ansicht.

Nie `override_reason` nehmen, um einen eigenen Lesefehler durchzudrücken.

## 5. Abschließen

1. `check_condition_report(year)` — keine `errors` mehr; `gaps` erklären (fehlt die Tabelle
   im Bericht, oder hast du sie übersehen?).
2. Den Jahrgang **nicht** freigeben — das kann nur ein Mensch (Admin → Zustandsbericht →
   Jahrgang → „Freigeben“). Werte bleiben bis dahin unsichtbar.
3. Bericht an den Nutzer: Tabellen geschrieben (Anzahl Werte), angenommene Abweichungen mit
   Grund, Lücken, alles Unsichere mit Seite.

## Ältere Jahrgänge (2021–2024)

- Ein Jahrgang je Durchgang, ältester zuerst; jeweils eigener `create_condition_report`.
- Die Netzzustandsberichte 2021–2023 zeigen den Fahrweg ohne Personenbahnhöfe. Fehlt eine
  Klasse, weglassen; Anlagenklassen umbenannter Gewerke nur nach Rückfrage neu anlegen
  (`create_condition_class` mit `reason`).
- Werte, die ein späterer Bericht für dasselbe Jahr nennt (Kennzahlenvergleich), gewinnen
  auf der Seite automatisch — nichts angleichen.
