# Feature: PDF-Import vereinheitlichen — Evaluation

> **Status: teilweise umgesetzt.** Schritte 1, 2, 4 und 5 der empfohlenen
> Reihenfolge sind implementiert (siehe *Umsetzungsstand* unten). Schritt 6 ist
> **beantwortet, nicht offen**: der Vergleichslauf gegen die echte API ist
> gelaufen und rot — der Haushalt bezieht seine Zahlen weiterhin aus pdfplumber
> (siehe *Schritt 6: Vergleich gelaufen* am Ende). Offen bleibt nur Schritt 3
> (Medien-PDF-Upload). Der Rest dieser Datei bleibt die Entscheidungsgrundlage.

## Ziel dieser Evaluation

Im VIB-Import ist seit Phase 4 eine zweistufige Pipeline etabliert: das PDF wird
zuerst per **OCR-Modell maschinenlesbar** gemacht (Mistral OCR → Markdown pro
Seite), erst danach findet die **Zuordnung auf das Zielformat** statt (Block-Splitting
+ LLM-Extraktion je Vorhaben). Diese Datei prüft die übrigen Einleseformate und
bewertet, ob und wie weit sie auf dieses System umgestellt werden sollten.

---

## Ist-Zustand: alle Einleseformate

| Quelle | Textgewinnung | Strukturierung | Semantik | Ausführung | Code |
|---|---|---|---|---|---|
| **VIB** (Verkehrsinvestitionsbericht) | Mistral OCR → Markdown, pymupdf-Fallback | TOC-verankertes Block-Splitting (Regex) | LLM je Vorhabenblock (`call_llm_json`) | Celery, 2-stufig mit Preview | `services/document_ocr.py`, `tasks/vib.py`, `tasks/vib_ai_extraction.py` |
| **Fulda-Runde** (Kleine Anfrage) | Mistral OCR (ruft `services.document_ocr` auf) | keine — Volltext in einem Stück | LLM über das ganze Dokument | Celery, einstufig | `tasks/fulda.py`, `tasks/fulda_extraction.py` |
| **Haushalt** (Anlage VWIB, Teil B) | `pdfplumber.extract_table()` je Seite, Zeilen-Rekonstruktion auf Seiten ohne Trennlinien | Segmentierung in die fünf Tabellen von Teil B + Flat-Table je Tabelle | `column_map` je Tabelle (Header → LLM → Fallback), Werte deterministisch | Celery, einstufig | `tasks/haushalt.py`, `tasks/haushalt_columns.py`, `tasks/haushalt_keys.py` |
| **Medien/Presse** | kein PDF — URL-Fetch oder Paste, HTML→Text | keine | LLM über den Volltext | synchron im Endpoint | `tasks/media_extraction.py` |
| **Bauportal** | kein PDF — öffentliche JSON-API | — | — | synchron im Endpoint | `tasks/bauportal.py` |

Gemeinsam ist allen bereits: Fuzzy-Matching auf Projekte, Human-Review vor
`confirm`, geteilte CRUD-Helfer (`crud/_importer_common.py`) und ein geteilter
LLM-Client (`services/llm.py`).

### Was tatsächlich uneinheitlich ist

1. **Zwei getrennte Textgewinnungs-Stacks.** `pdfplumber` (Haushalt) und
   Mistral-OCR/`pymupdf` (VIB, Fulda) lösen dasselbe Problem doppelt. Drei
   PDF-Libraries stehen in `requirements.txt` (`pdfplumber`, `pymupdf`, plus
   `mistralai`).
2. **Falscher Modulort.** `extract_full_pdf_text` ist die de-facto gemeinsame
   OCR-Schicht, liegt aber unter `tasks/vib_ocr.py`. `fulda_extraction.py`
   importiert quer aus einer fremden Domäne — jeder weitere PDF-Importer
   erbt diese Kopplung.
3. **Format-Heuristiken statt Schema-Mapping.** Der Haushalt-Parser kodiert das
   Spaltenlayout des 2026-PDFs als feste Indizes (`_COL_* = 0..15`) plus
   Sonderfälle (`_parse_combined_id_cell`, `_build_sv_raw_lookup`,
   `_is_erlaeuterung_continuation`). Ein anderes Jahrgangs-Layout bricht das.
   Das blockiert direkt den offenen Roadmap-Punkt *„Import der Haushaltsberichte
   2020–2025"*.
4. **Kein einheitlicher Zwischenstand.** VIB persistiert den OCR-Rohtext
   (`vib_draft_report.ocr_raw_text/ocr_status/ocr_model`) und kann nach einem
   Fehler im Post-Processing ohne erneuten OCR-Call weiterarbeiten. Haushalt
   und Fulda haben das nicht — jeder Fehlversuch ist ein kompletter Neulauf.
5. **Uneinheitliche Ausführung.** Celery (VIB, Fulda, Haushalt) vs. synchron
   (Medien, Bauportal); zweistufig mit Struktur-Preview nur beim VIB.

---

## Bewertung: Wo lohnt die Umstellung — und wo nicht

Die entscheidende Unterscheidung ist **nicht** „LLM ja/nein", sondern welche
der drei Stufen umgestellt wird:

```
Stufe 1  Textgewinnung   PDF-Bytes → Markdown/Text     (OCR-Modell)
Stufe 2  Segmentierung   Volltext → Blöcke/Zeilen      (deterministisch)
Stufe 3  Semantik        Block → Zielfelder            (LLM oder Regex)
```

**Stufe 1 ist für alle PDF-Quellen uneingeschränkt zu empfehlen.** Sie ist
verlustfrei gegenüber dem Status quo (pymupdf-Fallback existiert bereits),
kostet ~$0,20 je 100-Seiten-Import und liefert bei mehrspaltigen Layouts und
Tabellen nachweislich bessere Ergebnisse — genau der Grund, warum die
pdfplumber-Zweispaltenlogik im VIB überhaupt ersetzt wurde.

**Stufe 3 ist quellenabhängig.** Der VIB besteht aus Fließtext mit variabler
Gliederung — dort ist das LLM klar überlegen. Der Haushalt ist eine
Zahlentabelle: ~700 Zeilen × 16 Spalten in €1.000-Beträgen, die exakt
übernommen werden müssen. Ein Transpositions- oder Halluzinationsfehler in
einer Kostenspalte ist im Review praktisch nicht auffindbar, weil der Reviewer
keine Vergleichsgröße hat. **Zahlenwerte gehören nicht durch ein LLM.**

### Empfehlung je Quelle

| Quelle | Stufe 1 (OCR) | Stufe 3 (LLM) | Bewertung |
|---|---|---|---|
| VIB | bereits | bereits | Referenzimplementierung — nur Modul verschieben |
| Fulda | bereits | bereits | nur Import-Pfad korrigieren (`services/` statt `tasks/vib_ocr`) |
| Medien | **neu: PDF-Upload ermöglichen** | bereits | kleiner Zugewinn: Pressemitteilungen als PDF |
| Haushalt | **ja, mit pdfplumber als Fallback** | **nein für Werte, ja für das Spalten-Mapping** | siehe unten |
| Bauportal | entfällt (JSON-API) | entfällt | unverändert |

### Der Haushalt-Sonderweg: LLM für das Mapping, nicht für die Werte

Der eigentliche Schmerzpunkt beim Haushalt ist nicht die Extraktion einzelner
Zellen, sondern dass jedes Berichtsjahr ein leicht anderes Spaltenlayout hat.
Statt pro Jahrgang neue Heuristiken zu schreiben, kann das LLM **einmal pro
Dokument** die Kopfzeile auf das kanonische Schema abbilden:

```
OCR-Markdown  →  Kopfzeile(n) der Tabelle
                       │
                       ▼
        LLM: "ordne diese Spaltenüberschriften den 16 Zielfeldern zu"
                       │
                       ▼
        column_map = {0: "lfd_nr", 1: "finve_nr", … }   ← im Review sichtbar
                       │
                       ▼
        deterministischer Parser überträgt ALLE Werte anhand column_map
```

Ein LLM-Call statt hunderter, keine Zahl passiert das Modell, und das Mapping
ist ein Objekt mit 16 Einträgen — im Review-UI in Sekunden prüf- und
korrigierbar. Das ist der Hebel, der *„Haushaltsberichte 2020–2025"* öffnet,
ohne die Datenqualität zu riskieren. Die Sonderlogik für Untertitel-Zeilen,
Nachrichtlich-Zeilen und SV-FinVes bleibt deterministisch und behält ihre
Tests (`test_haushalt_parser_blocks.py`, `test_haushalt_upsert.py`).

---

## Zielarchitektur

```
                      apps/backend/dashboard_backend/services/
                      ├── document_ocr.py   (aus tasks/vib_ocr.py)
                      └── llm.py            (bestehend)
                                │
   ┌────────────┬───────────────┼───────────────┬──────────────┐
   │            │               │               │              │
  VIB         Fulda          Haushalt         Medien        Bauportal
   │            │               │               │           (JSON-API,
Stufe 1  ────── gemeinsam: extract_document_text() ──────      kein PDF)
   │            │               │               │
Stufe 2   TOC-Anker      Volltext        Tabellenzeilen    Volltext
   │            │               │               │
Stufe 3   LLM/Block     LLM/Dokument   column_map (LLM)   LLM/Dokument
   │            │          + det. Werte          │
   └────────────┴───────────────┴───────────────┘
                                │
                Fuzzy-Matching → Human-Review → Confirm
                (crud/_importer_common.py, features/import-review/shared)
```

### Gemeinsamer Vertrag Stufe 1

```python
# services/document_ocr.py
def extract_document_text(
    pdf_bytes: bytes,
    *,
    start_page: int | None = None,
    end_page: int | None = None,
    strip_headers_footers: bool = True,
) -> OcrResult:
    """PDF → Markdown. Mistral OCR, pymupdf-Fallback ohne OCR_API_KEY."""

@dataclass
class OcrResult:
    text: str            # Markdown, alle Seiten zusammengefügt
    pages: list[str]     # NEU: pro Seite, für Seitenzuordnung im Review
    model: str           # "mistral-ocr-2512" | "pymupdf" | "none"
    status: str          # "done" | "fallback" | "failed"
    images: list[dict]
```

Gegenüber heute drei Änderungen: Rückgabe als benanntes Objekt statt
4er-Tupel (der aktuelle Docstring in `vib_ocr.py` beschreibt noch ein 3er-Tupel),
Settings-Zugriff im Service statt vier Aufrufstellen mit identischen
`settings.ocr_*`-Argumenten, und `pages` als Feld — Voraussetzung für den
offenen Roadmap-Punkt *„VIB-Review: Original-PDF-Anzeige"* (Sprung zur
richtigen Seite).

### Gemeinsame OCR-Persistenz

Die drei VIB-Spalten (`ocr_raw_text`, `ocr_status`, `ocr_model`) haben sich
bewährt und sollten als Mixin für alle PDF-Draft-Modelle bereitstehen, damit
Haushalt und Fulda dieselbe Resume-Fähigkeit und dieselbe Inspizierbarkeit
bekommen.

---

## Aufwand, Kosten, Risiken

**Aufwand** (grobe Einordnung, keine Zusage):

| Schritt | Umfang |
|---|---|
| `tasks/vib_ocr.py` → `services/document_ocr.py`, `OcrResult`, Aufrufer nachziehen | klein, rein mechanisch, bestehende Tests decken ab |
| OCR-Mixin + Migration für Haushalt-/Fulda-Drafts | klein |
| Haushalt: OCR-Markdown-Pfad neben pdfplumber, umschaltbar | mittel |
| Haushalt: `column_map` per LLM + Review-UI dafür | mittel |
| Medien: PDF-Upload über dieselbe Stufe 1 | klein |

**Laufende Kosten:** unverändert im Rahmen des VIB-Werts — ~$0,20 je
100-Seiten-OCR plus <$0,10 LLM. Der Haushalt kommt mit **einem** zusätzlichen
LLM-Call pro Import dazu, nicht mit einem pro Zeile.

**Risiken:**

- *Externe Abhängigkeit.* Mistral-Ausfall degradiert auf pymupdf; für den
  Haushalt muss pdfplumber als zweiter Fallback erhalten bleiben, sonst ist ein
  funktionierender Importer von einem Fremddienst abhängig.
- *Nicht-Determinismus.* Zwei Läufe desselben PDFs können abweichen. Für Werte
  durch den deterministischen Pfad ausgeschlossen; für das `column_map` durch
  Review abgefangen (`temperature=0` ist gesetzt, aber keine Garantie).
- *Datenabfluss.* Beim Haushalt gehen Dokumentinhalte an einen externen
  Dienst. Alle betroffenen PDFs sind öffentliche Bundestagsdrucksachen — kein
  Vertraulichkeitsproblem, sollte aber bewusst festgehalten werden.
- *Regression im Haushalt.* Der bestehende Parser funktioniert für 2026.
  Umstellung nur mit Golden-Fixture-Test: identisches PDF, alter und neuer Pfad,
  Zeilen- und Wertegleichheit als Testbedingung.

---

## Empfohlene Reihenfolge

1. **Stufe-1-Vereinheitlichung ohne Verhaltensänderung** — `services/document_ocr.py`,
   `OcrResult`, VIB und Fulda umstellen. Reiner Refactor, sofort werthaltig
   (löst die Domänen-Kopplung, macht `pages` verfügbar).
2. **OCR-Persistenz-Mixin** für alle PDF-Draft-Modelle.
3. **Medien-Importer um PDF-Upload erweitern** — kleinster Nutzen-pro-Aufwand-Schritt
   auf dem neuen Fundament, validiert den gemeinsamen Vertrag mit einer dritten Quelle.
4. **Haushalt: OCR-Pfad parallel** hinter Feature-Schalter, Golden-Fixture-Vergleich
   gegen den pdfplumber-Pfad für den 2026-Bericht.
5. **Haushalt: `column_map` per LLM** + Review-UI; danach 2020–2025 einlesen.
6. Erst wenn 4 und 5 grün sind: pdfplumber-Pfad zum Fallback zurückstufen.

Schritte 1–3 sind unabhängig vom Haushalt und können vorgezogen werden.

---

## Nicht empfohlen

- **Haushalt-Zahlenwerte per LLM extrahieren.** Kein Reviewer kann 700 × 16
  Zahlen gegenprüfen; ein stiller Fehler landet unbemerkt in Budget-Zeitreihen.
- **Seiten als Bilder an ein Vision-LLM.** Im VIB-Feature bereits verworfen
  (Kosten, Latenz, Nicht-Determinismus) — die Bewertung gilt unverändert.
- **pdfplumber vollständig entfernen**, solange der Haushalt-Pfad nicht über
  mindestens einen vollständigen Jahresimport verifiziert ist.
- **Bauportal anfassen.** JSON-API, keine Extraktion, kein Handlungsbedarf.

---

## Offene Fragen

- Soll der Haushalt-Import bei fehlendem `OCR_API_KEY` weiterhin vollwertig
  über pdfplumber laufen (Empfehlung: ja) oder wie VIB/Fulda degradieren?
- Braucht das `column_map` eine Versionierung pro Berichtsjahr in der DB, damit
  ein Re-Import desselben Jahrgangs ohne LLM-Call auskommt?


---

## Umsetzungsstand

Stand nach der Aktualisierung des Haushalts-Imports (verifiziert am EP-12-Bericht
Teil B zum HH-Entwurf 2027).

| Schritt | Stand | Ergebnis |
|---|---|---|
| 1 Stufe-1-Vereinheitlichung | **erledigt** | `services/document_ocr.py` mit `OcrResult(text, pages, model, status, images)`; Credentials kommen aus `settings`, nicht mehr aus vier Aufrufstellen. VIB und Fulda ziehen darüber; `tasks/vib_ocr.py` existiert nicht mehr. |
| 2 OCR-Persistenz-Mixin | **erledigt** | `models/mixins.py::OcrSourceMixin` (`ocr_raw_text`/`ocr_status`/`ocr_model`), genutzt von `VibDraftReport` und neu von `HaushaltsParseResult` (Migration `20260908001`). |
| 3 Medien-Importer um PDF-Upload | offen | — |
| 4 Haushalt: OCR-Pfad parallel | **erledigt (Vergleich gegen echte API offen)** | `HAUSHALT_EXTRACTION=compare` liest dasselbe PDF über beide Wege und speichert den Zeilen- und Wertevergleich beim Lauf; im Review sichtbar. Werte kommen dabei aus pdfplumber. Vergleichsskript: `scripts/compare_haushalt_extraction.py`. |
| 5 Haushalt: `column_map` + Review-UI | **erledigt** | `tasks/haushalt_columns.py`; Anzeige im Review über `ColumnMappingPanel`. |
| 6 pdfplumber zum Fallback zurückstufen | **entschieden: nein** | Der Vergleich gegen die echte API ist gelaufen (2026-09-10, `mistral-ocr-latest`): Exit-Code 1, 141 ↔ 107 Zeilen, 79 Wertabweichungen. `HAUSHALT_EXTRACTION` bleibt auf `pdfplumber`. Begründung und Zahlen unten. |

### Abweichungen von der Empfehlung — und warum

**Die Spaltenzuordnung ist deterministisch-zuerst, nicht LLM-zuerst.** Die
Kopfzeile der Tabelle steht in der pdfplumber-Ausgabe bereits als Text zur
Verfügung; ein Musterabgleich darauf löst alle bisher gesehenen Layouts (2026 und
2027) ohne externen Dienst, ohne Kosten und reproduzierbar. Der LLM-Call bleibt
als zweite Stufe erhalten und greift, wenn der Abgleich ein Pflichtfeld nicht
findet — genau der Fall, den die Empfehlung adressiert. Ergebnis ist dieselbe
Entkopplung vom Jahrgang bei strikt geringerem Risiko.

**Zusätzlich zur Empfehlung: Tabellen-Segmentierung und Mehrtabellen-Import.**
Der 2027-Bericht zeigte ein Problem, das die Evaluation nicht erfasst hatte: Teil B
enthält fünf Tabellen, und der Parser las alle als eine. Die Zeilen der Tabellen
2–5 (Lärmsanierung, ERTMS, Kleine und Mittlere Maßnahmen, InvKG) haben keine
FinVe-Nummer und landeten deshalb als Titel- und Erläuterungs-Untereinträge an der
letzten Sammel-FinVe von Tabelle 1 — im 2027-Bericht 51 statt 3 Titel-Einträge und
78 statt 1 Erläuterungs-Projekt an „SV Rest 2025". Die Segmentierung nach der
Seitenüberschrift `Tabelle <N> - <Titel>` behebt das; seither wird **jede** der
fünf Tabellen eingelesen (Details in `feature-haushalt-import.md`). Dafür waren
zwei Dinge nötig, die die Evaluation nicht vorgesehen hatte: eine Identität für
Maßnahmen ohne FinVe-Nummer (`finve.finve_key`) und eine Rekonstruktion der
Zeilen auf den ERTMS-Seiten, wo pdfplumber mangels Trennlinien ganze Abschnitte
in eine Zelle zusammenfasst.

### Golden-Fixture-Vergleich

Die von der Evaluation geforderte Bedingung („identisches PDF, alter und neuer
Pfad, Zeilen- und Wertegleichheit") ist am EP-12-Bericht Teil B 2027 für die
Bedarfsplan-Tabelle erfüllt: 83 FinVe-Zeilen und 2 unmatched Zeilen vor wie nach
der Umstellung, **null** Abweichungen in `proposed_finve` und `proposed_budget`.
Die einzige Differenz ist die beseitigte Kontamination an „SV Rest 2025". Diese
Gleichheit gilt auch nach dem Mehrtabellen-Import weiter — die Tabellen 2–5
kommen als 58 zusätzliche Zeilen hinzu, ohne eine einzige Zeile der Tabelle 1 zu
verändern. Als Regressionsschutz im Repo:
`tests/unit/test_haushalt_parse_2027.py` gegen die aufgezeichnete pdfplumber-
Ausgabe in `tests/fixtures/haushalt_ep12_2027_pages.json`.

### Beantwortete offene Fragen

- *Läuft der Haushalt bei fehlendem `OCR_API_KEY` weiterhin vollwertig?* Ja —
  `HAUSHALT_EXTRACTION` steht per Default auf `pdfplumber`, und auch in den
  Modi `compare`/`ocr` trägt pdfplumber den Import, wenn die OCR-Stufe ausfällt
  oder keine Zeilen findet. Ein Import scheitert nie an einem fremden Dienst.
- *Braucht `column_map` eine Versionierung pro Berichtsjahr?* Nicht als eigene
  Tabelle: die Zuordnung wird je Lauf in `haushalts_parse_result.column_map_json`
  gespeichert und ist damit pro Import nachvollziehbar. Da die deterministische
  Erkennung ohnehin ohne LLM-Call auskommt, spart eine Wiederverwendung nichts.


### Schritt 6: Vergleich gelaufen — pdfplumber bleibt die Quelle der Zahlen

Der Vergleichslauf gegen die echte API ist am 2026-09-10 erfolgt, mit dem
EP-12-Bericht Teil B zum HH-Entwurf 2027 (44 Seiten, Tabellen 1–5) und
`mistral-ocr-latest`:

```
.venv/bin/python scripts/compare_haushalt_extraction.py EP12_TeilB_2027.pdf 2027
→ Exit-Code 1
   Rows pdfplumber: 141      Rows OCR: 107      Rows in both: 107
   Nur pdfplumber: 34        Nur OCR: 0         Wertabweichungen: 79
```

Vor diesem Ergebnis stehen zwei Reparaturen, ohne die der Lauf noch weit
schlechter aussah (141 ↔ 55 Zeilen, 69 Abweichungen, dazu 19 erfundene Zeilen):

1. **Die OCR-Stufe wird für den Haushalt auf `table_format="html"` umgestellt.**
   Markdown kann keinen Zeilenumbruch *innerhalb* einer Zelle ausdrücken — im
   ganzen Dokument kam kein einziges `<br>` zurück. Ein Haushalts-Datensatz ist
   aber genau das: eine Zeile mit gestapelten `davon:`-Titelzeilen darunter.
   Markdown klebte sie mit Leerzeichen zusammen (`"77.859 22.200 - 55.659"` in
   einer Zelle), und welcher Wert zu welcher Titelzeile gehört, war weg. HTML
   liefert `<br>` und drückt eine verbundene Kopfzelle als `colspan`/`rowspan`
   aus — dieselbe Form, die pdfplumber zurückgibt.
2. **Die drei Identitätsspalten werden über die Spaltenzuordnung gelesen.**
   pdfplumber gibt Lfd. Nr., FinVe-Nummer und Bedarfsplan-Nummer im 2026+-Layout
   in *einer* Zelle zurück (`"B0080 275 N19"`), die OCR-Stufe in den drei
   Spalten, die der Tabellenkopf deklariert. Die Zeilenerkennung hing an der
   verbundenen Variante; jetzt liest sie beide. Das ist unabhängig vom OCR-Pfad
   der richtige Umgang mit einem Jahrgangs-Layout und öffnet die älteren
   Berichte mit.

Was danach übrig bleibt, ist nicht reparierbar — es liegt am Modell, nicht an
der Übersetzung:

| Klasse | Umfang | Bewertung |
|---|---|---|
| **Fehlende Zeilen** — das Modell lässt den Identitätsmarker `YYY` auf den Seiten der Tabellen 2–4 weg (21 von 44 Vorkommen im Dokument) | 34 von 141 Zeilen: Tabelle 2 (8), 3 (10) und 4 (11) **vollständig**, Tabelle 5 fünf von 29. Tabelle 1 ist mit 83/83 vollständig | Ohne den Marker hat die Zeile keine Identität; der Parser kann sie nicht erfinden |
| **Falsch gelesene Zahlen** | ~29 von 5.568 Zahl-Token im Dokument, u. a. `1.843.520 → 1.043.520`, `98.205 → 58.205`, `33.939 → 33.999`, `244.130 → 244.110` | Genau der Fehler, den kein Reviewer findet — es gibt keine Vergleichsgröße |
| **Vorzeichen als eigene Spalte** | 5 Zeilen: das Minus eines negativen Deltas wird als eigene Tabellenzelle ausgegeben, der Betrag rutscht in die Prozentspalte (`delta_previous_year` leer, `delta_previous_year_relativ = 4.275`) | Dieselbe Ursache wie der `–`-Platzhalter-Fall aus dem Mehrtabellen-Import: ohne Zellkoordinaten ist die Spaltengeometrie nicht rekonstruierbar |
| **Falsch gelesene Namen** | 20 Zeilen, u. a. `Kehl → Kohl`, `Ebensfeld → Ebersfeld`, `Schienenanbindung → Schienemanbindung`, `SV EKrG 2019 → SV (KrG 2019` | Im Review sichtbar, aber Handarbeit für jeden Import |
| **Nicht-Determinismus** | Zwei Läufe desselben PDFs lieferten unterschiedliche Zeilenzahlen (55 bzw. 38 auf dem Markdown-Pfad) und unterschiedliche Lesefehler | Ein grüner Lauf würde nichts über den nächsten aussagen |

Die 79 Wertabweichungen verteilen sich über 50 der 107 gemeinsamen Zeilen:
`lfd_nr` (24) und `bedarfsplan_number` (24) sind reine Darstellungsunterschiede
aus der oben beschriebenen Spaltenverbindung — dort liest die OCR-Stufe sogar
sauberer. Substanziell sind `name` (20), `delta_previous_year` und
`delta_previous_year_relativ` (je 5) und `next_years` (1).

**Bemerkenswert:** in den eigentlichen Geldspalten — `cost_estimate_original`,
`cost_estimate_last_year`, `cost_estimate_actual`, `spent_two_years_previous`,
`allowed_previous_year`, `spending_residues`, `year_planned` — steht über alle
107 gemeinsamen Zeilen **null** Abweichung. Das Modell liest die Tabelle also im
Kern richtig; es scheitert an den Rändern, und die Ränder entscheiden hier über
die Richtigkeit einzelner Zahlen.

### Entscheidung

`HAUSHALT_EXTRACTION` bleibt per Default auf `pdfplumber`, und der Haushalt
bezieht seine Zahlen weiter von dort. Schritt 6 ist damit beantwortet, nicht
offen: die Umstellung ist an diesem Bericht nachweislich nicht verlustfrei, und
die drei Fehlerklassen liegen alle außerhalb dessen, was
`tasks/haushalt_markdown.py` oder `tasks/haushalt_columns.py` beheben können.

Der Umschalter, der Vergleichsmodus und das Skript bleiben — sie sind jetzt das
Messinstrument für die nächste Modellgeneration statt eine offene Baustelle. Was
den Vergleich wiederholt, wiederholt ihn gegen den verbesserten OCR-Pfad: die
beiden Reparaturen oben sind eingebaut und getestet
(`tests/unit/test_haushalt_markdown.py`, `tests/unit/test_haushalt_id_columns.py`,
`tests/unit/test_haushalt_ocr_path.py` fährt den Round-Trip über **beide**
Tabellenformate).

`pdfplumber` bleibt aus demselben Grund in `requirements.txt`; der in Schritt 6
vorgesehene Ausbau der Bibliothek entfällt, solange dieses Ergebnis gilt.

Ein Wort zur Erwartung, die sich bestätigt hat: Für **Fließtext** (VIB, Fulda)
ist die OCR-Stufe klar überlegen, dafür wurde sie eingeführt. Für den Haushalt
entscheidet die *Spaltengeometrie* über die Richtigkeit jeder Zahl, und die ist
in einer Auszeichnungssprache ohne Zellkoordinaten nicht vollständig
darstellbar. pdfplumber liefert sie mit.
