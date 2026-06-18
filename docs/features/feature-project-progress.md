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

1. **Hauptspur (linear, immer vorhanden)** — geordnete Phasen:
   `NICHT_GESTARTET → VORPLANUNG (LP1-2) → GENEHMIGUNGSPLANUNG (LP3-4) → BAU → IN_BETRIEB`

2. **Parallelspuren (bedingt, nur bei manchen Projekten; einfache Zustände
   `offen / läuft / abgeschlossen`):**
   - **Planfeststellung** — läuft *parallel* zu `GENEHMIGUNGSPLANUNG`; Flag pro Projekt
     „hat PF" (manche Projekte haben keine PF).
   - **Parlamentarische Befassung** — Flag pro Projekt; **Voreinstellung aus Projektgruppe**
     (Bedarfsplan Schiene / BSWAG → an), manuell übersteuerbar.

3. **Lebenszyklus-Overlay (orthogonal):** `AKTIV / PAUSIERT / ABGEBROCHEN`.
   Nicht in die Phasenkette gemischt; **nicht** standardmäßig angezeigt. Bei
   `PAUSIERT`/`ABGEBROCHEN` wird die **gesamte** Darstellung überblendet
   (Banner + abgeblendeter Stepper); die zuletzt bekannte Phase bleibt erhalten.

**Ableitung = HYBRID:** Ein Algorithmus erzeugt einen *Vorschlag* für die Headline-Phase
(die meisten Quellen sind **monotone Untergrenzen**: Phase ≥ max der glaubwürdigen
Untergrenzen). Der Vorschlag ist redaktionell **übersteuerbar**. Konflikte werden nie
weggerechnet, sondern im Aufklappbereich transparent gezeigt.

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
  - Hauptphase = `max(order)` über glaubwürdige MAIN-Untergrenzen.
  - PF/PARL-Zustand nur ableiten, wenn Spur aktiv.
  - Lebenszyklus als Overlay-Flag zurückgeben (ändert Phasenwert nicht).
  - Output: `computed_phase`, `confidence`, `pf_state`, `parl_state`, Beitrag je Quelle
    (`was_decisive`), `effective_headline = manual_phase_override ?? computed_phase`.
- **DB-Zugriff** in `crud/projects/progress.py`:
  - `sync_derived_observations(db, project_id)` — löscht `is_derived=True`-Zeilen und
    regeneriert sie aus aktuell verknüpften VIB/FinVe-Records (**materialisieren**, nicht
    derive-on-read). Lazy bei stalem `computed_at` im GET + explizit per „recompute".
  - Mapping VIB: `status_planung→≥VORPLANUNG`, `status_bau→≥BAU`,
    `status_abgeschlossen→≥IN_BETRIEB`; PFA-Felder → PF-Spur + Prognose.
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
  abgeschlossen`) inkl. verlinkter Dokumente je Spur.
- `LifecycleOverlay.tsx` — Banner/Abblendung bei `PAUSIERT`/`ABGEBROCHEN`.
- `SourceBreakdown.tsx` — `<Collapse>` mit Beitrag je Quelle (Typ, Aussage, Datum,
  Vertrauen, „entscheidend"); bei Superior Kinderliste mit Links; manuelle Beobachtungen
  hinzufügen/löschen (gated `progress.edit`).
- `ForecastPanel.tsx` — Restdauer + nächste Schritte.

React-Query-Hooks in `shared/api/queries.ts`: `useProjectProgress`,
`useUpdateProjectProgress`, `useCreate/DeleteProgressObservation`,
`useLink/UnlinkTrackDocument`, `useRecomputeProgress` (Invalidate
`["project-progress", projectId]`). Typen via `make gen-api` → `types.gen.ts`.
Flags/Lebenszyklus **inline** in `ProgressSection` bearbeiten (nicht in das große
`ProjectEdit`-Formular mischen, da andere Tabelle), gated `can("progress.edit")`.

## Implementierungsreihenfolge (Phasen-Rollout)

1. **Modell + manuelle Erfassung + Visualisierung**: Tabellen/Enums, CRUD, GET/PATCH/
   Observation-Endpoints, `progress.edit`, reine Ableitung über manuelle Beobachtungen +
   Flags + Lebenszyklus, voller Stepper, Superior-Aggregation (Spanne), Dokument-Verknüpfung.
2. **VIB/FinVe-Ableitung**: `sync_derived_observations`, Lazy-Resync, `recompute`,
   Provenienz im Breakdown.
3. **Prognose**: `ProgressForecastSchema` aus BVWP-Dauern + VIB-PFA-Terminen + Fulda.
4. **Neue externe Quellen**: reichere manuelle Erfassung für FULDA_RUNDE/BAUPORTAL/MEDIEN,
   später eigene Importer (`is_derived`).

## Offene Punkte / Risiken / Edge Cases

- **`parl_befassung_relevant`-Default**: `project_group` hat kein stabiles Typ-Flag →
  Identifikation von „Bedarfsplan Schiene / BSWAG" per `short_name`/id klären; nullable
  Override hält Re-Gruppierung live.
- **VIB-Datumsfelder sind Freitext** (`baubeginn`, `datum_pfb`, …) → tolerantes Parsen +
  Fallback „nicht parsebar" (geringes Recency-Gewicht).
- **Echte Phasen-Rückschritte** (Reset) widersprechen der Untergrenzen-Regel → über
  manuellen Override / Lebenszyklus auffangen.
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
- [x] Übergeordnete Projekte zeigen eine Spanne + ihre Unterprojekte.
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
  sonst LAEUFT); FinVe → MAIN ≥ Bau, Sammel-FinVe schwächer (`confidence=0.35`).
  PFA-Evidenz schaltet `has_planfeststellung` automatisch ein. Beobachtungsdatum = VIB-
  **Report-Jahr** (das Freitext-`report_date` ist unzuverlässig).
- **Recency-Floor** auf `0.3` angehoben, damit strukturierte Quellen (VIB/FinVe) ihre
  monotone Untergrenze über Jahre halten (Fortschritt „passiert nicht rückwärts"), während
  veraltete Medien-Beobachtungen unter die Glaubwürdigkeitsschwelle fallen können.
- **Prognose** (`services/progress_forecast.py` + `services/progress_dates.py`): konkrete
  Termine (PFA/Fulda) schlagen BVWP-Schätzungen; Restdauer wird humanisiert.

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
