# Feature: Projektfortschritt / Planungsstand

> Diese Datei ersetzt die frühere, einfachere `ProjectProgress`-Skizze. Das hier
> beschriebene Modell subsumiert sie: Mehrquellen-Darstellung **mit** Konfliktauflösung
> (Hybrid-Ableitung, Konfliktliste im Admin-Bereich), Parallelspuren, Lebenszyklus-Overlay, Unterprojekt-Aggregation,
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

**Ableitung = HYBRID** (Regel neu gefasst 2026-10-22): Ein Algorithmus erzeugt einen
*Vorschlag* für die Headline-Phase, der redaktionell **übersteuerbar** bleibt (Phasen-Override).
Beobachtungen sind von zweierlei Art:

- **Untergrenzen** (FinVe inkl. Sammel-FinVe): „mindestens diese Phase“. Eine FinVe für Bau
  bleibt wahr, egal wie alt — Untergrenzen **veralten nicht** und heben die Phase nur an. Gegen
  einen neueren Statusbericht, der das Projekt weiter sieht, entscheiden sie nie.
- **Statusberichte** (VIB, Infraplan, GVFG-Bundesprogramm, Bauportal, Fulda-Runde, Medien, manuell):
  Stand zum jeweiligen Datum. Der **neueste** Bericht gewinnt; nur innerhalb von **einem Jahr**
  vor dem neuesten Bericht entscheidet das **Vertrauen** (explizite Konfidenz, sonst
  Quellen-Default — ohne Altersabschlag), Gleichstand → höhere Phase.

**Rückstufung = Konflikt:** Meldet ein neuerer Bericht eine **niedrigere** Phase als ältere
Angaben (Untergrenze oder älterer Bericht), stuft er nur zurück, wenn sein Vertrauen
mindestens so hoch ist wie das jeder widersprechenden Beobachtung (z. B. Infraplan 0.85 gegen
FinVe 0.7) oder wenn er manuell erfasst ist. Sonst bleibt die höhere Phase stehen (z. B. VIB 0.6
oder Medien 0.4 gegen FinVe 0.7). In beiden Fällen — außer bei manuellen Einträgen, die eine
redaktionelle Entscheidung sind — wird ein **Konflikt** gemeldet: im Projekt als Hinweis (für
Bearbeitende), gesammelt unter **Admin → „Planungsstand-Konflikte“**
(`/admin/planungsstand-konflikte`, `GET /api/v1/admin/progress-conflicts`, Recht
`progress.edit`). Ein Phasen-Override löst den Konflikt auf. Anlass: Eine 15 Jahre alte FinVe
(„Bau“) schlug den VIB 2023 („In Betrieb“), weil beide auf dem Recency-Floor lagen und dann nur
noch das Grundvertrauen zählte.

**Quellen → Beobachtungen:** Jede Quelle erzeugt eine oder mehrere *Beobachtungen*
`(source_type, track, asserted_state, observed_date, confidence)`.
Quellentypen: `VIB, FINVE, FULDA_RUNDE, BAUPORTAL, MEDIEN, INFRAPLAN, GVFG, MANUELL`
(Infraplan: `feature-infraplan-import.md`; GVFG: Abschnitt „Planungsstand aus dem
GVFG-Bundesprogramm“ unten).
- **VIB** und **FINVE** sind bereits importiert & m:n verknüpft → Beobachtungen werden
  daraus **abgeleitet/materialisiert** (nicht neu erfasst).
- **FULDA_RUNDE, BAUPORTAL, MEDIEN** haben inzwischen eigene Importer; die Fulda-Runde ist
  keine manuelle Quelle mehr (`feature-fulda-import.md`).

**Vertrauensmodell:** Default-Vertrauen pro Quellentyp, pro Beobachtung übersteuerbar. Die
Aktualität wirkt **nicht** als Gewicht, sondern über die Datumsreihenfolge (neuester Bericht
gewinnt). Trust × `recency_decay` (Floor 0.3) entscheidet nur noch, ob ein Statusbericht
überhaupt **glaubwürdig** ist (Schwelle 0.15): alte Medienmeldungen fallen heraus, VIB bleibt
drin. Untergrenzen veralten nicht.

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
- **Zuordnung per Vorschlag + Editor-Bestätigung:** Im VIB-Review/-Edit bzw. über MCP
  (`get_vib_entry`, `assign_vib_pfa`, `feature-vib-import.md` → Phase 7) wird je PFA ein
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
- Termin-Cache für Listen und Filter: `construction_start_date/_precision`,
  `commissioning_date/_precision` (→ „Datumsqualifikation“)
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
  `observed_date` (Sortierwert), `date_precision` (EXACT/MONTH/YEAR/NOT_BEFORE/ASSUMED,
  Default EXACT), `date_label` (optional), `confidence`, `note`
- Provenienz: `vib_entry_id`, `vib_pfa_entry_id`, `finve_id` (nullable, `SET NULL`)
- `is_derived: bool`, `created_at`, `created_by_user_id`, `username_snapshot`
  (Provenienz-Muster aus `change_log.py`)

**Änderungsprotokoll:** Alle nutzergetriebenen Planungsstand-Änderungen (PATCH,
Beobachtung anlegen/löschen, Dokument verknüpfen/lösen) landen im Projekt-`change_log`
mit Feldpräfix `progress.` — als Historie ohne Revert. Materialisierte Beobachtungen
aus den Importen (`sync_derived_observations`) werden nicht protokolliert.

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
  - Vertrauen je Beobachtung (`trust`) = `confidence ?? SOURCE_TYPE_DEFAULT_TRUST`;
    Glaubwürdigkeit (`effective_confidence`) = Vertrauen × `recency_decay(observed_date)`,
    bei Untergrenzen (`LOWER_BOUND_SOURCES` = FinVe) ohne Verfall.
  - Hauptphase: neuester glaubwürdiger Statusbericht, innerhalb `TRUST_WINDOW` (365 Tage)
    vor ihm entscheidet das Vertrauen; Untergrenzen heben nur an; Rückstufung nur bei
    Vertrauen ≥ Widerspruch oder MANUELL, sonst gehalten — beides als `PhaseConflict`
    gemeldet (außer MANUELL; ein Phasen-Override löscht den Konflikt).
  - PF/PARL-Zustand nur ableiten, wenn Spur aktiv.
  - Lebenszyklus als Overlay-Flag zurückgeben (ändert Phasenwert nicht).
  - Output: `computed_phase`, `confidence`, `pf_state`, `parl_state`, Beitrag je Quelle
    (`was_decisive`, `trust`, `is_lower_bound`, `in_conflict`), `conflict`, `effective_headline = manual_phase_override ?? computed_phase`.
- **DB-Zugriff** in `crud/projects/progress.py`:
  - `sync_derived_observations(db, project_id)` — löscht `is_derived=True`-Zeilen und
    regeneriert sie aus aktuell verknüpften VIB/FinVe-Records (**materialisieren**, nicht
    derive-on-read). VIB nur aus **bestätigten** Einträgen (`vib_entry.confirmed`, seit
    2026-10-20; über MCP geschriebene Einträge sind bis zum Bestätigen offen). Lazy bei stalem `computed_at` im GET + explizit per „recompute".
  - Mapping VIB: `status_planung→≥VORPLANUNG`, `status_bau→≥BAU`,
    `status_abgeschlossen→≥IN_BETRIEB` (Eintrags-Flags, am Elternprojekt unterdrückt
    sobald PFAs auf Unterprojekte zugeordnet sind); PFA-Felder → PF-Spur + Prognose **und**
    pro-PFA-MAIN am zugeordneten Unterprojekt (`inbetriebnahme`/`baubeginn`/`datum_pfb`).
  - Mapping FinVe: aktive Verknüpfung → Untergrenze `GENEHMIGUNGSPLANUNG/BAU`; Sammel-FinVe
    mit geringerem Vertrauen (0.35), also von jedem Bericht rückstufbar.
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
- `ProgressSection.tsx` — Wrapper (`Paper`/`Title`), `useProjectProgress(projectId)`.
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
  **Alter**; für Admins zusätzlich Vertrauen ohne Altersabschlag und die Marken
  „entscheidend“, „Untergrenze“, „Konflikt“). Ein Konflikt erscheint für Bearbeitende als
  Hinweis über dem Stepper. **Rein lesend** (Anlegen/Löschen läuft im
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

### Liste & Karte: Phasen-Badge und Phasen-Filter (#9/#10)

**Backend.** Die schlanke Projektgruppen-Liste (`GET /api/v1/project_groups/` und
`GET /api/v1/project_groups/{id}`, siehe `feature-slim-project-groups.md`) — die einzige
Datenquelle für Karten- **und** Listenansicht auf `/` — trägt pro Projekt zwei zusätzliche
Felder in `ProjectListItem`:

- `headline_phase: MainPhase | null` — aus der **gespeicherten** `project_progress`-Zeile:
  `manual_phase_override`, sonst `computed_phase`
  (`services/progress_derivation.py:stored_headline_phase`). `null`, wenn es keine Zeile gibt
  **oder** der Stand unbekannt ist: die Ableitung speichert bei fehlender glaubwürdiger
  MAIN-Beobachtung `NICHT_GESTARTET` mit Konfidenz `0.0` als Fallback — das wird wie
  `is_known = false` als „unbekannt" gemeldet, nicht als „nicht gestartet".
- `lifecycle_status: LifecycleStatus | null` — `null` ohne Zeile.

Geladen wird **gebündelt**: ein zusätzliches `selectinload(Project.progress)` im Loader
(`crud/projects/project_groups.py:_with_projects`) — ein `SELECT … WHERE project_id IN (…)`
für alle Projekte aller Gruppen, beschränkt auf die vier gelesenen Spalten. `Project.progress`
ist eine `viewonly`-Relation mit `lazy="raise"`; der Schema-Validator liest sie nur, wenn sie
geladen wurde, und löst nie ein Lazy-Load aus. Die Liste liest nur den Cache: sie ruft weder
die Ableitung noch den Lazy-Resync (`_ensure_fresh`) auf, legt keine Zeilen an und schreibt
nichts. Veraltete Caches werden weiterhin beim Öffnen der Detailseite bzw. per „Neu
berechnen" aufgefrischt. Die ETag-Revalidierung bleibt korrekt, weil der Hash über den
Payload inklusive Phase gebildet wird. `PATCH /project_groups/{id}` liest die Gruppe nach
dem Update über denselben Loader neu ein.

*Einschränkung:* Übergeordnete Projekte liefern die Phase **ihrer eigenen** Zeile, nicht die
auf der Detailseite gezeigte Spanne über die Unterprojekte (die bräuchte die rekursive
Aggregation pro Request). Eine Phasen-Verteilung für Parent-Projekte war #11 und ist nicht
Teil dieses Pakets.

**Frontend.**

- **Filter „Planungsphase"** auf `/` für Karte und Liste (`PhaseFilterSelect`, Mantine
  `MultiSelect`, Mehrfachauswahl). Optionen: die fünf Hauptphasen (Labels aus `phaseMeta.ts`)
  plus **„Unbekannt"** für Projekte ohne `headline_phase` — sie sind so gezielt auswählbar statt
  stillschweigend herauszufallen. Mehrere Phasen werden ODER-verknüpft; leere Auswahl = kein
  Filter.
- **URL-Param** `?phase=BAU,VORPLANUNG,UNBEKANNT` (MainPhase-Werte + `UNBEKANNT`, kanonische
  Reihenfolge, unbekannte Token werden verworfen). Er kombiniert sich (UND) mit `?group` und
  `?search` und bleibt wie `?search` beim Wechsel Karte ↔ Liste und in geteilten Links erhalten.
- **Pausierte/abgebrochene Projekte** (`lifecycle_status ≠ AKTIV`) werden nach ihrer
  Headline-Phase gefiltert wie alle anderen: der Lebenszyklus ist ein Overlay und ändert den
  Phasenwert nicht (gleiche Regel wie in der Ableitung). Auf der Projektkarte erscheint
  zusätzlich ein grauer Lebenszyklus-Badge.
- **Platzierung:** Desktop-Karte im schwebenden `MapControls`-Panel unter der Suche; Telefon im
  Bottom-Sheet „Karte einstellen" (ein aktiver Phasenfilter markiert den Einstellungs-Button mit
  einem Punkt, der Zähler „x von y Projekten" erscheint über der Karte); Listenansicht in der
  Filterzeile neben Projektgruppe und Suche (bricht bei 360 px auf eine eigene Zeile um).
- **Phasen-Badge** in der `ProjectCard` der Listenansicht (`PhaseBadge.tsx`): Palette
  `MAIN_PHASE_COLOR` wie `SubprojectsTable`, „Unbekannt" als grauer Outline-Badge.
- Filterlogik als reine, mit Vitest getestete Helfer in `features/projects/phaseFilter.ts`
  (`parsePhaseParam`, `serializePhaseParam`, `filterProjectsByPhase`, `phaseFilterOptions`).

**Nicht Teil dieses Pakets:** `ProjectGroup.default_phase_filter` (vorbelegter Filter je Gruppe,
zurückgestellt) und die Phasen-Verteilung für Parent-Projekte (#11).

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
BAUPORTAL 0.8, FULDA_RUNDE 0.55, MEDIEN 0.4). Abgeleitete Zeilen sind nicht hand-löschbar
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

> **Seit 2026-10-17 eigenes Feature:** `docs/features/feature-fulda-import.md`. Der frühere
> Weg (PDF-Upload → OCR → LLM mit fünf Kategorien) ist entfernt. Ein Agent liest die
> Antwort selbst und schreibt sie über MCP; Trust 0.55; Ist-Aussagen setzen die Phase,
> Prognosen und Neuaufnahmen erzeugen nur erwartete Termine (`is_expected`, abgeleitet).
> Die Jahres-Ansicht (`FuldaYearDetailPage`) bleibt als Freigabe-Fläche.

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
Zustand (Untergrenze oder Statusbericht für die Headline-Phase). Ein **erwarteter** Eintrag behauptet,
dass eine Phase erst *künftig* erreicht wird — er darf die aktuelle Phase **nicht**
hochziehen, sondern speist ausschließlich die **Prognose**.

**Datenmodell:** neues Flag `is_expected: bool` (default `False`, `server_default
"false"`) auf `progress_observation`. Ein erwarteter Eintrag nutzt dieselben Felder:
`track=MAIN`, `asserted_state` = Zielphase, `observed_date` = erwartetes Datum,
`source_type=MANUELL`, optional `note`. Migration via `make migrate-create`.

**Ableitung (`derive_headline`):** Beobachtungen mit `is_expected=True` werden aus der
Headline-/`computed_phase`-Ableitung **ausgeschlossen** (kein Beitrag zur
Headline). Sie tauchen weiterhin in der Provenienz-/Quellen-Tabelle auf,
klar als „erwartet" markiert.

**Prognose (`build_forecast` / `_build_forecast_for_project`):** erwartete Einträge
fließen als neue, **höchstpriorisierte** Quelle ein — *manuell übersteuert immer*.
Neuer Parameter `manual_expected: list[(MainPhase, date)]`; im `concrete`-Aufbau
**nach** VIB-PFA/Fulda gesetzt (die untereinander nach Glaubwürdigkeit × Aktualität
konkurrieren, siehe `feature-fulda-import.md`), sodass er bestehende Einträge überschreibt (nicht nur
Lücken füllt). Quelle-Label `"Manuell"` im `ForecastStep` und farblich im
`ForecastPanel` (`SOURCE_COLOR`). CRUD lädt alle `is_expected=True`-MAIN-Beobachtungen
mit Datum und trennt sie mit `split_expected`: nicht abgeleitete → „Manuell“, abgeleitete
Fulda-Prognosen → Fulda-Eingang (mit Datum der Antwort für die Gewichtung).

**Sichtbarkeit:** wie der übrige Planungsstand **öffentlich** (GET offen). Eingabe nur
mit Permission `progress.edit`.

**Frontend (`ProgressEditDrawer`):** der Abschnitt „Manuelle Beobachtungen" erhält im
`ObservationDraftForm` einen Schalter **„erwarteter Termin"**. Bei aktivem Schalter wird
`is_expected=true` mitgeschickt; Label/Beschreibung verdeutlichen „erwartet" statt
„erreicht". In der Beobachtungstabelle (Drawer) und im `SourceBreakdown` ein Badge
„erwartet". `ProgressObservationCreate`/`ProgressObservationSchema` um `is_expected`
erweitern → `make gen-api`.

## Übersprungene Planungsphasen je Projektgruppe (#164)

**Problem:** Das lineare Phasenmodell unterstellt jedem Projekt Vorplanung und
Genehmigungsplanung. Korridorsanierungen (HLK) kommen meist ohne Planfeststellung aus
und durchlaufen diese Phasen nicht — die Prognose zeigte trotzdem „Vorplanung" und
„Genehmigung / PFB" als nächste Schritte vor dem Bau.

**Datenmodell:** `project_group.skipped_phases` (JSON-Liste, `server_default '[]'`,
rückwärtskompatibel). Erlaubt sind nur die Planungsphasen `VORPLANUNG` und
`GENEHMIGUNGSPLANUNG` (`SkippablePhaseLiteral`); Start, Bau und Betrieb gehören immer
zum Projekt. Gepflegt im Admin-Formular der Projektgruppe („Übersprungene
Planungsphasen").

**Regeln:**
- **Mehrere Gruppen:** Eine Phase gilt für ein Projekt nur als übersprungen, wenn
  **alle** seine Gruppen sie überspringen (`resolve_skipped_phases`, Schnittmenge).
  Projekte ohne Gruppe überspringen nichts.
- **Daten gewinnen:** Die Gruppe setzt nur einen Default. Liegt das Projekt laut
  Ableitung/Override in einer übersprungenen Phase, liegt ein Unterprojekt darin oder
  gibt es einen konkreten Termin dafür (VIB-PFA, Fulda-Runde, erwarteter Termin), bleibt
  die Phase sichtbar (`resolve_hidden_phases`).
- Die Ableitung der Headline-Phase bleibt unverändert — ausgeblendet wird nur in
  Prognose und Darstellung.

**Prognose:** `build_forecast(skipped_phases=…)` lässt übersprungene Phasen ohne
konkreten Termin aus den nächsten Schritten weg; ein HLK-Projekt springt so von „Nicht
gestartet" direkt zu „Baubeginn" (BVWP-Planungsdauer ergibt weiterhin das Bau-Datum).

**API / Frontend:** `ProjectProgressSchema.hidden_phases` listet die ausgeblendeten
Phasen. `PhaseStepper` und `ProgressMini` lassen sie **ganz weg** (Leiste z. B.
Start → Bau → Betrieb, Nummerierung fortlaufend); Meilenstein-Rauten (Parl., PFB) rücken
auf die Verbindung, die ihre Phasengrenze überspannt.

## IBN-Plausibilität aus der GVFG-Finanzreihe

**Ziel:** Plant das GVFG-Bundesprogramm für ein Vorhaben noch nennenswerte
Finanzhilfen für Jahre **nach** dem bisher bekannten Inbetriebnahmejahr, ist dieses
Jahr fraglich — wer baut, bekommt noch Geld. Die Prognose zeigt dann einen Hinweis
„Inbetriebnahme JJJJ fraglich“ mit Verweis auf die GVFG-Finanzreihe; das Datum selbst
bleibt unverändert (keine Quelle wird übersteuert, der Mensch entscheidet).

- **Bekanntes IBN-Jahr:** Für GVFG-Vorhaben äußern sich nur zwei Quellen, beide
  gleichwertig: das größte Inbetriebnahmejahr der Vorhaben in der neuesten
  GVFG-Ausgabe — „Inbetriebnahme tats.“, sonst „gepl.“, also dasselbe Jahr wie in der
  Prognose (Entscheidung W4, 2026-10-22) — und die Inbetriebnahme aus dem Infraplan. Es gilt der **jüngere Stand**
  (Stand der Ausgabe vs. Veröffentlichung des Infraplans, wie Entscheidung 22 in
  `feature-gvfg-import.md`), bei gleichem Datum der Infraplan (`known_ibn`). VIB,
  Fulda-Runde und BVWP sagen zu GVFG-Vorhaben nichts und bleiben außen vor. Projekte in
  Betrieb werden nicht geprüft.
- **Finanzreihe:** ∑-Zeile aller finanzrelevanten Vorhaben des Projekts und seiner
  direkten Teilprojekte in der **neuesten** GVFG-Ausgabe, je Jahresspalte summiert.
  Eine Spalte zählt als „danach“, wenn sie nach dem IBN-Jahr beginnt („ab 2030“ zählt
  bei IBN 2030 also nicht).
- **Relevant:** danach ≥ 1 Mio. € **und** ≥ 15 % der Finanzhilfen aller Jahresspalten
  (`services/gvfg_ibn_check.py`) — Schlusszahlungen ein Jahr nach IBN lösen nichts aus.
- **API:** `ProgressForecastSchema.ibn_doubt` (Jahr, Quelle, Ausgabe, Mio. € danach und
  gesamt, Spalten danach); MCP: `get_project_progress` → `forecast.ibn_doubt` und
  `list_project_gvfg` → `ibn_doubt`. Ein Agent, der den Hinweis sieht, stellt das
  IBN-Datum in seiner Antwort in Frage und nennt die GVFG-Finanzreihe.
- **Frontend:** gelber Hinweis unter der Prognose (`ForecastPanel`).

## Planungsstand aus dem GVFG-Bundesprogramm

**Problem (2026-10-22):** Die GVFG-Ausgabe war keine Quelle des Planungsstands. Sie
unterdrückte nur die GVFG-Zeile des Infraplans, wenn sie jünger war (Entscheidung 22
in `feature-infraplan-import.md`), lieferte selbst aber nichts — ein GVFG-Projekt ohne
Infraplan-Zeile blieb „Unbekannt“ (z. B. 08 D 120_S S-Bahn Stuttgart S60, Baubeginn
2004, nur von Hand auf „In Betrieb“ übersteuert).

**Quelle `GVFG`** (Vertrauen 0.75 wie die GVFG-Zeilen des Infraplans, Länderangaben;
`observed_date` = Stand der Ausgabe, ohne Stand der 1.1. ihres ersten Jahres). Es zählt
je Projekt und Schlüssel die **neueste Ausgabe**, die den Schlüssel für das Projekt
führt. Mapper `gvfg_entry_to_specs` in `services/progress_materialization.py`, Zweig
`_add_gvfg_specs` in `sync_derived_observations_bulk`, Provenienz
`progress_observation.gvfg_entry_id` (Migration `20261022001`, nur Expand).

- **MAIN — eine Beobachtung, die stärkste dieser Aussagen** (mehrere mit gleichem
  Gewicht und Datum ließen bei Gleichstand nicht sicher die richtige gewinnen):
  - „Inbetriebnahme tats.“ **vor** dem Standjahr → `IN_BETRIEB` (W2),
  - Lph wie bei den GVFG-Zeilen des Infraplans (`5 - 9`, `8` → `BAU`; `3 - 4` →
    `GENEHMIGUNGSPLANUNG`; `1 - 2` → `VORPLANUNG`), zusätzlich eine alleinstehende `9`
    (Objektbetreuung) → `IN_BETRIEB`; Spannen über die Grenzen (`1 - 9`, `4 - 8`) und
    Listen (`4, 9`, `1 - 3 / 5 - 9`) sagen nichts (W1),
  - Baubeginn im oder vor dem Standjahr → `BAU` (W3).
  Die Notiz nennt alle Gründe („GVFG 2025–2029: Inbetriebnahme 2017, Lph 5 - 9“).
- **Erwartete Inbetriebnahme** (`is_expected`, 31.12. des Jahres, Präzision MONTH = Fahrplanwechsel 12/JJJJ): „Inbetriebnahme
  tats.“ — in den Ausgaben oft ein künftiges Jahr, also die aktuelle Erwartung —, sonst
  „gepl.“; nur wenn das Jahr nicht vor dem Standjahr liegt (frühere Jahre sind
  Restarbeiten, wie beim Infraplan) und das Vorhaben nicht schon in Betrieb ist (W2).
  In der Prognose und im Zeitstrahl konkurriert sie mit Quelle „GVFG“ wie die
  Infraplan-Termine über Glaubwürdigkeit × Aktualität (`concrete_milestone_dates`).
- **Vorrang zum Infraplan (Entscheidung 22, jetzt in beide Richtungen):** Ist die
  Infraplan-GVFG-Zeile desselben Schlüssels im neuesten Infraplan-Jahrgang des Projekts
  mindestens so jung wie die Ausgabe, liefert der Infraplan und die Ausgabe bleibt
  außen vor; sonst umgekehrt.
- **Sofort wirksam:** Übernahme einer Ausgabe (`confirm_parse_result`), Zuordnen
  (`assign_entry`) und Korrigieren (`set_entry_projects`, MCP `assign_gvfg_entry`)
  berechnen den Planungsstand der betroffenen Projekte neu; ersetzte Vorhaben nehmen
  ihre abgeleiteten Beobachtungen mit.
- **Nicht genutzt:** Kategorien A/C und der Auszahlungsgrad. Ein weitgehend ausgezahltes
  Vorhaben ist kein sicherer Beleg für die Inbetriebnahme.

**Entscheidungen (Widerspruchs-Check 2026-10-22):** W1 Lph `9` → In Betrieb, gemischte
Angaben → nichts · W2 „tats.“ vor dem Standjahr = In Betrieb, sonst erwartete IBN;
„gepl.“ nur ohne „tats.“ · W3 Baubeginn ≤ Standjahr → mindestens Bau · W4 die
IBN-Plausibilität nimmt dasselbe GVFG-Jahr wie die Prognose.

**Datenlage:** Bei den DB-Vorhaben Baden-Württembergs (`08 D …`) druckt die Ausgabe
2025–2029 weder Lph noch Inbetriebnahme; dort trägt nur der Baubeginn.

## Datumsqualifikation

Issues #243–#248 (2026-10-22). Viele Termine sind nicht als Tag bekannt: nur das Jahr
(HLK Hagen – Unna – Hamm: „2028“), nur eine Untergrenze (PM BMV/DB InfraGO vom 09.10.2026:
„nach 2031“) oder aus einer Regel abgeleitet (6 Monate Bauzeit). Bisher stand dafür ein
Pauschaldatum, das wie ein echter Termin aussah.

**Grundsatz** (`docs/architecture.md`): Ein Termin wird nie ohne seine Präzision angezeigt.
Das gespeicherte Datum ist nur noch der Sortierwert.

| `date_precision` | Bedeutung | Anzeige | Sortierwert |
|---|---|---|---|
| `EXACT` | Tag veröffentlicht (Default, alle Bestandsdaten) | 06.02.2026 | das Datum |
| `MONTH` | nur Monat bekannt | 02/2027 | 1. des Monats |
| `YEAR` | nur Jahr bekannt | 2028 | 01.01. |
| `NOT_BEFORE` | nur Untergrenze, kein Termin | nach 2031 (Grenze am 01.01., sonst „frühestens 07/2032“) | Untergrenze, z. B. 2032-01-01 |
| `ASSUMED` | aus einer Regel abgeleitet, nicht veröffentlicht | ca. 07/2028 (Annahme) | berechnetes Datum |

- **Freitext `date_label`** (optional, max. 120 Zeichen) wird angehängt: „nach 2031 –
  Priorisierung 2027 offen“. Im Zeitstrahl ersetzt er „Termin offen“.
- **Formatter:** `services/date_precision.py` und als Zwilling `src/shared/datePrecision.ts`.
  Die API liefert zu Beobachtungen, Quellen, Konflikten, Prognoseschritten und
  Zeitstrahl-Meilensteinen fertige `date_text`-Felder.
- **Inbetriebnahme, von der nur das Jahr bekannt ist** (Entscheidung W1): Das ist der
  Fahrplanwechsel Anfang Dezember, solange nichts anderes bekannt ist. Präzision `MONTH`,
  Anzeige 12/JJJJ, Sortierwert 31.12. (die späteste Lesart).
  - Das gilt für die erwartete Inbetriebnahme aus Infraplan und GVFG.
  - Es gilt auch für eine VIB-PFA-`inbetriebnahme`, die nur ein Jahr nennt
    (`parse_commissioning_with_precision`).
  - Der Fulda-Fallback ohne Prognosedatum (31.12. des Dokumentjahres) ist `YEAR`.
- **VIB-Freitext:**
  - `parse_flexible_date_with_precision` liest die Präzision mit: Tagesdatum → EXACT,
    Monat → MONTH, Quartal/Stichwort/Jahr → YEAR.
  - „nach 2031“, „>2031“, „ab/frühestens 2032“ → NOT_BEFORE mit dem ersten erlaubten Tag.
  - `parse_flexible_date` selbst bleibt unverändert.

### Prognose

- `concrete_milestone_dates` liefert je Phase ein `ConcreteDate` mit Datum, Quelle,
  Präzision, Label und Herleitung. Prognose und Zeitstrahl nutzen dieselbe Funktion.
  Gebündelte Angaben (frühester Beginn, späteste Inbetriebnahme) behalten die Präzision
  des gewählten Termins.
- **Bauzeit-Annahme:** Projektgruppen haben `assumed_build_months`; die Migration setzt HLK
  auf 6. Nennt keine Quelle eine Inbetriebnahme, rechnet die Prognose Baubeginn + diese Zeit.
  - Quelle „Annahme“, Herleitung z. B. „Annahme: 6 Monate Bauzeit ab Baubeginn 2028 (Manuell)“.
  - Präzision `ASSUMED`; bei einem `NOT_BEFORE`-Baubeginn ebenfalls `NOT_BEFORE`.
  - Ein konkreter oder manueller Termin gewinnt immer (Daten gewinnen vor der Gruppenregel).
  - Mehrere Gruppen mit Wert → der längste.
- **BVWP-Schätzungen** sind `ASSUMED` und bekommen eine Herleitung („Schätzung: …“).
  Auf einem Untergrenzen-Baubeginn bleiben sie `NOT_BEFORE`.
- **Restdauer:** Bei einer Untergrenze wird keine Restdauer behauptet; es steht „Ende der
  aktuellen Phase offen (nach 2031)“.
- `next_steps[]` trägt `date_precision`, `date_label`, `date_text` und `derivation`.
  `estimated_phase_end_precision` gehört zu `estimated_phase_end`.

### Listen und Filter

- `project_progress` speichert Baubeginn und Inbetriebnahme der eigenen Prognose als Cache:
  `construction_start_date/_precision` und `commissioning_date/_precision`, nur konkrete
  Termine und Annahmen, nie BVWP-Schätzungen.
  - Aktualisiert wird er bei jedem Lesen des Planungsstands (`get_progress_view`) und bei
    jedem `recompute_progress`, also auch nach Importen.
  - Einmal nach der Migration `20261022004`: `make docker-refresh-progress-dates`
    (`scripts/refresh_progress_dates.py`).
  - Die Liste liest weiter nur den Cache.
- Die Liste hat eine Spalte „Termine“ („Bau: nach 2031“, „IB: ca. 07/2028 (Annahme)“),
  sortierbar nach dem Sortierwert.
- **Filter** (Liste, Zeitstrahl, Karte; URL `bau_von`, `bau_bis`, `ib_von`, `ib_bis`,
  `termin_offen=1`; `features/projects/dateFilter.ts`):
  - Ein Zeitraum zählt `YEAR`/`MONTH`, wenn sich der Zeitraum mit dem Jahr bzw. Monat
    überschneidet.
  - `NOT_BEFORE` zählt **nie** als Treffer.
  - „Termin offen“ wählt Projekte, deren Baubeginn oder Inbetriebnahme nur eine
    Untergrenze ist.
  - Dieselbe Regel gilt in MCP `list_projects` (`construction_start`, `commissioning`,
    `date_open`).

### Pflege

- **Drawer:** Für neue Beobachtungen gibt es die Auswahl „Genauigkeit“ und das Feld
  „Terminzusatz“. Bei bestehenden manuellen Beobachtungen lässt sich die Genauigkeit direkt
  ändern (`PATCH /projects/{id}/progress/observations/{obs_id}`). MONTH und YEAR legen den
  Sortierwert auf den Periodenbeginn.
- **MCP:**
  - `add_progress_observation` nimmt `date_precision` (Default EXACT) und `date_label`.
  - `update_progress_observation` ändert Präzision, Label, Datum, Notiz, Vertrauen und
    `is_expected` einer manuellen Beobachtung in place; die Änderung wird protokolliert.
  - Abgeleitete Beobachtungen bleiben geschützt; sie bekommen ihre Präzision aus der
    Materialisierung.
- **Bestandsdaten:** Die Migration ändert nichts. Manuelle erwartete Inbetriebnahmen mit
  „Annahme“ im Notiztext (z. B. HLK, 6 Monate) gewinnen als manuelle Termine weiter gegen die
  Gruppenregel. Nach dem Deploy werden sie per MCP gelöscht, die Prognose rechnet dasselbe
  Datum dann sichtbar als Annahme. Platzhalter-Baubeginne bekommen per
  `update_progress_observation` `YEAR` oder `NOT_BEFORE`.

### Entscheidungen (Widerspruchs-Check 2026-10-22)

- **W1:** Eine abgeleitete Inbetriebnahme, von der nur das Jahr bekannt ist, behält den
  Sortierwert 31.12. und wird als Fahrplanwechsel 12/JJJJ angezeigt (Präzision MONTH).
- **W2:** Ob ein angekündigter Fulda-Abschluss eine Untergrenze (`NOT_BEFORE`) der Folgephase
  ist, wird zurückgestellt, siehe #250. Bis dahin EXACT bzw. YEAR.
- **W3:** Annahmen bekommen im Zeitstrahl einen gestrichelten Rahmen in Tintenfarbe. Die
  gestrichelte Linie in `seq-4` bleibt die Pause zwischen Bauetappen.

## Zeitstrahl über mehrere Projekte

Die Gantt-artige Übersicht über eine ganze Projektgruppe ist ein eigenes Feature:
`docs/features/feature-project-timeline.md`. Sie nutzt dieselbe Vorrangregel für konkrete
Termine wie die Prognose (`progress_forecast.concrete_milestone_dates`) und zeigt keine
BVWP-Schätzungen.

## Offene Punkte / Risiken / Edge Cases

- **`parl_befassung_relevant`-Default**: `project_group` hat kein stabiles Typ-Flag →
  Identifikation von „Bedarfsplan Schiene / BSWAG" per `short_name`/id klären; nullable
  Override hält Re-Gruppierung live.
- **VIB-Datumsfelder sind Freitext** (`baubeginn`, `datum_pfb`, …) → tolerantes Parsen +
  Fallback „nicht parsebar" (geringes Recency-Gewicht).
- **Echte Phasen-Rückschritte** (Reset): ein neuerer Bericht mit mindestens gleichem
  Vertrauen oder eine manuelle Beobachtung stuft zurück; sonst Konflikt in der Admin-Liste,
  aufzulösen per Phasen-Override / Lebenszyklus.
- **Sammel-FinVe** (`is_sammel_finve`, jahres-skaliert) mit geringerem Vertrauen.
- **Datum der Beobachtung = Datum der Aussage**: pro-PFA-MAIN-Beobachtungen tragen das
  Meilensteindatum (`baubeginn`/`datum_pfb`), Bauportal das erste Abrufdatum
  (`fetched_at`). Für „neuester Bericht gewinnt“ zählen sie damit als älter als ihr Bericht.
- **Superior ohne/gemischte Kinder** sowie Superior, das selbst Blatt ist (keine Kinder).
- **Derived-Observation-Churn**: regenerierte `is_derived`-Zeilen nicht ins Changelog;
  nur manuelle Edits auditieren.
- **Staleness-Fenster** für Lazy-Resync definieren (nicht bei jedem GET neu rechnen).
- **Sichtbarkeit**: GET offen (wie BVWP) oder login-gated (wie VIB) — entscheiden.
- **Fulda-Abschluss als Untergrenze** der Folgephase (`NOT_BEFORE`): zurückgestellt, #250.

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
- [x] Aufklappbereich zeigt je Quelle Aussage, Datum, Alter und (Admin) Vertrauen; Konflikte bleiben sichtbar.
- [x] Neuester Statusbericht gewinnt, Vertrauen nur innerhalb eines Jahres; FinVe ist
  Untergrenze und veraltet nicht (Regressionstest: VIB 2023 „In Betrieb“ schlägt FinVe 2011 „Bau“).
- [x] Rückstufungen durch neuere Berichte werden als Konflikt gemeldet und unter
  Admin → „Planungsstand-Konflikte“ gesammelt; weniger vertrauenswürdige werden zurückgehalten.
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
- **Recency-Floor** `0.3`: wirkt nur noch auf die Glaubwürdigkeit von Statusberichten (VIB
  bleibt über Jahre über der Schwelle, veraltete Medien fallen darunter), **nicht** mehr auf
  die Rangfolge — die folgt dem Datum (seit 2026-10-22, siehe „Ableitung = HYBRID“).
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
  `derive_headline` (Untergrenzen, neuester Bericht, Vertrauensfenster, Rückstufungs-Konflikte,
  Lebenszyklus-Overlay, Superior-Spanne)
  und Endpoint-Tests (PATCH-Override gewinnt, derived nicht löschbar). Neue Tabellen ins
  Test-Schema (`TABLES`) eintragen.
- Migration lokal anwenden (`make migrate-create` → `make migrate`), Modelle vorher
  registriert.
- API-Client: `make gen-api` nach Schemas.
- End-to-end manuell: Projekt mit Unterprojekten → Stepper + Parallelspuren +
  Aufklappbereich; Projekt auf `PAUSIERT` → Overlay; Dokument hinter PF verlinken;
  Override setzen → gewinnt über computed.
