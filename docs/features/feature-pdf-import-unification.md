# Feature: PDF-Import vereinheitlichen — Evaluation

> **Status: Evaluation / Entscheidungsvorlage.** Nichts hiervon ist implementiert.
> Umsetzung erst nach Zerlegung in Board-Issues (`docs/github-projects.md`).

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
| **VIB** (Verkehrsinvestitionsbericht) | Mistral OCR → Markdown, pymupdf-Fallback | TOC-verankertes Block-Splitting (Regex) | LLM je Vorhabenblock (`call_llm_json`) | Celery, 2-stufig mit Preview | `tasks/vib_ocr.py`, `tasks/vib.py`, `tasks/vib_ai_extraction.py` |
| **Fulda-Runde** (Kleine Anfrage) | Mistral OCR (ruft `tasks.vib_ocr` auf) | keine — Volltext in einem Stück | LLM über das ganze Dokument | Celery, einstufig | `tasks/fulda.py`, `tasks/fulda_extraction.py` |
| **Haushalt** (Anlage VWIB, Teil B) | `pdfplumber.extract_table()` je Seite | Flat-Table über alle Seiten + ~15 Format-Heuristiken | **keine** — reine Regex/Spaltenindex-Logik | Celery, einstufig | `tasks/haushalt.py` (802 Zeilen) |
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
