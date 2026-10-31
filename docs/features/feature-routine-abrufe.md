# Feature: Routine-Abrufe (zeitgesteuert, ohne Mensch und Agent)

## Ziel

Abrufe aus externen Quellen, die reine Routine sind, laufen nach Zeitplan, statt dass ein
Mensch einen Knopf im Adminbereich drückt oder ein Agent sie über MCP anstößt. Ob ein Lauf
fehlschlug oder ausblieb, sieht man im Adminbereich.

Die Lückenanalyse REST ↔ MCP vom 2026-10-31 (`feature-mcp-server.md` → „Ausbau 2026-10-31“)
hat zwei Abrufe bewusst **nicht** als MCP-Tools gebaut, weil sie Routinejobs sind: den
Abgeordnetenstand von abgeordnetenwatch und das DB-Bauportal (#293). Dieses Dokument
plant ihren Zeitplan.

## Scope

**In scope**

1. Eigener Compose-Dienst `scheduler` (Celery Beat), Zeitplan im Code.
2. Drei Routinejobs:
   - **DB-Bauportal:** Abruf, Upsert, Vorschläge. Danach werden die Projekte neu
     berechnet, deren bestätigter Eintrag den Status gewechselt hat.
   - **Abgeordnetenstand:** `refresh_parliament_data`.
   - **Planungsstand:** Neuberechnung aller Projekte (`recompute_all_progress_task`).
3. Der Bauportal-Abruf wird ein Celery-Task mit Laufnachweis (`bauportal_import_run`).
4. Das Datum einer Bauportal-Beobachtung wird korrigiert: `status_changed_at` und
   `last_seen_at` statt `fetched_at`.
5. Sperre gegen parallele Läufe, Wiederholung bei Netzfehlern, Abschalten per Env.
6. Block „Zeitgesteuerte Abrufe“ in `/admin/system` plus Badge in der Admin-Übersicht.

**Nicht in scope**

- Weitere Quellen. Haushalt, VIB, GVFG, Infraplan, Zustandsbericht, Fulda und Medien sind
  Dokumente mit Mensch im Loop, keine Routine.
- Überlappungen neu berechnen (`recompute_all_overlaps_task`) und die Wahlkreis-
  Verschneidung (`rebuild_constituency_links`). Beide hängen an Ereignissen (Geometrie
  gespeichert, neue Wahl) und werden dort schon angestoßen, nicht an der Zeit.
- Ein Schalter je Job in der Oberfläche. Ebenso Benachrichtigungen (Mail,
  Healthchecks-Ping); die können später kommen.
- Abruf über MCP. Der Ausschluss aus #293 und dem Ausbau 2026-10-31 bleibt.
- Bauportal-Einträge, die aus der API verschwinden. Sie bleiben wie bisher stehen.

## Entscheidungen

Mit dem Nutzer am 2026-10-31 entschieden (Entscheidungskarten EK-2026-035 bis -043,
Stapel EKS-2026-007), jeweils nach Empfehlung.

| # | Frage | Entscheidung | Verworfen |
|---|---|---|---|
| W1 | Abgeordnetenstand zeitgesteuert, obwohl `feature-abgeordnete.md` das ausschloss? | **Ja.** Der Ausschluss ist dort datiert ersetzt, der Knopf bleibt. | manuell lassen |
| W2 | Welches Datum trägt eine Bauportal-Beobachtung? | **Zwei Felder:** `status_changed_at` (= `observed_date`, nur bei echtem Statuswechsel) und `last_seen_at` (= „Stand“, jeder Lauf). | `fetched_at` je Lauf setzen (Bauportal wäre jeden Tag „neueste“ Quelle); so lassen |
| W3 | Bauportal als Celery-Job? | **Ja**, mit Tabelle `bauportal_import_run`. `feature-worker-status.md` ist korrigiert. | nur die Doku korrigieren |
| W4 | Planungsstand regelmäßig neu berechnen? | **Ja:** wöchentlich alle Projekte, zusätzlich nach jedem Bauportal-Lauf die betroffenen. | nur nach dem Bauportal-Lauf; gar nicht |
| E1 | Mechanismus | **Eigener Compose-Dienst `scheduler`** mit `celery beat`. | Worker `-B`, Host-Cron/systemd-Timer, „beim Lesen veraltet → nachladen“ |
| E2 | Intervalle (Europe/Berlin) | **Bauportal täglich 02:40, Abgeordnete montags 02:50, Neuberechnung sonntags 03:10** | alles wöchentlich; Abgeordnete monatlich |
| E3 | Sichtbarkeit | **`/admin/system`: Block „Zeitgesteuerte Abrufe“ + Badge** | nur Fachseiten; zusätzlich Benachrichtigung |
| E4 | Sperre, Wiederholung, Abschalten | **Redis-Lock je Job, bis 3 Wiederholungen bei Netzfehlern, `ROUTINE_JOBS_ENABLED`** | Schalter je Job in der Oberfläche; keine Sperre |
| E5 | Was bleibt manuell | **Knöpfe bleiben, Bestätigung beim Menschen, kein MCP-Abruf** | Knöpfe entfernen; Abruf über MCP |

### Warum ein eigener Dienst und nicht Worker `-B` oder Cron

- **Rollback trägt:** Der Dienst läuft auf demselben Backend-Image und derselben
  `IMAGE_TAG` wie Backend und Worker. Ein Rollback auf eine frühere SHA nimmt den Zeitplan
  mit. Ein Host-Cron wäre davon getrennt, läge außerhalb des Repos und widerspräche
  „nur `/srv/raildashboard` anfassen“ (`docs/workflow.md`).
- **Genau einmal:** Compose startet den Dienst einmal. Beat im Worker (`-B`) liefe in
  jedem Worker, und bei mehr als einem Worker würden die Jobs doppelt gestartet.
- **Deploy-Tor unberührt:** Der Scheduler ist keine harte Abhängigkeit der Seite und
  gehört deshalb **nicht** in `/healthz`. Fällt er aus, merkt man das am Badge (E3),
  nicht am Deploy.
- **Lazy-on-read** scheidet aus: Ohne Aufruf passiert nichts, und für das Bauportal gibt
  es keinen Lese-Anlass, der den Abruf auslösen könnte.

### Warum zwei Datumsfelder beim Bauportal (W2)

Heute wird `fetched_at` nur beim Anlegen gesetzt (Default in
`models/projects/bauportal_status.py`); `import_bauportal` aktualisiert bei einem
erneuten Abruf nur den Status. Bei einem täglichen Abruf würde ein Wechsel von der
Planungs- in die Bauphase deshalb auf das Datum des ersten Abrufs zurückdatiert, und die
Recency-Abwertung behandelte ihn als alt.

Würde man `fetched_at` stattdessen bei jedem Lauf neu setzen, gälte das Bauportal jeden
Tag als „neueste“ Quelle. Nach dem Grundsatz „Die neuere Quelle gewinnt“
(`docs/architecture.md`) würde jeder Konflikt mit einer vertrauenswürdigeren, älteren
Meldung dann täglich erneuert. Eine neue Beobachtung ist aber nur ein Statuswechsel, kein
bloßes „wieder gesehen“.

## Verhalten

| Situation | Was passiert / was man sieht |
|---|---|
| Nächtlicher Bauportal-Lauf ohne Statuswechsel | `last_seen_at` steigt, `status_changed_at` bleibt. Der Planungsstand ändert sich nicht. Die Projektseite zeigt „Stand: <last_seen_at>“. |
| Bestätigter Eintrag wechselt den Status | `status_changed_at` = heute. Die betroffenen Projekte werden sofort neu berechnet (`recompute_for`), Liste und Karte sind am Morgen aktuell. |
| Neuer, unbestätigter Eintrag | Er bekommt wie bisher einen Vorschlag. Eine Beobachtung entsteht erst, wenn ein Mensch bestätigt. |
| Knopf wird gedrückt, während der Job läuft | `409` mit „Läuft bereits seit …“. Ein Zeitplan-Lauf, der eine Sperre vorfindet, wird übersprungen und protokolliert. |
| Netzfehler (Timeout, 5xx) | Bis zu 3 Wiederholungen mit Backoff (1, 4, 16 min). Danach ist der Lauf `error` mit Meldung. |
| Datenfehler (unerwartete Antwort) | Keine Wiederholung, der Lauf ist sofort `error`. |
| Scheduler-Container steht | Kein Lauf. Ist der letzte erfolgreiche Lauf älter als das doppelte Intervall, zeigt die Admin-Übersicht ein Badge. Die 60-Tage-Markierung „veraltet“ der Abgeordneten bleibt als zweiter Alarm. |
| `ROUTINE_JOBS_ENABLED=false` | Der Scheduler reiht nichts ein. `/admin/system` zeigt „Zeitplan abgeschaltet (Env)“. Die Knöpfe gehen weiter. |
| Borg-Sicherung 04:05 | Alle Jobs liegen davor. Ein verpasster Termin wird nicht nachgeholt (Crontab-Zeitplan), der nächste Termin greift. |

### Block „Zeitgesteuerte Abrufe“ in `/admin/system`

Je Job eine Zeile: Name, Intervall, nächster Termin, letzter Lauf (Zeit, Auslöser
„Zeitplan“ oder Nutzer, Dauer), Status (`success` / `error` / `running` / `skipped`) und
bei Fehler die Meldung. Dazu der Knopf, der zur Fachseite führt, auf der der Job manuell
gestartet wird.

Das Badge in der Admin-Übersicht erscheint, wenn mindestens ein Job

- als letzten Lauf `error` hat, oder
- seit mehr als dem doppelten Intervall keinen erfolgreichen Lauf hatte, oder
- als „Zeitplan abgeschaltet“ gemeldet wird.

## Akzeptanzkriterien

- [ ] `compose.yaml` hat den Dienst `scheduler` (Image `raildashboard-backend:${IMAGE_TAG}`,
      `command: celery -A dashboard_backend.celery_app beat`, `SKIP_MIGRATIONS=1`,
      `depends_on: backend: service_healthy`, kein `build:`, kein Port).
- [ ] Die drei Jobs laufen zu den Zeiten aus E2 (Europe/Berlin). Ein Test prüft den
      Zeitplan (`beat_schedule`) gegen die Tabelle in diesem Dokument.
- [ ] Der Bauportal-Abruf läuft als Celery-Task. Knopf und Zeitplan nutzen denselben Task.
      Jeder Lauf schreibt eine Zeile in `bauportal_import_run`, auch wenn er fehlschlägt.
- [ ] `bauportal_status` hat `status_changed_at` und `last_seen_at`.
      - Die Migration ist reines Expand: Beide Spalten werden aus `fetched_at` gefüllt,
        `fetched_at` bleibt vorerst bestehen.
      - `status_changed_at` ändert sich nur bei einem Wechsel von `status_raw`.
      - Die abgeleitete Beobachtung nutzt `status_changed_at`, die Projektseite zeigt
        `last_seen_at` als „Stand“.
- [ ] Nach einem Bauportal-Lauf sind Projekte mit einem bestätigten Statuswechsel sofort
      neu berechnet.
- [ ] Zeitplan-Läufe der Abgeordneten erscheinen in `parliament_import_run` mit
      `triggered_by_user_id = NULL`. Die Oberfläche zeigt dafür „Zeitplan“.
- [ ] Ein zweiter Start desselben Jobs während eines laufenden Laufs wird abgelehnt
      (Knopf: `409`) bzw. übersprungen (Zeitplan). Getestet für Knopf gegen Zeitplan.
- [ ] Netzfehler werden bis zu dreimal wiederholt, Datenfehler nicht (Test mit gemocktem
      HTTP).
- [ ] Mit `ROUTINE_JOBS_ENABLED=false` reiht der Scheduler nichts ein. Die Testsuite setzt
      den Wert in `apps/backend/tests/conftest.py`.
- [ ] `/admin/system` zeigt den Block „Zeitgesteuerte Abrufe“. Die Admin-Übersicht zeigt
      das Badge nach den Regeln oben. Der Block ist bei 360 px nutzbar.
- [ ] `/healthz` bleibt unverändert, der Scheduler ist keine Abhängigkeit des Deploy-Tors.
- [ ] Doku nachgezogen: `CHANGELOG.md`, `DEPLOY.md`, `docs/production_setup.md`,
      `docs/environment.md`, `.env.prod.example`, `.env.example`,
      `apps/backend/README.md`, In-App-Doku (`DocumentationPage.tsx`), Docstring in
      `tasks/progress.py`.

## Technische Schritte

1. **Bauportal-Daten (Migration, Expand).** `make migrate-create MSG="bauportal status
   dates and import run"`:
   - `bauportal_status.status_changed_at`, `bauportal_status.last_seen_at` (beide aus
     `fetched_at` befüllt),
   - neue Tabelle `bauportal_import_run`, angelehnt an `parliament_import_run`: `id`,
     `started_at`, `finished_at`, `status`, `error`, `stats` (JSON),
     `triggered_by_user_id` (nullable = Zeitplan).

   `fetched_at` wird erst in einem späteren Release entfernt (Contract, siehe #325).
2. **Bauportal-Task.** `tasks/bauportal.py` bekommt einen Celery-Task
   `refresh_bauportal(user_id=None)`.
   - Er schreibt den Laufnachweis, ruft `import_bauportal` auf und gibt die IDs der
     Projekte zurück, deren bestätigter Eintrag den Status gewechselt hat. Diese Projekte
     berechnet er mit `recompute_for` neu.
   - `import_bauportal` setzt `last_seen_at` immer und `status_changed_at` nur bei
     geändertem `status_raw`.
   - `POST /import/bauportal/fetch` reiht den Task ein und antwortet mit `202` +
     `task_id`, wie die anderen Importe.
   - Die Frontend-Seite nutzt `useImportTask`.
3. **Beobachtungsdatum.** `crud/projects/progress.py` (BAUPORTAL-Materialisierung)
   nutzt `status_changed_at` statt `fetched_at`. `GET /projects/{id}/bauportal` liefert
   `last_seen_at`, `BauportalSection` zeigt es als „Stand“. Danach `make gen-api`.
4. **Sperre.** Ein kleiner Helfer `services/job_lock.py`:
   - Redis `SET NX` mit TTL = Zeitlimit des Tasks, Schlüssel `routine-lock:<job>`.
   - Er wird von den drei Tasks und den drei Endpunkten genutzt. Der Endpunkt prüft die
     Sperre vor dem Einreihen und antwortet sonst mit `409`.
5. **Wiederholung.** `autoretry_for=(httpx.TransportError, httpx.HTTPStatusError bei
   5xx)`, `max_retries=3`, Backoff 60 s × 4ⁿ; für `refresh_bauportal` und
   `refresh_parliament_data`. Die Neuberechnung wird nicht wiederholt.
6. **Zeitplan.**
   - `celery_app.conf.beat_schedule` mit drei `crontab`-Einträgen, `timezone =
     "Europe/Berlin"`.
   - Die Zeiten stehen als Konstanten in einem Modul (`dashboard_backend/schedule.py`),
     damit Test und `/admin/system` dieselbe Quelle lesen.
   - Ein Wrapper-Task je Job prüft `ROUTINE_JOBS_ENABLED` und die Sperre, bevor er den
     eigentlichen Task startet.
7. **Konfiguration.** `Settings.routine_jobs_enabled: bool = True` (`core/config.py`),
   dokumentiert in `.env.prod.example`, `.env.example` und `docs/environment.md`. Die
   Testsuite setzt `ROUTINE_JOBS_ENABLED=false` in `conftest.py`.
8. **Compose.**
   - Dienst `scheduler` wie im ersten Akzeptanzkriterium.
   - Die Schedule-Datei von Beat liegt unter `/tmp` im Container, damit kein Zustand
     außerhalb eines Volumes bleibt. Für Crontab-Zeitpläne braucht sie keinen Bestand.
   - Lokal läuft der Dienst über `compose.override.yaml` mit (Build-Block).
9. **Sichtbarkeit.**
   - `GET /api/v1/system/routine-jobs` (Recht `settings.manage`) liefert je Job:
     Intervall, nächster Termin, letzter Lauf und Status, gelesen aus
     `bauportal_import_run`, `parliament_import_run` und dem Laufnachweis der
     Neuberechnung (siehe Offene Punkte).
   - Frontend: Block in `features/admin/SystemStatusPage.tsx`, Badge in der
     Admin-Übersicht.
10. **Abgeordnete.** `refresh_parliament_data` ohne `user_id` gilt als Zeitplan-Lauf. Die
    Oberfläche (`/admin/abgeordnete`) zeigt „Zeitplan“ statt eines Nutzernamens.
11. **Doku und Deploy.**
    - `CHANGELOG.md` (Added: Scheduler, Jobs; Changed: Bauportal asynchron, Datumsfelder).
    - `DEPLOY.md` → Server-Layout und „Daran hängen die Container-Namen“: `scheduler`
      kommt in `/root/expected_containers.txt` (Handschritt in `docs/uebergabe-deploy.md`).
    - `docs/production_setup.md`: Dienstliste, Env, Zeitplan, Borg-Fenster.
    - `compose.yaml` muss nach dem Merge von Hand auf den Server
      (`docs/uebergabe-deploy.md`, Schritt 5).

## Folgen für Deploy und Rollback

- **Neuer Container**, sonst nichts Neues auf dem Host. Die Host-Überwachung kennt ihn
  erst nach dem Eintrag in `/root/expected_containers.txt`. Das ist ein Handschritt
  (human task) und wird im Issue als solcher genannt.
- **Rollback auf eine SHA ohne Scheduler:** `prod.sh` tauscht nur `IMAGE_TAG`, die
  `compose.yaml` auf dem Server bleibt. Der `scheduler`-Container startet dann mit dem
  älteren Image, das kein `beat_schedule` hat, und tut nichts. Das ist harmlos, und mit
  dem nächsten Vorwärts-Deploy ist der Zeitplan wieder da.
- **Migration:** nur Expand (zwei Spalten, eine Tabelle). Ein älterer Code mappt die
  neuen Spalten nicht und läuft weiter.
- **`/healthz` bleibt gleich.**

## Offene Punkte

- **Laufnachweis der wöchentlichen Neuberechnung.** `recompute_all_progress_task` hat
  heute keinen. Vorschlag: `bauportal_import_run` von Anfang an allgemein als
  `routine_job_run` mit Spalte `job` (`bauportal`, `progress_recompute`) anlegen, statt
  einer zweiten Tabelle. Die Abgeordneten behalten `parliament_import_run`. Wird vor der
  Umsetzung mit dem Nutzer geklärt.

## Konzept-Verweis

- Issue: #340
- `docs/features/feature-abgeordnete.md` → „Wie oft wird der Abgeordnetenstand
  aktualisiert …“
- `docs/features/feature-project-progress.md` → „DB-Bauportal (#47)“
- `docs/features/feature-worker-status.md` (Systemstatus)
- `docs/features/feature-mcp-server.md` → „Ausbau 2026-10-31“
- `DEPLOY.md`, `docs/workflow.md`, `docs/production_setup.md`
