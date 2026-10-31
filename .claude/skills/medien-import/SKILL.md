---
name: medien-import
description: Trägt Presse- und Medienberichte zum Planungsstand von Schienenprojekten ins Schienendashboard ein — Artikel selbst lesen, je Projekt einen Bericht mit Zitat und behaupteter Phase anlegen, zuordnen, belegte Aussagen bestätigen. Verwenden, wenn ein Artikel vorliegt oder die Presselage Meldungen zu Projekten gefunden hat, und bei „Medienbericht eintragen“, „Pressemeldung ins Dashboard“, „Presse zum Planungsstand“.
metadata:
  mcp: true
---

# Medienberichte eintragen

Presseberichte sind die schwächste Quelle des Planungsstands (Glaubwürdigkeit 0.4, sie
altern schnell). Sie lohnen sich, wenn ein Artikel einen **neuen Stand** meldet, den
noch kein Bericht abbildet: Baubeginn, Inbetriebnahme, Planfeststellung beantragt,
Vorhaben gestoppt. Du liest den Artikel selbst und schreibst über die MCP-Tools; der
Server ruft nichts ab und extrahiert nichts.

**Grundregel:** Eingetragen wird, was im Artikel steht — mit wörtlichem Zitat. Keine
Schlussfolgerung über das hinaus, was der Text sagt. Im Zweifel nicht bestätigen.

Recht: `progress.edit`.

## 1. Lohnt sich der Bericht?

1. Projekt finden: `list_projects(search=…)`, bei Teilabschnitten mit
   `superior_project_id` das passende Teilprojekt.
2. `get_project_progress(project_id)` — was sagt das Dashboard schon? Ein Artikel, der
   nur den bekannten Stand wiederholt, braucht keinen Bericht.
3. `list_media_reports(project_id=…)` bzw. `list_media_reports(search=<URL-Teil>)` —
   ist der Artikel schon drin?

Kein Bericht für Meinungsstücke, Forderungen („muss endlich gebaut werden“),
Pressemitteilungen von Parteien ohne Sachstand oder Ankündigungen ohne Termin.

## 2. Phase bestimmen

`asserted_phase` ist die Hauptphase, in der das Projekt laut Artikel **ist**:

| Formulierung (Beispiele) | Phase |
|---|---|
| „Vorplanung läuft“, „Variantenuntersuchung“, „Grundlagenermittlung“ | `VORPLANUNG` |
| „Entwurfsplanung“, „Planfeststellung beantragt/läuft“, „Genehmigungsplanung“ | `GENEHMIGUNGSPLANUNG` |
| „Spatenstich“, „Bauarbeiten haben begonnen“, „im Bau“ | `BAU` |
| „in Betrieb genommen“, „erste Züge fahren“, „eröffnet“ | `IN_BETRIEB` |

- Zukunft („soll 2027 beginnen“) ist **kein** Stand: Phase leer lassen oder den
  aktuellen Stand nehmen, wenn er dasteht. Termine gehören nicht in Medienberichte.
- „Planfeststellungsbeschluss liegt vor“ heißt noch nicht Bau — `GENEHMIGUNGSPLANUNG`.
- Stopp, Moratorium, Abbruch: keinen Bericht mit Phase, sondern dem Nutzer melden
  (Lebenszyklus setzt `set_project_lifecycle`, nur auf seine Bitte).

`observed_date`: wann der gemeldete Zustand galt, wenn der Artikel es sagt („seit
Montag“ → das Datum); sonst leer lassen (= Erscheinungsdatum).

## 3. Eintragen

`add_media_report` je Artikel **und** Projekt:

- `url`, `publication` (Name des Mediums), `published_date`,
- `quote`: der Satz bzw. die Sätze, die die Phase belegen, wörtlich,
- `project_id`, `asserted_phase`, ggf. `observed_date`,
- `raw_text` optional: der relevante Absatz.

Ein Artikel über mehrere Projekte → ein Bericht je Projekt, jeweils mit dem Zitat, das
dieses Projekt betrifft.

## 4. Bestätigen

Erst ein bestätigter Bericht mit Projekt und Phase zählt im Planungsstand.

- Direkt `confirmed: true`, wenn das Zitat die Phase eindeutig trägt und das Projekt
  sicher ist.
- Sonst unbestätigt lassen und im Bericht an den Nutzer nennen; er bestätigt in der
  Oberfläche oder sagt es dir (`update_media_report(report_id, confirmed=true)`).
- Danach `get_project_progress` prüfen: Steht die MEDIEN-Beobachtung da, und widerspricht
  sie neueren, glaubwürdigeren Quellen (Rücksprung)? Dann den Bericht wieder
  zurücknehmen (`confirmed: false`) und den Widerspruch melden — eine Pressemeldung
  überstimmt keinen VIB.

Korrekturen mit `update_media_report` (Projekt wechseln, `clear_project`,
`clear_phase`), Fehleinträge mit `delete_media_report`.

## 5. Bericht an den Nutzer

- **Eingetragen:** je Bericht Projekt, Medium, Datum, Phase, bestätigt ja/nein.
- **Nicht eingetragen:** Artikel ohne neuen Stand oder ohne belastbare Aussage, kurz warum.
- **Auffällig:** Widersprüche zum Planungsstand, Stopps, fehlende Projekte.
