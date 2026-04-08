# Feature: VIB Import — Robuster Parser + KI-Extraktion

## Ziel

Den Verkehrsinvestitionsbericht (VIB) zuverlässig importieren. Die bisherige rein
regex-basierte Implementierung verliert regelmäßig Daten, weil das PDF ein
zweispaltiges Layout mit inkonsistenten Seitenstrukturen hat. Ziel ist eine
**Hybridarchitektur**: robuste Strukturerkennung aus dem Inhaltsverzeichnis +
LLM-basierte Inhaltsextraktion pro Vorhabenblock.

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
- [x] 4c: `tasks/vib_ocr.py` schreiben + Tests
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

## Phase 6: Post-Confirm KI-Extraktion → ProjectProgress (geplant)

Nach dem Bestätigen eines VIB-Imports kann ein Admin optional eine KI-gestützte Extraktion starten, die strukturierte Fortschrittsinformationen aus den VIB-Einträgen zieht und als `ProjectProgress`-Einträge speichert.

- **Voraussetzung:** `ProjectProgress`-Modell muss implementiert sein (→ `docs/features/feature-project-progress.md`). Bis dahin Zwischenspeicherung in `vib_entry.ai_result`.
- Celery-Task `extract_vib_progress` in `tasks/vib_ai_extraction.py`
- "KI-Extraktion starten"-Button nach Confirm (deaktiviert ohne `LLM_BASE_URL`)
- Pro VIB-Eintrag ein `ProjectProgress`-Eintrag (`source="vib_{year}"`)

---

## Nicht im Scope

- Automatischer Import ohne Human Review
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
