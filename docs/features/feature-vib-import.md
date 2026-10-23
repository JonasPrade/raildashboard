# Feature: VIB Import — Robuster Parser + KI-Extraktion

## Ziel

Den Verkehrsinvestitionsbericht (VIB) zuverlässig importieren. Die bisherige rein
regex-basierte Implementierung verliert regelmäßig Daten, weil das PDF ein
zweispaltiges Layout mit inkonsistenten Seitenstrukturen hat. Ziel ist eine
**Hybridarchitektur**: robuste Strukturerkennung aus dem Inhaltsverzeichnis +
LLM-basierte Inhaltsextraktion pro Vorhabenblock.

> **Seit 2026-10-20 (Phase 7):** Der empfohlene Weg ist das Einlesen über MCP + Skill
> (`vib-import`); der hier beschriebene Upload bleibt als zweiter Weg bestehen.

---

## Bekannte Probleme (Ist-Zustand)

| # | Problem | Symptom |
|---|---------|---------|
| 1 | Fester Spaltentrennwert 250 pt | Einspaltiger Seiten werden falsch aufgeteilt → unlesbarer Text |
| 2 | Fehlgeschlagene Heading-Erkennung | Block eines Projekts "frisst" PFA-Tabelle des nächsten |
| 3 | `project_status` wird nie befüllt | Feld immer `null`, obwohl Projektstand-Block geparst wird |
| 4 | PFA-Parser bricht bei Spaltenartefakten | "in Überarbeitung" über Spaltengrenze → alle Datumswerte verloren |
| 5 | Sub-Blocks nicht editierbar in Review-UI | Falsch erkannte Felder können nicht korrigiert werden |
| 6 | Kein Debug-Script für VIB-Parse | Diagnose nur über Celery/Redis möglich |

---

## Architektur (Soll)

### Warum kein reiner AI-First-Ansatz?

**Option: PDF-Seiten als Bilder an LLM senden**
- Kosten: ~$1–5 pro Import (100 Seiten × Image-Tokens)
- Langsam, nicht-deterministisch
- Unnötig: Die Dokumentstruktur (welcher Block gehört zu welchem Projekt)
  ist über das Inhaltsverzeichnis bereits zuverlässig extrahierbar.

**Empfehlung: Hybrid**

```
PDF
 │
 ├─ Schritt 1: Strukturerkennung (Regex/TOC — zuverlässig)
 │    ├─ Inhaltsverzeichnis → kanonische Namen + Sektionsnummern
 │    ├─ Spaltenanalyse pro Seite (bimodal vs. unimodal x0-Verteilung)
 │    └─ Blöcke anhand Sektionsnummern als Anker trennen
 │
 ├─ Schritt 2: Inhaltsextraktion (LLM — robust gegen Layout-Variationen)
 │    └─ Pro Block: Bauaktivitäten, PFA-Tabelle, Planungsstand, Status, …
 │
 └─ Schritt 3: Human Review (unverändert)
      └─ Projektzuordnung bestätigen, Korrekturen, Confirm
```

**Kosten:** ~50 Projekte × ~1.500 Token = ~75.000 Token pro Import.
Mit `claude-haiku-4-5` < $0,10 pro Import.

---

## Phase 1: Strukturerkennung reparieren

### 1a — Spaltentyp-Erkennung pro Seite

Statt festem `COL_BOUNDARY = 250` die x0-Verteilung der Wörter analysieren:
- Histogram der x0-Werte erstellen
- Wenn klare Lücke zwischen ~43–220 pt und ~283–400 pt → zweispaltig
- Sonst → einspaltig (ganzseitig extrahieren)

Implementierungsort: `_extract_page_text_columns()` in `tasks/vib.py`

### 1b — TOC-verankerte Blockgrenzen

Derzeit: Regex sucht im Fließtext nach Überschriften → fehleranfällig.
Neu: TOC liefert bereits alle `B.4.x.x`-Sektionsnummern. Im Fließtext nur noch
nach der Sektionsnummer selbst suchen (kurzes, robusteres Pattern), nicht nach
der vollständigen Überschriftenzeile.

```python
# Statt: r"^(B[\s.]4\.\d+\.\d+)\s{1,8}(.+)$"
# Nur Anker: r"^(B[\s.]4\.\d+\.\d+)"  → findet die Zeile zuverlässig
# Namen kommen aus dem TOC (bereits implementiert)
```

### 1c — Debug-Script

Analog zu `scripts/dump_parse_result.py` (Haushalt):
`scripts/dump_vib_parse_result.py` — gibt alle erkannten Blöcke, Sub-Blocks
und PFA-Einträge strukturiert aus, ohne Celery/DB.

---

## Phase 2: LLM-Inhaltsextraktion

### Frontend-Flow (zweistufig)

```
Upload PDF
    │
    ▼
[Parse-Task läuft — Fortschrittsbalken: Seite X / Y]
    │
    ▼
VibStructurePreviewPage  (/admin/vib-import/preview/{taskId})
    │
    │  Zeigt: Liste aller gefundenen Projekte
    │    - Sektionsnummer (B.4.1.x)
    │    - Projektname (aus TOC)
    │    - Kategorie (laufend / neu / potentiell)
    │    - Rohtext-Vorschau (erste ~200 Zeichen)
    │    - Anzahl erkannter PFA-Zeilen
    │    ┌────────────────────────────────────┐
    │    │  ⚠ 3 Projekte ohne PFA-Tabelle    │  (Warnung wenn auffällig)
    │    └────────────────────────────────────┘
    │
    │    [Abbrechen]   [Weiter mit KI-Extraktion →]
    │                   (deaktiviert wenn LLM_BASE_URL nicht konfiguriert,
    │                    Tooltip: "LLM nicht konfiguriert")
    │
    ▼ (Nutzer klickt "Weiter")
[KI-Extraktions-Task läuft — Fortschrittsbalken: Projekt X / Y]
    │
    ▼
VibReviewPage  (/admin/vib-import/review/{taskId})   ← bestehend, erweitert
    │  Alle Felder jetzt befüllt + editierbar
    │
    ▼
Confirm → Daten in DB
```

### Warum eine eigene Preview-Seite?

- Nutzer sieht sofort ob die Struktur stimmt (richtige Anzahl Projekte,
  plausible Namen) — **bevor** kostenpflichtige LLM-Calls laufen
- Gibt Kontrolle: Nutzer kann abbrechen und PDF neu hochladen wenn offensichtlich
  etwas schiefgelaufen ist (z.B. nur 10 statt 50 Projekte erkannt)
- Fortschrittsanzeige für KI-Extraktion ist sinnvoll weil ~50 API-Calls
  mehrere Sekunden dauern

### Ansatz

Nach Schritt 1 liegt pro Projekt ein `raw_text`-Block vor (bereits korrekt
begrenzt). Dieser Block wird an das LLM gesendet, das strukturiert antwortet.

**Wann:** Explizit ausgelöst durch Nutzer-Klick auf "Weiter mit KI-Extraktion"
in der Preview-Seite. Läuft als Celery-Sub-Task.

**Provider:** Jeder Anbieter mit OpenAI-kompatibler API (OpenAI, Mistral, Ollama,
Azure OpenAI, LiteLLM-Proxy, …). Konfigurierbar über Umgebungsvariablen:

| Variable | Pflicht | Beschreibung | Beispiel |
|---|---|---|---|
| `LLM_BASE_URL` | Ja | Base-URL des OpenAI-kompatiblen Endpunkts. Leer = KI-Extraktion deaktiviert. | `http://localhost:11434/v1` |
| `LLM_API_KEY` | Nein | API-Key — bei lokalen Anbietern (Ollama) nicht benötigt. | `sk-…` |
| `LLM_MODEL` | Ja | Modellname | `gpt-4o-mini` |

### Prompt (pro Vorhabenblock)

```
Du analysierst einen Abschnitt aus dem Verkehrsinvestitionsbericht (VIB) des Bundes.
Extrahiere die folgenden Felder als JSON. Antworte NUR mit dem JSON-Objekt.

Sektionsnummer: {vib_section}
Projektname: {vib_name_raw}

--- ROHTEXT ---
{raw_text}
--- ENDE ---

{
  "verkehrliche_zielsetzung": "<Text oder null>",
  "durchgefuehrte_massnahmen": "<Text oder null>",
  "noch_umzusetzende_massnahmen": "<Text oder null>",
  "bauaktivitaeten": "<Text oder null>",
  "teilinbetriebnahmen": "<Text oder null>",
  "planungsstand": "<Text oder null>",
  "project_status": "<'Planung' | 'Bau' | null>",
  "strecklaenge_km": <float oder null>,
  "gesamtkosten_mio_eur": <float oder null>,
  "entwurfsgeschwindigkeit": "<z.B. '200/250' oder null>",
  "pfa_entries": [
    {
      "nr_pfa": "<z.B. '1.1'>",
      "oertlichkeit": "<Text oder null>",
      "entwurfsplanung": "<'abgeschlossen' | 'offen' | 'in Überarbeitung' | null>",
      "abschluss_finve": "<Datum oder null>",
      "datum_pfb": "<Datum oder null>",
      "baubeginn": "<Datum oder null>",
      "inbetriebnahme": "<Datum oder null>"
    }
  ]
}
```

### Verhalten

- Extraktion läuft asynchron (Celery-Task `extract_vib_blocks`), Polling analog Haushalt-Import
- Button deaktiviert wenn `LLM_BASE_URL` nicht konfiguriert
- Ergebnis überschreibt die regex-extrahierten Felder im Draft; `ai_extracted = true`
- Fehlschlag eines einzelnen Blocks → Fehler protokolliert, andere Blöcke weiter
- Bereits extrahierte Felder (aus Phase 1) bleiben als Fallback erhalten

---

## Phase 3: Review-UI erweitern

### Sub-Blocks editierbar machen

Aktuell sind `bauaktivitaeten`, `verkehrliche_zielsetzung` etc. reine Anzeige.
Nach LLM-Extraktion müssen Nutzer Korrekturen vornehmen können.

- `Textarea` für: `bauaktivitaeten`, `teilinbetriebnahmen`, `planungsstand`,
  `verkehrliche_zielsetzung`, `durchgefuehrte_massnahmen`, `noch_umzusetzende_massnahmen`
- Alle Felder müssen in `VibEntryProposed` und `VibConfirmEntryInput` als editierbar behandelt werden
- KI-extrahierte Karten mit Badge "KI" markieren (`ai_extracted`-Flag)

### PFA-Tabelle editierbar

- Inline-Editierbarkeit für Datum-Felder in der PFA-Tabelle
- Zeile hinzufügen / löschen

---

## Implementierungsreihenfolge

### Phase 1 (Parser-Fixes — kein LLM)

- [x] 1a: Per-Seite Spaltentyp-Erkennung (bimodal x0-Analyse)
- [x] 1b: TOC-verankerte Blockgrenzen (Sektionsnummer als Anker statt voller Heading-Regex)
- [x] 1c: `scripts/dump_vib_parse_result.py` Debug-Script
- [x] 1d: `project_status` aus `planungsstand`-Block extrahieren (Regex: `Planung|Bau`)

### Phase 2 (LLM-Extraktion)

- [x] 2a: Celery-Task `extract_vib_blocks` in `tasks/vib_ai_extraction.py`
- [x] 2b: Endpoint `POST /api/v1/import/vib/{task_id}/extract-ai` + eigener Task-Status-Polling
- [x] 2c: `VibStructurePreviewPage` (`/admin/vib-import/preview/{taskId}`)
      — Projektliste mit Rohtext-Vorschau + Warnungen + "Weiter"-Button
- [x] 2d: Nach Parse-Task: Redirect zu Preview statt direkt zur Review-Page
- [x] 2e: Nach KI-Task: Redirect zur Review-Page
- [x] 2f: `ai_extracted`-Badge in VibEntryCard

### Phase 3 (Review-UI)

- [x] 3a: Sub-Block-Felder als editierbare Textareas in VibEntryCard
- [x] 3b: PFA-Tabelle inline editierbar (Zeilen hinzufügen/löschen, Felder editieren)

---

## Phase 4: OCR-Pipeline (Mistral OCR oder pymupdf-Fallback)

### Ziel

Die fragile pdfplumber-Zweispalten-Extraktion durch Mistral OCR ersetzen, das das gesamte PDF in einem Aufruf verarbeitet und **Markdown pro Seite** zurückgibt — mit korrekter Tabellenrekonstruktion (HTML colspan/rowspan), was für PFA-Tabellen entscheidend ist.

### Ziel-Modell

**`mistral-ocr-latest`** (aktuell `mistral-ocr-2512`) — Mistral Document AI.
Preis: $2 / 1.000 Seiten → ca. **$0,20 pro VIB-Import** (~100 Seiten).

### Wie Mistral OCR funktioniert

Mistral OCR ist **kein** OpenAI-kompatibler Chat-Endpunkt. Es ist eine dedizierte Document-AI-API mit eigenem SDK:

```python
from mistralai import Mistral

client = Mistral(api_key=settings.mistral_api_key)
ocr_response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{b64_pdf}",
    },
    table_format="html",   # beste Tabellenrekonstruktion für PFA-Tabellen
)
```

**Response-Struktur:**
```python
ocr_response.pages  # Liste von Page-Objekten
ocr_response.pages[i].markdown  # Markdown-Text der Seite (inkl. HTML-Tabellen)
ocr_response.pages[i].index     # Seitennummer
```

Das gesamte PDF wird in **einem** API-Call verarbeitet (kein per-Seite-Loop nötig). Die zurückgegebenen Seiten entsprechen dem Gesamt-PDF — wir filtern danach auf Abschnitt B.

### Pipeline

```
PDF-Bytes
    │
    ├─ MISTRAL_API_KEY konfiguriert?
    │    Ja → client.ocr.process(PDF als base64) → pages[i].markdown pro Seite
    │    Nein → pymupdf get_text("text") als Fallback (kein Markdown, kein HTML)
    │
    ▼
Seiten auf Abschnitt B filtern (nach "B Schienenwege" / vor "C Bundesfernstraßen")
    │
    ▼
Markdown-Seiten zusammenfügen → full_text (in DB speichern, s.u.)
    │
    ▼
Block-Splitter → raw_text pro Eintrag (VibEntryProposed)
    │
    ▼
Semantik-KI — Phase 2 (unverändert, liest raw_text wie bisher)
```

### Konfiguration

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `OCR_API_KEY` | Nein | Mistral-API-Key. Leer = pymupdf-Fallback. |
| `OCR_BASE_URL` | Nein | Mistral API base URL (default: `https://api.mistral.ai`) |
| `OCR_MODEL` | Nein | OCR-Modell (default: `mistral-ocr-latest`) |

### DB-Persistenz

Die OCR-Ausgabe wird **vor dem Block-Splitting** in der DB gespeichert, damit:
- Bei Fehler im Block-Splitting OCR nicht erneut läuft
- OCR-Qualität inspizierbar ist (Admin kann Rohtext-Markdown vor dem Import prüfen)
- Prozess jederzeit resumt werden kann

**Neue Spalten in `VibDraftReport`:**

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `ocr_raw_text` | `Text`, nullable | Zusammengefügtes Markdown aller Abschnitt-B-Seiten, vor Block-Splitting. Leer wenn pymupdf-Fallback. |
| `ocr_status` | `String(20)`, nullable | `running` / `done` / `failed` / `fallback` |
| `ocr_model` | `String(100)`, nullable | Genutztes Modell, z.B. `mistral-ocr-2512` (für Debugging) |

**Ablauf:**
```
parse_vib_pdf startet
  → VibDraftReport anlegen, ocr_status="running"
  → Mistral OCR läuft (1 API-Call)
  → ocr_raw_text = Markdown, ocr_status="done", ocr_model="mistral-ocr-2512"
  → Block-Splitting → raw_result_json befüllen
  → Task fertig

Bei Mistral-Fehler:
  → ocr_status="fallback", pymupdf übernimmt, ocr_raw_text=None

extract_vib_blocks (Phase 2): liest raw_result_json wie bisher — unverändert
```

### Scope

- Neues Modul `tasks/vib_ocr.py`: `_find_rail_page_range`, `_ocr_with_mistral`, `_ocr_fallback_pymupdf`, `extract_text_from_rail_section`
- `mistralai` zu `requirements.txt` (zusätzlich zu `openai` für Semantik-Extraktion)
- `pymupdf` zu `requirements.txt` (Fallback, kein Pillow nötig)
- Config-Feld `mistral_api_key: str = ""`
- Migration: `ocr_raw_text`, `ocr_status`, `ocr_model` in `vib_draft_report`
- `parse_vib_pdf` ruft `extract_text_from_rail_section` statt pdfplumber-Loop
- Endpoint `GET /api/v1/import/vib/ocr-available` analog zu `/ai-available`
- Frontend: OCR-Modus-Badge in VibReviewPage (`Mistral OCR` / `pymupdf`)

### Implementierungsreihenfolge

- [x] 4a: `mistralai` + `pymupdf` zu `requirements.txt` + Config-Felder `ocr_api_key`, `ocr_base_url`, `ocr_model`
- [x] 4b: Alembic-Migration: `ocr_raw_text`, `ocr_status`, `ocr_model`, `ocr_images_json` in `vib_draft_report`
- [x] 4c: `tasks/vib_ocr.py` schreiben + Tests — seit der PDF-Import-Vereinheitlichung `services/document_ocr.py` (gemeinsame Stufe 1, siehe `feature-pdf-import-unification.md`)
- [x] 4d: `parse_vib_pdf` auf `extract_full_pdf_text` umstellen + OCR-Spalten befüllen
- [x] 4e: `GET /ocr-available` Endpoint + Schema
- [x] 4f: OCR-Modus-Badge in VibReviewPage; optionale Seitenbereichs-Inputs + "Kopf-/Fußzeilen ignorieren"-Checkbox im Upload-Formular

---

## Akzeptanzkriterien

- Alle `B.4.x.x`-Projekte aus dem TOC werden als Blöcke erkannt (keine fehlenden Einträge)
- PFA-Tabellen werden dem korrekten Projekt zugeordnet (kein Cross-Contamination)
- `project_status` wird aus dem Planungsstand-Block befüllt
- LLM-Extraktion befüllt alle Textfelder zuverlässiger als der bisherige Regex-Parser
- Alle extrahierten Felder sind in der Review-UI editierbar vor Confirm
- KI-extrahierte Einträge sind visuell gekennzeichnet

---

## Phase 5: Parser-Bugfixes (offene Punkte)

Bekannte Probleme nach der Mistral-OCR-Umstellung. OCR-Qualität ist hoch;
Fehler liegen ausschließlich im Post-Processing (Parser, Review-UI).

---

### Bug 1 — Planungsstand entfernen

**Problem:** Das Feld `planungsstand` wird in der Review-UI als eigene Textarea und in der Strukturvorschau-Tabelle angezeigt, wird aber weder im Confirm noch in der ProjectDetail-Seite genutzt. Erzeugt unnötige Kognitionslast.

**Fix:**
- `VibReviewPage.tsx`: `planungsstand`-Textarea und zugehörige Labels entfernen
- `VibStructurePreviewPage.tsx`: Planungsstand-Vorschau aus `ExpandedRawText` entfernen
- Backend-Feld und DB-Spalte bleiben bestehen (historische Daten, KI nutzt es intern für Status-Flag-Extraktion)

---

### Bug 2 — Projektnamen gehen verloren

**Problem:** Der Parser verwendet `_VORHABEN_SECTION_RE` zum Erkennen von Block-Grenzen, setzt aber `extracted_name = ""` (leer). Namen kommen ausschließlich aus dem TOC. Bei Projekten, die im TOC fehlen oder bei denen die Sektionsnummer leicht abweicht (z.B. Leerzeichen statt Punkt: `B 4.1.1` vs. `B.4.1.1`), bleibt `vib_name_raw` leer.

**Ursache:** `_VORHABEN_SECTION_RE` erfasst nur die Sektionsnummer (zwei Capturing Groups — Markdown-Heading-Format und Plain-Format), nicht den danach stehenden Namen.

```python
# Aktuell — Gruppe 1 oder 2 = Sektionsnummer, Name wird nicht erfasst
_VORHABEN_SECTION_RE = re.compile(
    r"^#+\s*(B[\s.]4\.[123]\.\d+)\b|^(B[\s.]4\.[123]\.\d+)\b",
    re.MULTILINE,
)
```

**Fix:** Den Namen aus der Heading-Zeile extrahieren, wenn er nicht im TOC gefunden wird.

```python
# Option 1: Dritten Capturing Group hinzufügen
_VORHABEN_SECTION_RE = re.compile(
    r"^#+\s*(B[\s.]4\.[123]\.\d+)\s+(.+)|^(B[\s.]4\.[123]\.\d+)\s+(.+)",
    re.MULTILINE,
)
# → Gruppe 2 bzw. 4 = Name (danach _HEADING_SUFFIX_RE anwenden)

# Option 2 (sauberer): Nach dem Section-Match die restliche Zeile separat auslesen
line_text = rail_text[hm.start():rail_text.find("\n", hm.start())]
name_from_heading = line_text[hm.end():].strip()
name_from_heading = _HEADING_SUFFIX_RE.sub("", name_from_heading).strip()
```

TOC-Name hat Vorrang. Heading-Name als Fallback wenn `section_nr not in toc_names`.

---

### Bug 3 & 4 — Status-Checkboxen automatisch setzen

**Problem 3:** `status_planung` und `status_bau` werden via `\bPlanung\b` / `\bBau\b` im `planungsstand`-Text erkannt — zu eng. Viele Einträge haben diesen Status implizit (z.B. "wird derzeit planfestgestellt" → Planung; "Baubeginn vorgesehen 2026" → Bau).

**Problem 4:** `status_abgeschlossen` erkennt "abgeschlossen", "in Betrieb", "fertiggestellt", "in Betrieb genommen" — fehlt aber: "Vorhaben ist abgeschlossen", "Inbetriebnahme erfolgte am", "wurde in Betrieb genommen", "Inbetriebnahme: \d{2}/\d{4}".

**Fix — `_STATUS_*_RE` in `tasks/vib.py` erweitern:**

```python
_STATUS_PLANUNG_RE = re.compile(
    r"\bPlanung\b"
    r"|\bplanfestgestellt\b"
    r"|\bPlanfeststellungsverfahren\b"
    r"|\bEntwurfsplanung\b"
    r"|\boffen\b",   # PFA-Spalte Entwurfsplanung "offen" → Planung läuft
    re.IGNORECASE,
)

_STATUS_BAU_RE = re.compile(
    r"\bBau\b"
    r"|\bBaubeginn\b"
    r"|\bim\s+Bau\b"
    r"|\bBauarbeiten\b"
    r"|\bBaumaßnahmen\b",
    re.IGNORECASE,
)

_STATUS_ABGESCHLOSSEN_RE = re.compile(
    r"\b(abgeschlossen"
    r"|in\s+Betrieb"
    r"|fertiggestellt"
    r"|in\s+Betrieb\s+genommen"
    r"|Inbetriebnahme\s+erfolgte"
    r"|wurde\s+in\s+Betrieb"
    r"|Vorhaben\s+ist\s+abgeschlossen"
    r"|Inbetriebnahme:\s*\d"        # "Inbetriebnahme: 12/2001"
    r"|Inbetriebnahme\s+\d{2}/\d{4}"
    r")\b",
    re.IGNORECASE,
)
```

Zusätzlich: wenn **alle** PFA-Einträge ein `inbetriebnahme`-Datum haben → `status_abgeschlossen = True` setzen (Post-Processing nach PFA-Parsing).

**Geltungsbereich:** Status-Flags werden auf `raw_text` angewendet (nicht nur `planungsstand`), da "Inbetriebnahme erfolgte am" oft im Fließtext steht.

---

### Bug 5 — PFA-Tabelle wird abgeschnitten / falsch geparst

**Problem:** Der aktuelle Parser (`_parse_pfa_table_markdown`) liest Markdown-Pipes und versucht, Zeilen auf feste Spalten zu mappen. Das schlägt fehl bei:
- **Gruppenzeilen** (z.B. `| Lübeck-Bad Kleinen (a) | | | | | | |` — Ortsbezeichnung ohne Nr.)
- **Fortsetzungszeilen** ohne Nr. PFA (`| | Schönberg(e)-Grieben | … |`)
- **Freitext-Zellen** (z.B. `| | Carlshöhe-Bad Kleinen | Diese Teilmaßnahme wurde im Rahmen von … | | | | |`)
- **Mehrzeiligen Örtlichkeiten** in einer Zelle

Beispiel B.4.1.1: Die tatsächliche Tabelle hat 4 Gruppen, ~17 Zeilen — der Parser liefert nur 4.

**Fix:** Komplette Markdown-Tabelle 1:1 als `pfa_raw_markdown` speichern, **zusätzlich** zum strukturierten Parsing.

```python
# In _extract_sub_blocks / _parse_pfa_table:
# 1. Alle Zeilen, die mit "|" beginnen, als Rohblock extrahieren
# 2. Rohblock in neuem Feld pfa_raw_markdown speichern
# 3. Strukturiertes Parsing bleibt als Best-Effort für maschinenlesbare Felder
```

**Schema-Änderung:**
```python
class VibEntryProposed(BaseModel):
    pfa_raw_markdown: Optional[str] = None  # komplette Markdown-Tabelle, unverändert
    pfa_entries: list[VibPfaEntryProposed] = []  # strukturiertes Parsing (Best-Effort)
```

**Review-UI:** Wenn `pfa_raw_markdown` vorhanden, wird es als Markdown gerendert (analog zur bestehenden `ReactMarkdown`-Integration) — direkt unter den strukturierten PFA-Zeilen oder als Tab-Toggle "Tabelle / Roh-Markdown".

**Extraktion:**
```python
_PFA_TABLE_RE = re.compile(
    r"(?:^\|.+\n)+",  # alle aufeinanderfolgenden Pipe-Zeilen
    re.MULTILINE,
)
# Größte zusammenhängende Pipe-Block-Sequenz im PFA-Sub-Block = pfa_raw_markdown
```

---

### Bug 6 — Resttext-Feld (ungenutzter Text)

**Problem:** Text, der keinem `_BLOCK_LABELS`-Abschnitt zugeordnet werden kann (Fußnoten, Einleitungstexte, Querverweise, Inbetriebnahme-Anmerkungen am Ende), geht verloren. Er ist in `raw_text` vorhanden, aber in keinem Anzeige-Feld der Review-UI sichtbar.

**Fix:** Neues Feld `sonstiges` — enthält alles aus `raw_text`, das nach dem Entfernen aller Sub-Block-Texte übrig bleibt.

```python
# Nach _extract_sub_blocks:
used_text = "\n".join(v for v in sub_blocks.values() if v)
remaining = raw_text
for block_text in sub_blocks.values():
    if block_text:
        remaining = remaining.replace(block_text, "", 1)
entry.sonstiges = remaining.strip() or None
```

**Schema:**
```python
class VibEntryProposed(BaseModel):
    sonstiges: Optional[str] = None  # Resttext: Fußnoten, Einleitungen, nicht zugeordneter Text
```

**Review-UI:** Ausklappbare "Sonstiges"-Textarea am Ende der VibEntryCard — immer angezeigt wenn nicht leer, editierbar.

---

### Implementierungsreihenfolge Phase 5

- [ ] **5a** Bug 2: Projektnamen aus Heading-Zeile als TOC-Fallback extrahieren
- [ ] **5b** Bug 3/4: `_STATUS_*_RE` erweitern + auf `raw_text` statt nur `planungsstand` anwenden + PFA-Vollständigkeits-Check
- [ ] **5c** Bug 5: `pfa_raw_markdown` Feld; Extraktion des kompletten Markdown-Table-Blocks; Review-UI Render
- [ ] **5d** Bug 6: `sonstiges`-Feld; Resttext-Berechnung im Parser; Textarea in Review-UI
- [ ] **5e** Bug 1: `planungsstand`-Feld aus Review-UI und Strukturvorschau entfernen

*Note: Phase 5 bugs were documented during implementation of Phase 4 (Mistral OCR pipeline). Parser output quality is already significantly improved over the pdfplumber baseline; these fixes are refinements for edge cases.*

---

## Phase 6: Post-Confirm KI-Extraktion → ProjectProgress — entfällt

Entfällt (2026-10-20, W5): Bestätigte VIB-Einträge werden längst über die Materialisierung
(`services/progress_materialization.py`) zu abgeleiteten Beobachtungen; eine zweite
KI-Extraktion nach dem Confirm ist überflüssig.

---

## Phase 7: VIB über MCP + Skill (Vorrang vor dem Upload)

> Entschieden 2026-10-20 (Widerspruchs-Check W1–W6, siehe [Entscheidungen](#entscheidungen-phase-7)).
> Vorbild: `feature-fulda-import.md`.

### Ziel

Der Upload-Weg (OCR → Regex-Blöcke → Fuzzy-Match → Review) ordnet viele Vorhaben falschen
Projekten zu und verteilt Text auf falsche Felder: Bis zu drei Namensvorschläge waren
vorausgewählt, Abschnittsüberschriften wurden irgendwo im Fließtext erkannt, und die
Statusflags trafen auf fast jede PFA-Tabelle („Entwurfsplanung … abgeschlossen“).

Neu liest ein Agent (Claude) den VIB selbst, der **Skill** `.claude/skills/vib-import/`
gibt die Leseregeln, die **MCP-Tools** geben die Felder vor und prüfen sie. Jede
Zuordnung trägt eine Begründung. Ein Mensch bleibt im Loop: Was der Agent schreibt, ist
**unbestätigt** und wirkt erst nach dem Bestätigen auf den Projektfortschritt.

Der Upload bleibt als **zweiter Weg** bestehen (W2); der MCP-Weg hat Vorrang und ist der
empfohlene. Beide schreiben dieselben Tabellen.

### Datenmodell

`vib_entry` bekommt (Migration `20261020001`, Expand only):

| Feld | Typ | Bedeutung |
|---|---|---|
| `confirmed` | bool, Pflicht, Default `true` | Nur bestätigte Einträge materialisieren. Bestehende Zeilen werden `true` (Backfill), der Upload-Confirm und Zuordnungen durch Menschen in der Oberfläche setzen `true`; jeder Schreibzugriff über MCP setzt `false`. |
| `assignment_note` | text? | Begründung der Projektzuordnung (W4: am Eintrag, nicht je Verknüpfung) |
| `page` | int? | Seite im PDF (Fundstelle) |

Die Zuordnung bleibt **m:n** (`vib_entry_project`): Ein Vorhaben kann mehreren Projekten
zugeordnet sein (z. B. ein Sammelvorhaben mehreren Oberprojekten); die Begründung deckt
alle zugeordneten Projekte ab. PFA-Abschnitte zeigen weiter einzeln auf ein Teilprojekt
(`vib_pfa_entry.project_id`).

Ein Bericht je Jahr (`vib_report.year` eindeutig). Innerhalb eines Berichts ist die
Sektionsnummer (`vib_section`) der Schlüssel: Ein zweites Vorhaben mit derselben Nummer
weist `add_vib_entries` zurück — so kann der Agent einen Jahrgang fortsetzen.

### Bestätigen und Materialisierung (W1)

- `sync_derived_observations` (`crud/projects/progress.py`) liest nur Einträge mit
  `confirmed = true` — für die m:n-Verknüpfung und für PFA→Teilprojekt (wie Bauportal,
  Medien, Fulda).
- `confirm_vib_report` bestätigt alle offenen Einträge eines Berichts, die mindestens ein
  Projekt haben, und rechnet die betroffenen Projekte neu. Einträge ohne Projekt bleiben
  offen und erscheinen unter „Offene Zuordnungen“.
- Ein Mensch, der in der Oberfläche zuordnet (Bearbeiten-Drawer, Projekt-Assistent,
  Offene Zuordnungen), bestätigt damit.
- Auf der Projektseite trägt ein unbestätigter Eintrag das Kennzeichen „unbestätigt“ und
  einen Knopf „Bestätigen“.

### Vorschläge

`add_vib_entries` füllt je Eintrag **genau einen** Vorschlag vor (nicht mehr bis zu drei)
und liefert alle Kandidaten mit Grund:

1. **Vorjahr** — dasselbe Vorhaben (gleicher normalisierter Name) war in einem früheren
   Bericht bestätigt zugeordnet → diese Projekte.
2. **VDE-Nummer** — gleiche „VDE Nr. x“ in Name/Beschreibung.
3. **Name** — Fuzzy-Match; das Präfix „Lfd. Vorhaben Nr. x –“ wird vor dem Vergleich
   entfernt.

`assignment_note` sagt „Automatischer Vorschlag (…), ungeprüft“, bis der Agent oder ein
Editor zuordnet. Für PFA-Abschnitte liefert `get_vib_entry` je offenem Abschnitt einen
Teilprojekt-Vorschlag mit Grund aus dem ganzen Teilbaum der zugeordneten Projekte
(Vorjahr → Abschnittsnummer → Ortsname, siehe Phase 8).

### MCP-Tools

Modul `mcp/tools/vib.py`; alle Tools prüfen das bestehende Recht `vib.import`.

| Tool | Art | Zweck |
|---|---|---|
| `list_vib_reports` | lesend | Berichte mit Jahr, Drucksache, Datum, Zählern (gesamt / zugeordnet / bestätigt) |
| `create_vib_report(year, drucksache_nr, report_date)` | schreibend | Bericht anlegen; gleiches Jahr → Fehler mit der vorhandenen id |
| `update_vib_report(report_id, changes)` | schreibend | Drucksache, Berichtsdatum korrigieren (W6) |
| `list_vib_entries(report_id, only_open?, search?)` | lesend | kompakte Liste: Abschnitt, Name, Kategorie, Projekte, Begründung, bestätigt |
| `get_vib_entry(entry_id)` | lesend | alle Felder, PFA-Zeilen mit id, Teilprojekt und Vorschlag |
| `add_vib_entries(report_id, entries[])` | schreibend | Vorhaben samt PFA-Zeilen anlegen, alles oder nichts; liefert Vorschläge |
| `update_vib_entry(entry_id, changes)` | schreibend | Felder korrigieren (Text, Status, Kenndaten, Kategorie, Name, Seite) |
| `set_vib_pfa_entries(entry_id, pfa_entries[])` | schreibend | PFA-Tabelle eines Vorhabens ersetzen |
| `assign_vib_entry(entry_id, project_ids, note)` | schreibend | Projekte (eins oder mehrere) mit Begründung; leere Liste löst die Zuordnung |
| `assign_vib_pfa(pfa_id, project_id)` | schreibend | PFA-Abschnitt einem Teilprojekt zuordnen oder lösen |
| `assign_vib_pfas(entry_id, items[])` | schreibend | mehrere PFA-Zeilen eines Vorhabens zuordnen (Phase 8) |
| `apply_vib_pfa_suggestions(report_id, entry_ids?)` | schreibend | starke PFA-Vorschläge (Vorjahr, Nummer) übernehmen (Phase 8) |
| `create_vib_pfa_subprojects(entry_id, items[])` | schreibend | Entwurfs-Teilprojekt je PFA-Abschnitt anlegen und zuordnen (Phase 8) |
| `delete_vib_entry(entry_id)` | löschend | Fehleintrag entfernen |
| `confirm_vib_report(report_id, entry_ids?)` | schreibend | offene Einträge mit Projekt bestätigen → Beobachtungen entstehen |

Bestehende Jahrgänge bleiben stehen (W3). Der Skill hat einen **Prüfmodus**: einen
vorhandenen Jahrgang durchgehen, Zuordnungen prüfen und mit Begründung korrigieren,
falsche Felder und Berichtsdaten richtigstellen, dann bestätigen.

### Skill

`.claude/skills/vib-import/SKILL.md` (`metadata: mcp: true`, kommt vom MCP-Server):

1. Bericht erkennen (Jahr, Drucksache, Datum der Drucksache), vorhandenen Bericht
   fortsetzen statt neu anlegen.
2. Vorhaben aus Abschnitt B (Schienenwege) einzeln erfassen: Sektionsnummer, Name wie in
   der Überschrift, Kategorie aus der Gliederung, Unterabschnitte nach ihren Überschriften,
   Kenndaten, PFA-Tabelle zeilenweise.
3. Status nur aus Projektstand/Planungsstand und den Terminen, nie aus Wörtern der
   PFA-Spalte „Entwurfsplanung“.
4. Zuordnen: Vorschlag prüfen, Teilprojekt-Ebene beachten, mehrere Projekte erlaubt,
   Begründung schreiben, Unklares offen lassen.
5. PFA-Abschnitte Teilprojekten zuordnen, wo es sie gibt.
6. Bestätigen, Bericht an den Nutzer: übernommen / selbst entschieden / offen.

### Entscheidungen Phase 7

| # | Datum | Entscheidung |
|---|---|---|
| W1 | 2026-10-20 | Neues Feld `vib_entry.confirmed`; nur bestätigte Einträge materialisieren. Backfill `true`. |
| W2 | 2026-10-20 | Upload bleibt als zweiter Weg; MCP + Skill hat Vorrang. Die OCR-Stufe bleibt Referenz der PDF-Vereinheitlichung. |
| W3 | 2026-10-20 | Vorhandene Jahrgänge bleiben; Prüfmodus im Skill korrigiert Zuordnungen und Felder. |
| W4 | 2026-10-20 | Begründung als `assignment_note` am Eintrag; Zuordnung bleibt m:n (mehrere Projekte je Vorhaben). |
| W5 | 2026-10-20 | Roadmap-Punkte des Review-Wegs (Original-PDF, OCR-Bilder, Phase 6) entfallen; „Lernen aus Zuordnungen“ wird für VIB durch den Vorjahres-Vorschlag gelöst. |
| W6 | 2026-10-20 | Der Agent trägt das Datum der Drucksache als `report_date` ein; der Prüfmodus korrigiert falsche Daten alter Jahrgänge. |

### Akzeptanzkriterien Phase 7

- [ ] Über MCP lässt sich ein VIB-Jahrgang vollständig erfassen: Bericht, Vorhaben mit
      PFA-Tabelle, Zuordnung mit Begründung (auch zu mehreren Projekten), Bestätigung.
- [ ] Ein unbestätigter Eintrag erzeugt keine Beobachtung; nach `confirm_vib_report`
      erscheinen sie.
- [ ] Bestehende VIB-Einträge sind nach der Migration bestätigt; der Projektfortschritt
      ändert sich nicht.
- [ ] Ein über MCP umgehängter Eintrag ist unbestätigt, bis er bestätigt wird.
- [ ] `add_vib_entries` füllt höchstens ein Projekt vor und nennt den Grund.
- [ ] Ohne `vib.import` verweigern die Tools den Zugriff.
- [ ] Der Upload-Weg funktioniert unverändert; seine Einträge sind bestätigt.

---

## Phase 8: PFA-Abschnitte → Teilprojekte (Vorschlag + Anlegen)

> Entschieden 2026-10-23 (Entscheidungen P1–P5 unten). Konzept der Zuordnung:
> `feature-project-progress.md` → „VIB-PFA-Abschnitte → Unterprojekte“.

### Ausgangslage (VIB 2023, Stand 2026-10-23)

171 PFA-Zeilen in 11 Vorhaben, **0** einem Teilprojekt zugeordnet. Der Vorschlag
(`suggest_subproject_for_pfa`) vergleicht `abschnitt_label + nr_pfa + oertlichkeit` per
SequenceMatcher mit den Namen der **direkten** Kinder der zugeordneten Projekte
(Schwelle 0.35). Stichproben aus dem Bestand:

| Vorhaben | Teilprojekte im Bestand | Heutiger Vorschlag |
|---|---|---|
| B.4.1.23 Karlsruhe–Basel (31 PFA) | Enkel unter 1504: „… Abschnitt 1 Karlsruhe – Rastatt Süd“, „Abschnitt 2-6“, „Abschnitt 7“, „8“, „9“ (`project_number` `2-005-V02-Abschnitt7`) | findet die Enkel nicht; PFA 1 → 1504 (Zwischenknoten), PFA 7.1 → „ABS Kehl – Appenweier“ (**falsch**) |
| B.4.1.8 Nürnberg–Erfurt (27 PFA) | 16 Kinder, `project_number` z. B. `BSWAG 2023 FD 4 PF 15-16`, `PF 11, 14`, `PFA 1+2`, `PF 23-25` | 6 richtig über den Namen; PFA 11 → „Teilmaßnahme 5“, PFA 14 → „Teilmaßnahme 4“ (**falsch**); 19 ohne Vorschlag, obwohl die Nummer passt |
| B.4.2.16 RRX (13 PFA) | „RRX Abschnitt 1 … 6“ | 9 richtig, 1.2 und 3.1/3.2 fehlen (Nummer passt) |
| B.4.1.1 VDE 1 (15 PFA) | 2 Kinder, eins davon praktisch das Oberprojekt selbst | 2 Vorschläge auf das Quasi-Duplikat (**falsch**); für die Abschnitte gibt es keine Teilprojekte |

Befund: Die **Abschnittsnummer** ist das stärkste Signal und wird nicht genutzt; der
Teilbaum ist zu flach; der Namensvergleich ist zu großzügig und schlägt Zwischenknoten
und thematisch fremde Geschwister vor. Für einen Teil der Vorhaben (VDE 1, viele
abgeschlossene Altabschnitte) gibt es gar kein passendes Teilprojekt.

### Vorschlagslogik

Reihenfolge der Signale, jedes liefert einen **Grund** (`suggested_reason`) wie bei den
Vorhaben-Vorschlägen:

1. **Vorjahr** — dieselbe PFA-Zeile (gleiche normalisierte `nr_pfa`, sonst gleiche
   normalisierte `oertlichkeit`) im selben Vorhaben (gleiche Sektion oder `same_vib_name`)
   eines früheren **bestätigten** Berichts war einem Teilprojekt zugeordnet → dieses,
   sofern es noch im Teilbaum liegt. Grund „Vorjahr: VIB 20xx bestätigt“.
2. **Abschnittsnummer** — Nummern aus `nr_pfa` (`7.1`, `2–6`, `16a`, `3.0a`) gegen
   Nummern in Name **und** `project_number` des Kandidaten nach einem Schlüsselwort
   (`Abschnitt`, `PFA`, `PF`, `PA`, `StA`, `BA`), inkl. Listen und Bereichen
   (`PF 11, 14`, `PF 15-16`, `PF 23-25`, `PFA 1+2`, `Abschnitt 2-6`). Exakte Nummer
   schlägt Hauptnummer (`7.1` → „Abschnitt 7“). Grund „Abschnittsnummer 7.1 ↔ Abschnitt 7“.
3. **Name** — wie heute, aber normalisiert (`(a)`/`(e)`, `Bf`/`Hbf`, km-Angaben,
   Fußnotenziffern `¹ ² ⁵`, Strichvarianten), Schwelle **0.5** und Abstand zum
   Zweitbesten; nur Ortsnamen-Token zählen (kein Treffer allein über „VDE“, „ABS“,
   „Nürnberg“, wenn das im Oberprojekt-Namen steht). Grund „Namensähnlichkeit 0.62“.
4. **Geometrie** (vorgemerkt, P4 — nicht gebaut) — Endpunkte der Örtlichkeit („A–B“) auf
   Betriebsstellen abbilden (Namensabgleich, eingegrenzt auf die Bounding Box des
   Oberprojekts) und prüfen, ob beide Punkte nahe (≤ 1,5 km) an der GeoJSON-Linie eines
   Kandidaten liegen. Grund „Geometrie: A und B liegen auf dem Teilprojekt“.

**Kandidaten**: der ganze Teilbaum unter allen zugeordneten Projekten (rekursiv, ohne
die zugeordneten Projekte selbst). Bei gleicher Stärke gewinnt das **tiefere** Projekt
(Blatt vor Zwischenknoten); ein Zwischenknoten wird nur vorgeschlagen, wenn er die
Nummer genau trägt und keines seiner Kinder passt.

Erwartung aus den Stichproben (Nummer + Teilbaum, ohne Geometrie; nachgemessen wird beim
Bau mit Tests, die die Stichproben nachbilden): Bei Karlsruhe–Basel, Nürnberg–Erfurt und
RRX trägt fast jede Zeile eine Nummer, die ein Teilprojekt in Name oder `project_number`
führt; die falschen Treffer von heute entfallen, weil die Nummer vor dem Namen kommt und
die Namensschwelle steigt.

**Geometrie — Abwägung:** In den Stichproben bringt sie keinen Treffer, den Nummer und
Name nicht schon liefern; sie hilft dort, wo Teilprojekte weder Nummer noch Ortsnamen
tragen. Kosten: Betriebsstellen-Namen sind mehrdeutig („Freiburg“, Abzweige), Örtlichkeiten
oft keine zwei Orte („Bf Schwerin“, „ESTW Düsseldorf“, „Stadtgebiet Essen“), viele
Teilprojekte haben keine Geometrie. Entschieden: **nicht in dieser Phase**, als späteres
Signal vorgemerkt (P4).

Umsetzung: `tasks/vib_matching.py` (`suggest_subproject_for_pfa`, `project_section_numbers`,
`pfa_row_key`; rein, unit-getestet), Vorjahr und Teilbaum in `crud/vib_agent.py`
(`_PfaMatcher`). Normalisierung: `(a)`/`(e)`, km-Angaben und Fußnotenzeichen fallen weg;
Wörter aus Vorhaben- und Projektnamen sowie allgemeine Wörter („ABS“, „Abschnitt“,
„Stadtgebiet“ …) entscheiden nie. Schwach = Name, stark = Vorjahr oder eindeutige Nummer.
`get_vib_entry` liefert je offener Zeile `suggested_project_id`, `suggested_project_name`,
`suggested_reason`, `suggestion_strong` und unter `subprojects` den ganzen Teilbaum (mit
`depth`, `superior_project_id`, `is_draft`).

### Vorschläge übernehmen

Entschieden (P2): eigenes Tool `apply_vib_pfa_suggestions(report_id, entry_ids?)`
übernimmt **nur starke** Vorschläge (Vorjahr, eindeutige Abschnittsnummer) für offene
Zeilen — Vorbild `apply_infraplan_suggestions`. Es ist ein sichtbarer, prüfbarer Schritt
(Ergebnis je Zeile mit Grund); jeder geänderte Eintrag wird unbestätigt, bis
`confirm_vib_report` läuft. `add_vib_entries` füllt PFA-Zeilen **nicht** vor (kein
Automatismus ohne Prüfung). Dazu `assign_vib_pfas(entry_id, [{pfa_id, project_id}])` als
Sammelzuordnung (alles oder nichts; das Projekt muss im Teilbaum liegen).

### Teilprojekte aus PFA-Abschnitten anlegen

Bisher bewusst nicht („nur bestehende Unterprojekte“). Für Vorhaben ohne passende
Teilprojekte bleibt der Stand dann am Oberprojekt — als **eine** Phase für einen ganzen
Korridor.

| Option | Was | Für | Gegen |
|---|---|---|---|
| A | Nie anlegen (heute) | keine Projekt-Inflation | Stand bleibt plattgedrückt, wo Abschnitte auseinanderlaufen |
| B | **Auf Anforderung** per MCP: `create_vib_pfa_subprojects(entry_id, items[{pfa_ids, parent_id, name?, note?}])` legt je Item ein **Entwurfsprojekt** (`is_draft`, ohne Geometrie) unter `parent_id` an und ordnet die Zeilen zu | Vorbild Infraplan; der Agent bündelt mehrere Zeilen eines Abschnitts (z. B. alle „7.1“-Zeilen NBS/ABS) zu einem Teilprojekt; Mensch entscheidet | ein Tool mehr; Entwürfe müssen später gepflegt werden |
| C | Automatisch je PFA-Zeile | vollständig | 171 neue Projekte für 2023, viele Altabschnitte (1990er) ohne Erkenntniswert, Dubletten zu späteren Teilprojekten |

Entschieden **B** (P1), Tool `create_vib_pfa_subprojects(entry_id, items[{pfa_ids,
parent_id, name?}])`, Recht `vib.import` wie beim Infraplan-Vorbild (P5); Ergebnis je
Item (`ok`/`error`), ein Commit, Eintrag wird unbestätigt. Regeln:
- Nur **auf Wunsch des Nutzers** (Skill fragt, wie bei fehlenden Projekten in Schritt 4).
- `parent_id` ist ein Projekt des Vorhabens oder liegt darunter; die Zeilen gehören zum
  Vorhaben und sind noch keinem Teilprojekt zugeordnet.
- Granularität **Abschnitt, nicht Zeile**: Zeilen mit derselben Hauptnummer bzw.
  demselben `abschnitt_label` gehören in ein Teilprojekt.
- Nur anlegen, wo es den Stand verbessert: Abschnitte mit **unterschiedlichem** Stand
  im selben Vorhaben, laufende oder geplante Abschnitte. Vollständig in Betrieb
  genommene Altabschnitte bleiben am Vorhaben.
- Name: `abschnitt_label` bzw. „PFA <nr> <Örtlichkeit>“, Vorschlag aus dem Tool,
  überschreibbar; `project_number` bleibt leer.
- Geometrie optional danach über `route_project_geometry` (bestehendes Tool), nicht im
  Anlege-Tool.
- Entwürfe erscheinen in der Entwurfsliste (`list_projects(drafts="only")`) zur Pflege.
  Wie jedes Teilprojekt zählen sie in der Spanne des Oberprojekts mit (auch als Entwurf).
- **Bisheriges Blatt als Elternprojekt** (P3): Das Tool legt auch unter einem Projekt ohne
  Teilprojekte an. Dieses wird damit Zwischenknoten — sein eigener Stand (eigene
  Beobachtungen, nicht zugeordnete PFA-Zeilen) zählt nicht mehr, nur die Spanne seiner
  Teilprojekte (`feature-project-progress.md` → rekursive Aggregation). Das Ergebnis meldet
  das (`parent_was_leaf`, `warning`); was dann nachzuarbeiten ist, regelt der Skill
  (Schritt 5): übrige Zeilen desselben Vorhabens ebenfalls zuordnen oder anlegen, eigene
  Quellen des Elternprojekts ansehen, im Bericht nennen.

### Entscheidungen Phase 8

| # | Datum | Entscheidung |
|---|---|---|
| P1 | 2026-10-23 | Teilprojekte aus PFA-Abschnitten werden **auf Anforderung** über MCP angelegt (`create_vib_pfa_subprojects`): Entwurf ohne Geometrie, je Abschnitt (mehrere Zeilen bündelbar). Ersetzt „nur bestehende Unterprojekte“. |
| P2 | 2026-10-23 | Starke Vorschläge übernimmt ein eigenes Tool (`apply_vib_pfa_suggestions`); `add_vib_entries` füllt PFA-Zeilen nicht vor. Sammelzuordnung `assign_vib_pfas`. |
| P3 | 2026-10-23 | Anlegen unter einem bisherigen Blatt ist erlaubt; das Tool warnt, der Skill regelt das Nacharbeiten. |
| P4 | 2026-10-23 | Geometrie-Abgleich (Örtlichkeit → Betriebsstellen → Nähe zur Teilprojekt-Linie) vorgemerkt, nicht gebaut. |
| P5 | 2026-10-23 | `vib.import` genügt zum Anlegen der Entwürfe (wie `infraplan.import` bei `create_infraplan_subproject`). |

### Akzeptanzkriterien Phase 8

- [x] Vorschläge kommen aus dem ganzen Teilbaum; ein Enkel „Abschnitt 7“ wird für PFA 7.1
      vorgeschlagen, nicht ein fremdes Geschwister mit ähnlichem Namen.
- [x] Nummern in Name und `project_number` (Listen, Bereiche, `Abschnitt7`) zählen; exakt vor
      Hauptnummer, tiefer vor höher.
- [x] Eine im Vorjahr bestätigte Zuordnung wird mit Grund „Vorjahr“ vorgeschlagen.
- [x] Jeder Vorschlag nennt seinen Grund; Ortsnamen des ganzen Vorhabens entscheiden nicht.
- [x] `apply_vib_pfa_suggestions` übernimmt nur starke Vorschläge; der Eintrag ist danach
      unbestätigt.
- [x] `create_vib_pfa_subprojects` legt Entwürfe ohne Geometrie an, ordnet die Zeilen zu,
      weist fremde/zugeordnete Zeilen und Eltern außerhalb des Teilbaums je Item ab und
      warnt bei einem bisherigen Blatt.

---

## Nicht im Scope

- Automatischer Import ohne Human Review (auch über MCP: Bestätigen bleibt ein eigener Schritt)
- Extraktion von Pressemitteilungen oder externen Quellen
- ProjectProgress-Verknüpfung (separates Feature: `feature-project-progress.md`)

---

## Technische Hinweise

- `ai_result` (JSON-Blob) und `ai_extracted` (Boolean) sind bereits im DB-Modell vorhanden
- `VibDraftReport` speichert das rohe Parse-Ergebnis (Redis-unabhängig)
- Celery-Worker muss nach Parser-Änderungen neu gestartet werden (läuft lokal, nicht in Docker)
- pdfplumber bleibt als Basis-Extraktions-Library; PyMuPDF nur als letzte Option wenn
  bimodale Spaltenanalyse nicht ausreicht

### Persistenz-Vorrang: DB-Draft gewinnt über Redis

`GET /parse-result/{task_id}` priorisiert den DB-Draft über das ursprüngliche Celery-Ergebnis in Redis.

**Hintergrund:** `PATCH /draft/{task_id}` (Entwurf speichern) schreibt die Nutzer-Änderungen in `VibDraftReport.raw_result_json` — aber das Celery-Ergebnis in Redis ist unveränderlich. Würde man beim State `SUCCESS` das Redis-Ergebnis zurückgeben, wären gespeicherte Änderungen nach einem Seitenreload verloren.

**Reihenfolge in `get_vib_parse_result`:**
1. State `PENDING/STARTED/PROGRESS` → DB-Draft (Redis noch nicht fertig, aber Draft könnte schon vorhanden sein)
2. State `SUCCESS` → DB-Draft bevorzugt; Redis-Ergebnis nur als Fallback wenn kein Draft vorhanden
3. Fallback (Redis evicted, State zurück auf PENDING) → DB-Draft
