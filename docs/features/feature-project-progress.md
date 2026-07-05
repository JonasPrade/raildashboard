# Feature: Projektfortschritt / Planungsstand

> Diese Datei ersetzt die frühere, einfachere `ProjectProgress`-Skizze. Das hier
> beschriebene Modell subsumiert sie: Mehrquellen-Darstellung **mit** Konfliktauflösung
> (Hybrid-Ableitung), Parallelspuren, Lebenszyklus-Overlay, Unterprojekt-Aggregation,
> Dokument-Verknüpfung und Prognose.

## Kontext / Ziel

Der Planungsstand von Bahnprojekten ist schwer zu ermitteln: Es gibt mehrere Quellen
mit unterschiedlicher Verlässlichkeit, unterschiedlichem Projektzuschnitt und
unterschiedlicher Aktualität. Bisher gibt es **kein** Status-/Phasen-Feld am Projekt
(Greenfield; in `models/projects/project.py:118` liegt nur ein auskommentierter
`# project_progress`-Hinweis).

Ziel: Pro Projekt einen **abgeleiteten Planungsstand** anzeigen, der sich aus dem
Übereinanderlegen mehrerer Quellen ergibt, plus eine aufklappbare Aufschlüsselung,
welche Quelle was zum Stand sagt, plus eine Prognose (Restdauer der aktuellen Phase +
nächste Schritte). Darstellung als horizontaler Verlauf mit **Kreisen + Pfeilen**.

## Inhaltliches Modell

**Drei Dimensionen pro Projekt:**

1. **Leistungsphasen (Hauptspur, linear, immer vorhanden)** — geordnete Phasen:
   `NICHT_GESTARTET → VORPLANUNG (LP1-2) → GENEHMIGUNGSPLANUNG (LP3-4) → BAU → IN_BETRIEB`

2. **Begleitende Verfahren (bedingt, nur bei manchen Projekten; einfache Zustände
   `offen / läuft / abgeschlossen`):**
   - **Planfeststellung** — läuft *parallel* zu `GENEHMIGUNGSPLANUNG`; Flag pro Projekt
     „hat PF" (manche Projekte haben keine PF). Der Planfeststellungsbeschluss (PFB) ist
     zugleich das rechtliche Tor zum Bau und wird daher als **Meilenstein-Raute auf der
     Hauptzeitleiste** (Verbindung `GENEHMIGUNGSPLANUNG → BAU`) angezeigt: grün + Datum
     wenn abgeschlossen, blau wenn laufend, Umriss wenn offen. Nur sichtbar, wenn „hat PF"
     explizit gesetzt ist (keine Ableitung aus der Phase). Das Flag wird jedoch
     **automatisch gesetzt**, sobald PF-Daten erfasst werden (Zustand/Datum/Link/Notiz im
     Verfahren-Menü oder VIB-Evidenz) — man muss „hat PF" nicht separat anhaken.
   - **Parlamentarische Befassung** — Flag pro Projekt; **Voreinstellung aus Projektgruppe**
     (Bedarfsplan Schiene / BSWAG → an), manuell übersteuerbar. Wird — analog zur PFB-Raute —
     als **Meilenstein-Raute** („Parl.") auf der Verbindung `VORPLANUNG → GENEHMIGUNGSPLANUNG`
     angezeigt (grün/blau/Umriss + Datum).

   **Erfassung:** Beide Verfahren werden im Bearbeiten-Drawer über ein **Schaltmenü
   „Verfahren"** gepflegt (Switch pro Verfahren). **Nicht** über manuelle Beobachtungen —
   diese erfassen ausschließlich **Leistungsphasen** (MAIN). Das löst die frühere
   Doppelpflege auf.
   - **Planfeststellung**: Zustand, Datum, Anmerkung und **mehrere kommentierte URL-Links**
     (`pf_links: [{url, comment}]`, ersetzt den früheren Einzel-Link + die Dokument-ID-
     Verknüpfung).
   - **Parl. Befassung**: Beschluss-Zustand, Datum, Anmerkung und der **DIP-Link** zur
     Bundestagsdrucksache (`parl_drucksache_url`).

3. **Lebenszyklus-Overlay (orthogonal):** `AKTIV / PAUSIERT / ABGEBROCHEN`.
   Nicht in die Phasenkette gemischt; **nicht** standardmäßig angezeigt. Bei
   `PAUSIERT`/`ABGEBROCHEN` wird die **gesamte** Darstellung überblendet
   (Banner + abgeblendeter Stepper); die zuletzt bekannte Phase bleibt erhalten.

**Ableitung = HYBRID:** Ein Algorithmus erzeugt einen *Vorschlag* für die Headline-Phase.
Maßgeblich ist die **glaubwürdigste Beobachtung**: unter allen MAIN-Beobachtungen
über der Glaubwürdigkeitsschwelle gewinnt die mit der **höchsten effektiven Konfidenz**;
ihre Phase wird zum Vorschlag. **Konfidenz** entscheidet, nicht die Phasen-Reihenfolge —
so schlägt eine redaktionelle Hochkonfidenz-Korrektur (z. B. manuell „Genehmigungsplanung")
ein schwaches abgeleitetes Signal (z. B. FinVe→„Bau" mit niedriger Konfidenz). Gleichstand
in der Konfidenz löst sich zur höheren Phase auf. Der Vorschlag ist zusätzlich redaktionell
**übersteuerbar** (Phasen-Override). Konflikte werden nie weggerechnet, sondern im
Aufklappbereich transparent gezeigt. *Trade-off:* ein frisches, schwach gewichtetes Signal
kann ein älteres, höheres überstimmen — der Stand kann für Automatik-Quellen also
rückwärts gehen; das ist gewollt, damit aktuelle und menschliche Eingaben maßgeblich sind.

**Quellen → Beobachtungen:** Jede Quelle erzeugt eine oder mehrere *Beobachtungen*
`(source_type, track, asserted_state, observed_date, confidence)`.
Quellentypen: `VIB, FINVE, FULDA_RUNDE, BAUPORTAL, MEDIEN, MANUELL`.
- **VIB** und **FINVE** sind bereits importiert & m:n verknüpft → Beobachtungen werden
  daraus **abgeleitet/materialisiert** (nicht neu erfasst).
- **FULDA_RUNDE, BAUPORTAL, MEDIEN** existieren noch nicht → zunächst manuelle Erfassung.

**Vertrauensmodell:** Default-Vertrauen pro Quellentyp × Aktualitätsverfall
(`recency_decay`; wichtig für den „immer veralteten" VIB), pro Beobachtung übersteuerbar.

**Mehrere Abschnitte = Unterprojekte:** Projekte mit mehreren Planfeststellungs-
abschnitten sind bereits als **Unterprojekte** modelliert (`Project.superior_project_id`
/ `superior_project`). Der Fortschritt hängt am **Blatt-Projekt** (genau ein Stand). Ein
**übergeordnetes Projekt aggregiert** seine Kinder: Headline als **Spanne** (min..max der
Kinder), Kinder im Aufklappbereich gelistet.

**Beliebig tiefe Hierarchie (rekursive Aggregation):** Die Unterprojekt-Kette kann
mehr als zwei Ebenen tief sein (Projekt → Abschnitt → PFA …). Die Aggregation ist
deshalb **rekursiv über den gesamten Teilbaum**, nicht nur eine Ebene tief — sonst
zeigte ein Projekt 1. Stufe nur den (oft pauschalen) Eigenstand eines Zwischenknotens
statt der real auseinanderlaufenden Blätter darunter. Regeln (`aggregate_tree` in
`services/progress_derivation.py`, rein/unit-getestet):
- **Nur echte Blätter tragen einen Zustand.** Ein Knoten *ohne* Kinder steuert seine
  abgeleitete `effective_phase` bei (sofern `is_known`).
- **Jeder Zwischenknoten spannt die Blätter unter sich** — auf jeder Ebene die
  Spanne min..max über *alle* erreichbaren Blätter (nicht über seine eigenen
  Beobachtungen; ein Zwischenknoten hat keinen Eigenstand).
- **Ausnahme — manueller Override sticht:** Ein `manual_phase_override` an einem
  Zwischenknoten (auch am Top-Projekt) **fixiert den ganzen Teilbaum** auf diese eine
  Phase („der ganze Abschnitt ist im Bau") und kürzt die Rekursion ab. Abgeleitete
  VIB/FinVe-Beobachtungen an einem Zwischenknoten bleiben unberücksichtigt.
- **`is_known`** eines Zwischenknotens = mindestens ein Blatt darunter ist bekannt.
- **Darstellung:** Ist ein *direktes* Kind selbst ein Superior, zeigt seine Zeile in
  der Unterprojekt-Tabelle seine **eigene Sub-Spanne** (Badge „Vorplanung – Bau" +
  Marker „Gruppe") statt einer einzelnen, irreführenden Phase — der Drill-down bleibt
  über jede Ebene navigierbar. Schema-Felder dafür: `ProgressChildSchema.is_superior`
  /`span_min_phase`/`span_max_phase`.

Bäume sind klein → reine Python-Rekursion im Request (kein rekursives SQL); Blätter
werden über das bestehende Lazy-Resync-Fenster (24 h) frisch gehalten.

**VIB-PFA-Abschnitte → Unterprojekte (Status liegt am Blatt):** Ein VIB-Eintrag
(Vorhaben) enthält oft eine **Tabelle von Planfeststellungsabschnitten (PFA)** mit
*unterschiedlichem* Stand. Die drei Eintrags-Flags (`status_planung/bau/abgeschlossen`)
sind nur eine Vorhaben-Zusammenfassung und würden das ganze Projekt auf **eine** Phase
plattdrücken. Stattdessen wird jede PFA-Zeile per neuer FK **`vib_pfa_entry.project_id`**
einem **Blatt-Unterprojekt** zugeordnet (1:1, nullable, `SET NULL`):

- **Pro-PFA-MAIN-Ableitung** aus den (bisher ungenutzten) Abschnittsterminen:
  `inbetriebnahme` → `IN_BETRIEB`, sonst `baubeginn` → `BAU`, sonst `datum_pfb`
  (Planfeststellungsbeschluss) → `GENEHMIGUNGSPLANUNG`; kein Termin → kein MAIN-Beitrag
  (PF-Spur bleibt). `observed_date` = jeweiliges Termin-Datum, sonst Berichtsjahresende.
- **Routing:** Beim Sync eines Unterprojekts werden die ihm zugeordneten PFAs
  (`project_id == self`) direkt ausgewertet — unabhängig davon, an welches Projekt der
  übergeordnete VIB-Eintrag verknüpft ist. So liegt der Status am Blatt.
- **Suppression am Elternprojekt:** Hat ein VIB-Eintrag ≥1 auf ein Unterprojekt
  zugeordnete PFA, wird die **Eintrags-Sammel-Phase nicht mehr aufs Elternprojekt**
  geschrieben — der Superior bekommt seinen Stand allein über die Spanne der Kinder.
  Ohne Zuordnung verhält sich alles **rückwärtskompatibel** wie bisher.
- **Zuordnung per Vorschlag + Editor-Bestätigung:** Im VIB-Review/-Edit wird je PFA ein
  Unterprojekt vorgeschlagen (Fuzzy-Match `nr_pfa`/`abschnitt_label`/`oertlichkeit` gegen
  die Unterprojekt-Namen) und vom Editor bestätigt/korrigiert. Nicht zugeordnete Abschnitte
  bleiben „offen". Es werden nur **bestehende** Unterprojekte angeboten (kein Auto-Anlegen).

**Dokumente:** Hinter **Planfeststellung** und **Parlamentarischer Befassung** sollen sich
**Dokumente verlinken** lassen (bestehendes `Document`-Modell wiederverwenden).

**Prognose:** kombiniert BVWP-Dauern (`bvwp_duration_of_outstanding_planning/_build/
_operating`) + VIB-PFA-Termine (`baubeginn`, `inbetriebnahme`, `datum_pfb`) +
Fulda-Runde-Vorankündigungen → Restdauer der aktuellen Phase + nächste Schritte.

## Datenmodell (Backend)

Neue Dateien unter `apps/backend/dashboard_backend/models/projects/`, registriert in
`models/projects/__init__.py`; Enums in `models/projects/progress_enums.py`
(als `enum.Enum`, in DB als `String` gespeichert — wie `vib_entry.category`).

**Enums:** `MainPhase` (geordnet, mit `order`-Helfer für `max()`-Untergrenzen),
`ParallelState (OFFEN/LAEUFT/ABGESCHLOSSEN)`, `LifecycleStatus (AKTIV/PAUSIERT/
ABGEBROCHEN)`, `SourceType`, `ObservationTrack (MAIN/PF/PARL)`.

**`project_progress`** (1:1 zum Blatt-Projekt; ersetzt die auskommentierte Relation in
`project.py:118`):
- `project_id` (FK unique, CASCADE)
- `has_planfeststellung: bool`
- `parl_befassung_relevant: bool | None` (`None` = Gruppen-Default verwenden)
- `lifecycle_status: str` (default `AKTIV`)
- `computed_phase / computed_confidence / computed_at`
- `manual_phase_override: str | None`, `manual_override_note: str | None`
- `pf_state_override / parl_state_override: str | None`
- Parl.-Befassung-Detailblock (ein Satz pro Projekt): `parl_befassung_text: str | None`
  (Freitext), `parl_drucksache_url: str | None` (Link zur Bundestagsdrucksache),
  `parl_befassung_date: date | None`. Der **Beschluss** selbst ist der PARL-Zustand
  (`parl_state_override`), kein eigenes Feld.
- Planfeststellung-Detailblock (spiegelt den Parl.-Block): `pf_text: str | None`
  (Freitext), `pf_beschluss_url: str | None` (Link zum Planfeststellungsbeschluss),
  `pf_date: date | None`. Der PF-Zustand selbst bleibt `pf_state_override`.
- `updated_at`

**`progress_observation`** (eine Zeile je atomarer Aussage; manuell = persistent,
VIB/FinVe = materialisiert mit `is_derived=True` + Provenienz-FKs):
- `project_id` (FK, CASCADE, indiziert), `source_type`, `track`, `asserted_state`,
  `observed_date`, `confidence`, `note`
- Provenienz: `vib_entry_id`, `vib_pfa_entry_id`, `finve_id` (nullable, `SET NULL`)
- `is_derived: bool`, `created_at`, `created_by_user_id`, `username_snapshot`
  (Provenienz-Muster aus `change_log.py`)

**`progress_track_document`** (neue Association — Dokumente hinter PF/parl. Befassung):
- `project_id` (FK, CASCADE), `track` (`ObservationTrack`, hier PF/PARL),
  `document_id` (FK→`document.id`, CASCADE), UniqueConstraint über die drei Felder.
- Wiederverwendung des bestehenden `Document`-Modells (`models/projects/document.py`)
  + `document_to_project`-Muster.

**Migration:** `make migrate-create MSG="add project progress and observations"`
→ `make migrate`. Modelle vorher in `__init__.py` registrieren, damit Autogenerate sie
sieht. Backend-Python: `apps/backend/.venv/bin/python`.

## Ableitungs-Service

- **Reine Logik** in `services/progress_derivation.py` (neues Package, ohne DB-Session,
  unit-testbar): `derive_headline(observations, *, has_pf, parl_relevant, lifecycle)`.
  - Effektives Vertrauen je Beobachtung = `confidence ?? SOURCE_TYPE_DEFAULT_TRUST ×
    recency_decay(observed_date)`.
  - Hauptphase = Phase der MAIN-Beobachtung mit der **höchsten effektiven Konfidenz**
    (Gleichstand → höhere Phase); Konfidenz entscheidet, nicht die Phasen-Reihenfolge.
  - PF/PARL-Zustand nur ableiten, wenn Spur aktiv.
  - Lebenszyklus als Overlay-Flag zurückgeben (ändert Phasenwert nicht).
  - Output: `computed_phase`, `confidence`, `pf_state`, `parl_state`, Beitrag je Quelle
    (`was_decisive`), `effective_headline = manual_phase_override ?? computed_phase`.
- **DB-Zugriff** in `crud/projects/progress.py`:
  - `sync_derived_observations(db, project_id)` — löscht `is_derived=True`-Zeilen und
    regeneriert sie aus aktuell verknüpften VIB/FinVe-Records (**materialisieren**, nicht
    derive-on-read). Lazy bei stalem `computed_at` im GET + explizit per „recompute".
  - Mapping VIB: `status_planung→≥VORPLANUNG`, `status_bau→≥BAU`,
    `status_abgeschlossen→≥IN_BETRIEB` (Eintrags-Flags, am Elternprojekt unterdrückt
    sobald PFAs auf Unterprojekte zugeordnet sind); PFA-Felder → PF-Spur + Prognose **und**
    pro-PFA-MAIN am zugeordneten Unterprojekt (`inbetriebnahme`/`baubeginn`/`datum_pfb`).
  - Mapping FinVe: aktive Verknüpfung → `≥GENEHMIGUNGSPLANUNG/BAU`; Sammel-FinVe schwächer.
  - `get_aggregated_progress(db, superior_id)` — Spanne über Blatt-Kinder + Kinderliste.

## API

Neuer Router `api/v1/endpoints/project_progress.py`, eingebunden in `api/v1/api.py`
mit Prefix `/projects`. Neue Permission `progress.edit` in `core/permissions.py`
(+ Admin-Rollenbündel). GET offen, Mutationen hinter `require_permission("progress.edit")`.
Schemas in `schemas/projects/progress_schema.py` (`ConfigDict(from_attributes=True)`,
Enums als `Literal[...]`/str für saubere TS-Unions via `make gen-api`).

- `GET /projects/{id}/progress` → `ProjectProgressSchema` (effektive Headline, computed +
  override, Flags, Lebenszyklus, aufgelöste Parallelspuren inkl. verlinkter Dokumente,
  Quellen-Aufschlüsselung, Prognose; bei Superior: Spanne + `children[]`). Lazy-Resync bei
  stalem `computed_at`.
- `PATCH /projects/{id}/progress` → Flags, Lebenszyklus, manueller Phasen-Override,
  Spur-Overrides.
- `POST/DELETE /projects/{id}/progress/observations` → manuelle Beobachtungen
  (Löschen von `is_derived=True` verweigern).
- `POST/DELETE /projects/{id}/progress/tracks/{track}/documents` → Dokument-Verknüpfung
  hinter PF/parl. Befassung.
- `POST /projects/{id}/progress/recompute` → Force-Resync + Neuberechnung.

## Frontend

Neuer Komponentenbaum `features/projects/components/progress/`, eingehängt in
`ProjectDetail.tsx` (neue Sektion oben + TOC-Eintrag „Planungsstand"):
- `ProgressSection.tsx` — Wrapper (ChronicleCard/Headline), `useProjectProgress(projectId)`.
- `PhaseStepper.tsx` — horizontaler Custom-Stepper (5 Kreise + Pfeile/Chevrons), aktuelle =
  effektive Headline; bei Superior Spanne hervorheben. (Mantine `Stepper` ist für
  Custom-Pfeile unpraktisch → Flex-Row im Stil der vorhandenen Chips/Cards.)
- `ParallelLanes.tsx` — bedingte Sub-Spuren PF / parl. Befassung (`offen/läuft/
  abgeschlossen`) inkl. verlinkter Dokumente je Spur. Bei der parl. Befassung zusätzlich
  (read-only) der Detailblock: Datum, Link zur Bundestagsdrucksache, Freitext. Bearbeitet
  wird er im `ProgressEditDrawer` (Beschluss-Select = `parl_state_override`, Datum, Link,
  Anmerkung — Teil des Skalar-Entwurfs).
- `LifecycleOverlay.tsx` — Banner/Abblendung bei `PAUSIERT`/`ABGEBROCHEN`.
- `SourceBreakdown.tsx` — `<Collapse>` mit Beitrag je Quelle (Typ, Aussage, Datum,
  Vertrauen, „entscheidend"). **Rein lesend** (Anlegen/Löschen läuft im
  `ProgressEditDrawer`). Zusätzlich eine **Provenienz-Tabelle der manuellen
  Beobachtungen** (Quelle, Spur, Aussage, Datum, Notiz, **Erfasst von**, **Erfasst am**),
  damit nachvollziehbar ist, ob eine Übertragung aktuell oder veraltet ist
  (`username_snapshot` + `created_at` aus `progress_observation`). Dieselben Wer/Wann-Spalten
  auch in der Beobachtungstabelle des Drawers.
- `ForecastPanel.tsx` — Restdauer + nächste Schritte.

React-Query-Hooks in `shared/api/queries.ts`: `useProjectProgress`,
`useUpdateProjectProgress`, `useCreate/DeleteProgressObservation`,
`useLink/UnlinkTrackDocument`, `useRecomputeProgress` (Invalidate
`["project-progress", projectId]`). Typen via `make gen-api` → `types.gen.ts`.

### Bearbeitung im Drawer (Ansicht/Edit getrennt)

Die Inline-Bearbeitung war über `ProgressSection`/`SourceBreakdown`/`ParallelLanes`
verstreut und vermischte sich mit der Visualisierung. Stattdessen:

- `ProgressSection` ist **rein lesend** (Stepper, Spanne, Unterprojekte, Prognose,
  `ParallelLanes`/`SourceBreakdown` mit `canEdit={false}`) + Button **„Bearbeiten"**
  (gated `can("progress.edit")`).
- `ProgressEditDrawer.tsx` — rechter `size="xl"`-Drawer mit vier Abschnitten: Phase &
  Übersteuerung · Lebenszyklus & Kennzeichen · Manuelle Beobachtungen · Parallelspuren
  & Dokumente; Fuß: „Aus Quellen neu berechnen" + Speichern/Abbrechen.
- **Voller Entwurf:** alle Änderungen (Skalar-Felder, Beobachtungen anlegen/löschen,
  Dokumente verknüpfen/lösen) werden lokal gepuffert und erst beim **Speichern**
  abgespielt (ein Skalar-`PATCH` + die gepufferten Add/Delete/Link/Unlink-Calls),
  danach Query-Invalidate. Dirty-Guard beim Schließen, „Speichern" nur bei Änderungen aktiv.

### Erfassung beim Anlegen neuer Projekte

Der „Neues Projekt anlegen"-Wizard (`features/admin/new-project/`) hat einen eigenen
Schritt **„Planungsstand"** (`StepPlanungsstand.tsx`) zwischen „Eigenschaften" und
„FinVes". Er rendert dieselbe read-only `ProgressSection` inkl. „Bearbeiten"-Button →
`ProgressEditDrawer`, sodass der Stand mit denselben Mitteln wie in der Projektansicht
erfasst wird (kein eigener Code-Pfad). Die frühere einfache „Planungsphase"-Auswahl in
Step 3 (Eigenschaften) entfällt dadurch.

## Automatische Quellen-Importer (#46/#47/#48)

Nachgezogen in v0.0.5. Alle drei folgen demselben Muster wie VIB/FinVe:
**Roh-Tabelle → Provenienz-FK auf `progress_observation` → reiner `*_to_spec`-Mapper
in `progress_materialization.py` → eigener Zweig in `sync_derived_observations`**
(regenerieren-statt-derive-on-read, sonst löscht der 24-h-Lazy-Resync die Zeilen).
Quellentyp + Default-Trust existieren bereits (`SourceType`, `SOURCE_TYPE_DEFAULT_TRUST`:
BAUPORTAL 0.8, FULDA_RUNDE 0.7, MEDIEN 0.4). Abgeleitete Zeilen sind nicht hand-löschbar
und werden nicht ins Changelog geschrieben.

### DB-Bauportal (#47) — offene JSON-API

- **Akquise:** `GET https://bauprojekte.deutschebahn.com/api/getProjectsList` (kein Auth,
  ~295 Projekte). Kein Scraping, kein Detail-Endpoint nötig.
- **Roh-Tabelle `bauportal_status`:** `bauportal_id` (extern), `shorttitle`, `status_raw`
  (= `icon_title`), `projecttime_raw`, `url`, `lat`/`lng`, `parent_bauportal_id`, `raw_json`,
  `fetched_at`, `project_id` (nullable FK, zugeordnetes Match), `suggested_project_id`,
  **`confirmed`** (Bool, Default false).
- **Mapping `bauportal_to_spec`:** `icon_title` „…Bauphase" → BAU, „…Planungsphase" →
  VORPLANUNG (konservative Untergrenze), „…gemischter Projektphase"/„Gesamtprojekt…" → kein
  Beitrag (Parent aggregiert über Kinder). `projecttime`-Endjahr → optionaler
  Inbetriebnahme-Forecast. `observed_date = fetched_at`.
- **Pipeline (`tasks/bauportal.py`):** Fetch → Upsert je `bauportal_id` → Fuzzy-Match auf
  `Project.name` (`suggest_project_for_bauportal`, analog `vib_matching`) → `suggested_project_id`.
- **Review-UI = Fulda-Parität (`BauportalImportPage`):** Der Vorschlag wird beim Import direkt in
  `project_id` **vorbefüllt** (unbestätigt), statt nur als graue Nebenspalte zu erscheinen.
  Reihenfolge-unabhängige Suche (`filterProjectOption`), per-Zeile „Übernehmen"-Toggle
  (optimistische Zwischenspeicherung), Kopf-Button **„Alle übernehmen (N)"**
  (`POST /confirm-all` → `confirm_all`). Erst **`confirmed`** materialisiert die abgeleitete
  Beobachtung — `sync_derived_observations` filtert Bauportal jetzt auf `project_id AND confirmed`
  (wie Medien/Fulda). Migration `20260705001` backfillt `confirmed=true` für bestehende Matches, damit
  deren Beobachtungen erhalten bleiben. `PATCH /entries/{id}` (`update_entry`) setzt `project_id`
  und/oder `confirmed`; Löschen der Zuordnung nimmt automatisch die Bestätigung zurück.

### Medien/Presse (#48) — halb-automatisch

- **Roh-Tabelle `media_report`:** `url`, `publication`, `published_date`, `raw_text`,
  extrahierte Felder, `project_id` (bestätigt). Eingabe URL/Text → LLM-Extraktion
  (`tasks/vib_ai_extraction.py`-Muster) → Mensch-im-Loop-Bestätigung. Niedriger Trust 0.4,
  Zitat/URL in `note`.

### Fulda-Runde (#46) — Antwort auf Kleine Anfrage (PDF)

- **Wichtig:** Hochgeladen wird die **Antwort der Bundesregierung** (enthält die Projekt-Tabellen),
  nicht die Kleine Anfrage selbst (nur Fragen). Die Antwort gliedert Projekte nach **Leistungsphase**;
  die Frage-Überschrift über jeder Tabelle sagt, in welcher Phase die Projekte stehen
  (Spalten „Projekt"/„Abschnitt").
- **UI = zwei Flächen (Tabelle wie VIB, aber synchron):**
  1. **Übersicht** (`FuldaImportPage`, `/admin/fulda-import`): Upload (Jahr + PDF) **plus** eine
     **Tabelle der Jahrgänge** (`GET /year-summaries` → `list_year_summaries`: Jahr, Drs, total,
     confirmed). Einstiegs- und Browse-Fläche; Upload navigiert direkt in die Jahres-Detailansicht.
  2. **Jahres-Detail** (`FuldaYearDetailPage`, `/admin/fulda-import/year/:year`): die **5 festen
     Phasen-Tabellen** in fester Reihenfolge (`CATEGORY_ORDER`: *in Lph 1–2*, *Abschluss Lph 1–2*,
     *in Lph 3–4*, *Abschluss Lph 3–4*, *BauFinVe*; leere Phasen als „Keine Projekte"). Je Zeile
     Projekt/Unterprojekt zuordnen (Reihenfolge-unabhängige Suche `filterProjectOption`) + „Übernehmen"-
     Toggle; optimistische Zwischenspeicherung. Kopf-Button **„Alle übernehmen (N)"**
     (`POST /years/{year}/confirm` → `confirm_year`) bestätigt alle zugeordneten offenen Einträge auf
     einmal; danach weiter anpassbar. Geteilte Komponenten in `fuldaShared.tsx`. (Der frühere
     Schritt-für-Schritt-Review `FuldaReviewPage` wurde verworfen.)
- **Jahresbezogen (wie VIB):** Der Redakteur gibt beim Upload das **Jahr** an (`announcement_year`,
  NOT NULL, indiziert). Alles ist nach Jahr gefiltert (`GET /entries?year=`, `/years`,
  `/year-summaries`). Ein erneuter Upload desselben Jahres ersetzt nur die **offenen** Drafts
  (bestätigte bleiben). Ganze Jahrgänge löschbar (`DELETE /years/{year}` → `delete_year`,
  re-materialisiert betroffene Projekte). Fehlt ein Beobachtungsdatum, dient der 1. Januar des Jahres
  als `observed_date` (Recency-Decay).
- **Abschnitt → Unterprojekt:** Jede Zeile trägt neben `raw_name` (Spalte „Projekt" = Oberprojekt)
  den `abschnitt` (Spalte „Abschnitt"; bei Bullet-Listen der Teil nach dem Doppelpunkt). Beim Parsen
  matcht `suggest_projects_for_vib_entry` zunächst das Oberprojekt; ist der Abschnitt distinkt (nicht
  „Gesamtstrecke" o. Ä.), sucht `suggest_subproject_for_pfa` ein passendes **Unterprojekt** unter den
  Kindern (`superior_project_id`) und füllt dieses **Blatt** vor (Zustand am Blatt). Es werden **keine
  Unterprojekte angelegt** — gibt es keins, bleibt der beste Oberprojekt-Treffer vorausgewählt; der
  Redakteur korrigiert.
- **m:n-Projektzuordnung (wie VIB):** Link-Tabelle `fulda_announcement_to_project` (analog
  `vib_entry_project`). Vorausgewählte Treffer als `MultiSelect`, kein separates Vorschlag-Feld. Erst
  Bestätigen erzeugt je verknüpftem Projekt eine Beobachtung (`sync_derived_observations` JOINt die
  Link-Tabelle, nur `confirmed`-Zeilen).
- **Roh-Tabelle `fulda_announcement`:** Jahr, Roh-Name, **Abschnitt**, Kategorie, angekündigte Phase,
  Quelle/Datum + m:n-Link zu Projekten. OCR (`vib_ocr.extract_full_pdf_text`) + LLM-Extraktion.
- **Mehrstufige Extraktion — LLM ordnet nur Phasen zu:** Enger Auftrag: jede Projektliste **anhand
  ihrer Frage-Überschrift** genau einer von fünf Kategorien zuordnen (Katalog in
  `FULDA_CATEGORY_LABELS`) und je Zeile `{category, project_name, abschnitt}` liefern (Projektname
  **wortwörtlich**; Abschnitt Pflicht — in Bullet-Listen „X: Y" wird X=Projekt, Y=Abschnitt). Kein
  Fragenummer-Raten mehr (der frühere, unzuverlässige Ansatz). Der Prompt erzwingt **Exklusivität**
  (eine Liste → genau eine Kategorie, keine Mehrfachausgabe) und „keine Liste → keine Einträge" für
  Fragen, die nur auf Anlagen verweisen — gegen die beobachtete Duplikation einer Tabelle nach
  BauFinVe. `normalize_items` validiert gegen `FULDA_CATEGORIES` und dedupt je (Name, Abschnitt,
  Kategorie). Kategorie→Phase (`FULDA_CATEGORY_PHASE`): IN_LPH_1_2→Vorplanung, COMPLETED_LPH_1_2 &
  IN_LPH_3_4→Genehmigungsplanung, COMPLETED_LPH_3_4 & HAS_BAUFINVE→Bau.
- Termine fließen über den bestehenden Seam `_build_forecast_for_project` (FULDA_RUNDE +
  `observed_date`) in die Prognose. Debug: `scripts/dump_fulda_parse.py <pdf>`.

### Fehlendes Projekt → Projektentwurf anlegen & verknüpfen

Fällt beim Review auf, dass ein zuzuordnendes Projekt **noch gar nicht existiert**, kann es direkt
aus dem Importer heraus als **Projektentwurf** angelegt und sofort mit dem Eintrag verknüpft werden —
statt den Import zu verlassen und das Projekt separat anzulegen.

- **Wiederverwendbare Komponente** `features/projects/CreateDraftProjectModal.tsx`: Name (aus dem
  Roh-Titel/Abschnitt vorbelegt) + optionales **Überprojekt** (`ProjectSearchSelect`). Legt das
  Projekt über die **bestehende** Projekt-Infrastruktur als Entwurf an (`POST /projects/` mit
  `is_draft = true`, `superior_project_id`) und gibt den erzeugten Entwurf per `onCreated` zurück, damit
  der Aufrufer ihn an seinen Eintrag hängt. Kein neues Backend nötig — Entwürfe leben schon unter
  `/admin/drafts` (`GET /projects/drafts`, `POST /projects/{id}/finalize`) und sind aus der
  öffentlichen Liste/Karte ausgeblendet.
- **Verknüpfung je Importer** (Link „Projekt fehlt?" an jeder Zuordnung):
  - **Bauportal:** setzt `project_id` des Eintrags (unbestätigt — Redakteur prüft/übernimmt danach).
  - **Fulda-Runde:** hängt den Entwurf an die m:n-Zuordnung (`project_ids`) der Zeile.
  - **Haushalt (VE-Linie):** hängt den Entwurf an die FinVe-Zuordnung (Haupt-`project_ids` bzw. an eine
    SV-Erläuterungs-Unterzeile).
- **Fertigstellen später:** Der Entwurf wird auf dem Drafts-Board vervollständigt und finalisiert
  (`is_draft = false`); die Importer-Verknüpfung bleibt bestehen.

## Implementierungsreihenfolge (Phasen-Rollout)

1. **Modell + manuelle Erfassung + Visualisierung**: Tabellen/Enums, CRUD, GET/PATCH/
   Observation-Endpoints, `progress.edit`, reine Ableitung über manuelle Beobachtungen +
   Flags + Lebenszyklus, voller Stepper, Superior-Aggregation (Spanne), Dokument-Verknüpfung.
2. **VIB/FinVe-Ableitung**: `sync_derived_observations`, Lazy-Resync, `recompute`,
   Provenienz im Breakdown.
3. **Prognose**: `ProgressForecastSchema` aus BVWP-Dauern + VIB-PFA-Terminen + Fulda.
4. **Neue externe Quellen**: reichere manuelle Erfassung für FULDA_RUNDE/BAUPORTAL/MEDIEN,
   dann eigene Importer (`is_derived`): Bauportal (#47), Medien (#48), Fulda-Runde (#46).

## Erwartete Termine (manuelle Prognose-Einträge)

**Ziel:** Redakteure sollen erwartete Phasentermine (insbesondere die erwartete
**Inbetriebnahme**) manuell erfassen können — wie die manuellen Leistungsphasen-
Beobachtungen, aber als **„erwartet"** statt „beobachtet/erreicht". Heute kommen
Inbetriebnahme-/Phasentermine nur aus VIB-PFA, BVWP-Dauern und Fulda-Runde; ein
direkter, redaktioneller Zukunftstermin fehlt.

**Kernunterscheidung:** Eine reguläre Beobachtung behauptet einen *aktuell erreichten*
Zustand (Untergrenze für die Headline-Phase). Ein **erwarteter** Eintrag behauptet,
dass eine Phase erst *künftig* erreicht wird — er darf die aktuelle Phase **nicht**
hochziehen, sondern speist ausschließlich die **Prognose**.

**Datenmodell:** neues Flag `is_expected: bool` (default `False`, `server_default
"false"`) auf `progress_observation`. Ein erwarteter Eintrag nutzt dieselben Felder:
`track=MAIN`, `asserted_state` = Zielphase, `observed_date` = erwartetes Datum,
`source_type=MANUELL`, optional `note`. Migration via `make migrate-create`.

**Ableitung (`derive_headline`):** Beobachtungen mit `is_expected=True` werden aus der
Headline-/`computed_phase`-Ableitung **ausgeschlossen** (kein Untergrenzen-Beitrag,
kein Vertrauensbeitrag). Sie tauchen weiterhin in der Provenienz-/Quellen-Tabelle auf,
klar als „erwartet" markiert.

**Prognose (`build_forecast` / `_build_forecast_for_project`):** erwartete Einträge
fließen als neue, **höchstpriorisierte** Quelle ein — *manuell übersteuert immer*.
Neuer Parameter `manual_expected: list[(MainPhase, date)]`; im `concrete`-Aufbau
**nach** VIB-PFA/Fulda gesetzt, sodass er bestehende Einträge überschreibt (nicht nur
Lücken füllt). Quelle-Label `"Manuell"` im `ForecastStep` und farblich im
`ForecastPanel` (`SOURCE_COLOR`). CRUD lädt manuelle `is_expected=True`-MAIN-Beobachtungen
mit Datum analog zu `fulda_obs`.

**Sichtbarkeit:** wie der übrige Planungsstand **öffentlich** (GET offen). Eingabe nur
mit Permission `progress.edit`.

**Frontend (`ProgressEditDrawer`):** der Abschnitt „Manuelle Beobachtungen" erhält im
`ObservationDraftForm` einen Schalter **„erwarteter Termin"**. Bei aktivem Schalter wird
`is_expected=true` mitgeschickt; Label/Beschreibung verdeutlichen „erwartet" statt
„erreicht". In der Beobachtungstabelle (Drawer) und im `SourceBreakdown` ein Badge
„erwartet". `ProgressObservationCreate`/`ProgressObservationSchema` um `is_expected`
erweitern → `make gen-api`.

## Offene Punkte / Risiken / Edge Cases

- **`parl_befassung_relevant`-Default**: `project_group` hat kein stabiles Typ-Flag →
  Identifikation von „Bedarfsplan Schiene / BSWAG" per `short_name`/id klären; nullable
  Override hält Re-Gruppierung live.
- **VIB-Datumsfelder sind Freitext** (`baubeginn`, `datum_pfb`, …) → tolerantes Parsen +
  Fallback „nicht parsebar" (geringes Recency-Gewicht).
- **Echte Phasen-Rückschritte** (Reset): per höher-konfidenter (frischer/manueller)
  Beobachtung oder Phasen-Override / Lebenszyklus auffangen.
- **Sammel-FinVe** (`is_sammel_finve`, jahres-skaliert) schwächer gewichten.
- **Superior ohne/gemischte Kinder** sowie Superior, das selbst Blatt ist (keine Kinder).
- **Derived-Observation-Churn**: regenerierte `is_derived`-Zeilen nicht ins Changelog;
  nur manuelle Edits auditieren.
- **Staleness-Fenster** für Lazy-Resync definieren (nicht bei jedem GET neu rechnen).
- **Sichtbarkeit**: GET offen (wie BVWP) oder login-gated (wie VIB) — entscheiden.

## Akzeptanzkriterien

> Stand: **Phasen 1–4 umgesetzt** (Issues #41/#43/#44/#45). Phase 1: Modell + manuelle
> Erfassung + Visualisierung. Phase 2: VIB/FinVe-Materialisierung + Lazy-Resync. Phase 3:
> Prognose. Phase 4: reichere manuelle Erfassung (Quellentyp + Vertrauen). Offen bleiben nur
> eigene **automatische** Importer für FULDA_RUNDE/BAUPORTAL/MEDIEN (keine externen APIs vorhanden).

- [x] Headline-Phase wird aus den verknüpften Quellen abgeleitet und ist redaktionell
  übersteuerbar; der Override gewinnt über den berechneten Wert.
- [x] Parallelspuren PF / parl. Befassung werden nur bei zutreffenden Projekten angezeigt;
  parl. Befassung wird per Projektgruppe (`short_name`-Prefix `BSWAG`) vorbelegt.
- [x] `PAUSIERT`/`ABGEBROCHEN` überblendet die gesamte Darstellung.
- [x] Aufklappbereich zeigt je Quelle Aussage, Datum und Vertrauen; Konflikte bleiben sichtbar.
- [x] Übergeordnete Projekte zeigen eine Spanne + ihre Unterprojekte; die Spanne wird
  **rekursiv über beliebig tiefe** Unterprojekt-Ebenen gebildet (Blätter tragen den Stand,
  manueller Override am Zwischenknoten fixiert den Teilbaum). Direkte Kinder, die selbst
  Superior sind, zeigen ihre eigene Sub-Spanne.
- [x] Dokumente lassen sich hinter PF und parl. Befassung verlinken.
- [x] VIB/FinVe-Beobachtungen werden materialisiert (`sync_derived_observations`) und sind
  nicht manuell löschbar; Lazy-Resync bei stalem `computed_at` (24h) + `recompute`.
- [x] Prognose: Restdauer der aktuellen Phase + nächste Schritte aus BVWP-Dauern +
  VIB-PFA-Terminen (tolerantes Parsen) + Fulda-Runde-Beobachtungen.
- [x] Reichere manuelle Erfassung: Quellentyp (MANUELL/FULDA_RUNDE/BAUPORTAL/MEDIEN) +
  Vertrauens-Override pro Beobachtung.

### Umsetzungsdetails (Phasen 2–4)

- **Materialisierung** (`services/progress_materialization.py`, rein/unit-getestet):
  VIB-Status → stärkste MAIN-Untergrenze; PFA → PF-Spur (`datum_pfb` → ABGESCHLOSSEN,
  sonst LAEUFT); reguläre FinVe → MAIN = Bau. **Sammel-FinVe**: Phase aus der Leistungsphase
  im Namen (`parse_sammel_finve_phase`: Lph 1/2 → VORPLANUNG, Lph 3/4 → GENEHMIGUNGSPLANUNG;
  **nicht** auf EKrG-Nummern wie „3/2010" triggern), sonst manuelle Zuordnung über
  `finve.progress_phase` (Admin-Seite „Sammel-FinVe Phasen"); ohne erkennbare/zugeordnete
  Phase **keine** Beobachtung. Alle Sammel-FinVe schwächer (`confidence=0.35`).
  PFA-Evidenz schaltet `has_planfeststellung` automatisch ein. Beobachtungsdatum = VIB-
  **Report-Jahr** (das Freitext-`report_date` ist unzuverlässig).
- **Recency-Floor** auf `0.3` angehoben, damit strukturierte Quellen (VIB/FinVe) über Jahre
  **glaubwürdig** bleiben (über der Schwelle), während veraltete Medien-Beobachtungen
  darunter fallen können. Der Floor hält eine alte Beobachtung im Rennen; ob sie die
  Headline entscheidet, hängt nun von ihrer Konfidenz relativ zu den anderen ab.
- **Prognose** (`services/progress_forecast.py` + `services/progress_dates.py`): konkrete
  Termine (PFA/Fulda) schlagen BVWP-Schätzungen; Restdauer wird humanisiert.

### Superior-Darstellung & „Unbekannt"-Status (Review-Feedback)

- **`is_known`** (Ableitungs-Ergebnis + Schema, leaf & Kind): `False`, wenn es weder eine
  glaubwürdige MAIN-Beobachtung noch einen manuellen Override gibt. Frontend zeigt dann
  **„Unbekannt"** statt des `NICHT_GESTARTET`-Fallbacks („wissen wir nicht" ≠ „nicht gestartet").
- **Superior-Spanne** wird **rekursiv** nur über **bekannte Blätter** des gesamten Teilbaums
  gebildet (siehe „Beliebig tiefe Hierarchie" oben); sind alle Blätter unbekannt, entfällt die
  Spanne („Status der Unterprojekte unbekannt"). Ein manueller Override am Superior fixiert
  stattdessen eine Einzelphase („Gesamter Abschnitt: …").
- **Unterprojekt-Tabelle** (`SubprojectsTable.tsx`): durchsuchbar, mit Status-Verteilungs-Chips
  (inkl. „Unbekannt"-Bucket), ersetzt die frühere Kinderliste im Aufklappbereich.
- **Phasen-Hover** im `PhaseStepper`: Tooltip + Zähler-Badge listen die Unterprojekte je Phase.

### Entscheidungen (Phase 1)

- **Sichtbarkeit `GET /progress`:** offen (wie BVWP); nur Mutationen hinter `progress.edit`.
- **`parl_befassung_relevant`-Default:** Mitgliedschaft in einer Projektgruppe mit
  `short_name`-Prefix `BSWAG` (`crud/projects/progress.py:BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX`);
  nullable Override bleibt maßgeblich.
- **Staleness-Fenster (Lazy-Resync, Phase 2):** `STALENESS_WINDOW = 24h`
  (`services/progress_derivation.py`), in Phase 1 noch ungenutzt.

## Verifikation

- Backend-Tests: `cd apps/backend && .venv/bin/python -m pytest` — Unit-Tests für
  `derive_headline` (Untergrenzen, Recency-Verfall, Lebenszyklus-Overlay, Superior-Spanne)
  und Endpoint-Tests (PATCH-Override gewinnt, derived nicht löschbar). Neue Tabellen ins
  Test-Schema (`TABLES`) eintragen.
- Migration lokal anwenden (`make migrate-create` → `make migrate`), Modelle vorher
  registriert.
- API-Client: `make gen-api` nach Schemas.
- End-to-end manuell: Projekt mit Unterprojekten → Stepper + Parallelspuren +
  Aufklappbereich; Projekt auf `PAUSIERT` → Overlay; Dokument hinter PF verlinken;
  Override setzen → gewinnt über computed.
