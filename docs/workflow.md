# Workflow dieses Repos

Gilt für jede Sitzung in diesem Repo, für Mensch und Agent. Wo eine Regel eine Begründung
trägt, steht sie dabei — sie ist der Teil, den keine Konfigurationsdatei verrät. Der
Standard über der Linie „Ausnahmen" ist derselbe wie in `JonasPrade/dtakt_mitglied`.

## Was in diesem Repo gilt

| | |
|---|---|
| Laufzeit | Backend Python 3.13 (`apps/backend/Dockerfile`), Abhängigkeiten exakt gepinnt in `apps/backend/requirements.txt` · Frontend Node 20, `package-lock.json` |
| Datenhaltung | PostgreSQL 16 + PostGIS + pgRouting (`docker/db`), SQLAlchemy 2.x, Alembic · Redis als Celery-Broker · GraphHopper (OpenRailRouting) für Routen |
| Eingehende Nahtstellen | Host-nginx (systemd) terminiert TLS für `dashboard.schienengruen.de` und leitet auf `127.0.0.1:5000` (Container-nginx im `frontend`-Image), der `/api/`, `/mcp` und `/healthz` an `backend:8000` weiterreicht · Login per Session, MCP per persönlichem API-Key · Volumes `pgdata`, `uploads`, `ghdata` · `backups/` als Bind-Mount |
| Zielhost und Architektur | Contabo-Host `vmd92747.contaboserver.net`, **`linux/amd64`** (`uname -m` → `x86_64`). Deshalb baut `ubuntu-latest` ohne `platforms:` das passende Image. Auf dem Host laufen weitere Dienste — nur `/srv/raildashboard` anfassen. Die erreichbare Adresse steht im Secret `DEPLOY_HOST`. |
| Images | `ghcr.io/jonasprade/raildashboard-{backend,frontend,db,graphhopper}` (`redis:7-alpine` von Docker Hub) |
| Prod-URL | `https://dashboard.schienengruen.de` |

## Ein Kommando

`make test` fährt die vollständige Prüfung. Die CI ruft dasselbe Kommando, ohne eigene
Schritte. Ein zweiter Weg wäre ein zweites System, und die Abweichung zwischen beiden wird
dann als Konfigurationsdetail gepflegt statt als Fehler behandelt.

Hier läuft das Kommando in den Prüfstufen der Dockerfiles (`test` im Backend, `check` im
Frontend) und baut danach die Laufzeit-Images. Es braucht nur `docker` und `bash`, und es
prüft mit demselben Interpreter, denselben gepinnten Abhängigkeiten und denselben Quellen,
aus denen das ausgelieferte Image entsteht. Reihenfolge:

1. `deploy/test_prod.sh` — `prod.sh` gegen ein gestubbtes `docker`
2. Backend: pytest (ohne `tests/db_related_tests`)
3. Frontend: `tsc --noEmit`, `eslint` (Fehler blockieren, Warnungen nicht), Vitest
4. Laufzeit-Images `backend`, `frontend`, `db`

Für die schnelle Schleife beim Entwickeln bleibt `make test-local` (pytest + Vitest gegen
die venv); das ist ausdrücklich nicht die Prüfung.

## Vom Branch nach Prod

Drei Workflow-Dateien, ohne `if`-Verzweigungen darin:

```
.github/workflows/ci.yml        # on: pull_request      — die Prüfung
.github/workflows/release.yml   # on: push [master]     — Prüfung und Build, ohne Auslieferung
.github/workflows/deploy.yml    # on: workflow_dispatch — Auslieferung, von Hand gestartet
```

`release.yml` fährt dieselbe Suite noch einmal — der PR-Lauf hat einen Baum geprüft, der nach
dem Merge einen anderen SHA trägt — und schiebt danach die Images nach GHCR, getaggt mit dem
Commit-SHA. Jeder Commit auf `master` hat seine Images; ausgeliefert wird nichts.

Der Image-Name steht fest im Workflow und wird nicht aus `github.repository` abgeleitet:

```yaml
env:
  IMAGE_PREFIX: ghcr.io/jonasprade/raildashboard
```

`github.repository` behält die Schreibweise des Kontos (`JonasPrade`), OCI-Registries
verlangen Kleinschreibung. Ein einziger Großbuchstabe lässt sonst den ersten Release-Lauf
scheitern.

Ausgeliefert wird über `deploy.yml`, gestartet von Hand unter Actions → Run workflow, mit
optionaler SHA-Eingabe (leer = aktueller Stand von `master`). Derselbe Knopf ist der Rückweg:
Rollback heißt vorherige SHA eintragen. Vor dem SSH-Aufruf prüft ein
`docker manifest inspect`, ob es die Images gibt — sonst fällt ein Tippfehler erst auf dem
Host auf. Nach dem Ausrollen ruft der Workflow `/healthz` von außen auf.

Der Knopf erscheint erst, wenn `deploy.yml` auf `master` liegt. Solange die Datei nur im PR
steht, ist er nicht zu finden.

```yaml
concurrency:
  group: production
  cancel-in-progress: true
```

Sitzt am `deploy`-Job, nicht am Workflow: Auf Workflow-Ebene würde ein schneller zweiter
Merge den laufenden Build abwürgen, und dem betroffenen Commit fehlten seine Images.

Prod zieht, Prod baut nicht: Das `compose.yaml` auf dem Host referenziert Images, keinen
`build:`-Block. Deshalb liegt dort kein Checkout und keine Buildkette.

`deploy/prod.sh` macht in einem Zug: SHA prüfen, Images ziehen, SHA in die `.env`,
`compose up -d`, auf den Healthcheck warten, optional Healthchecks-Ping. Bleibt der
Healthcheck aus, zurück auf den vorherigen SHA — die Images liegen noch lokal und sind
bitgleich mit dem, was lief. Das trägt, solange Migrationen rückwärtskompatibel bleiben.

Der Deploy-Key trägt in `authorized_keys` ein `command="/srv/raildashboard/prod.sh",…`
ohne Interpolation und kann damit nur dieses eine Skript ausführen.

## Beim Arbeiten

Änderungen laufen über Branch und PR. Was auf dem Server repariert wird, geht im selben
Zug zurück in einen PR — sonst ist der nächste Deploy die Rückabwicklung der Reparatur.
`compose.yaml` und `prod.sh` kommen nicht mehr mit der Pipeline auf den Server; ändern sie
sich, werden sie von Hand nachgezogen (`docs/uebergabe-deploy.md`, Schritt 5).

Regeln, die sich durchsetzen lassen, gehören in die Umgebung statt in diese Datei. Wer hier
eine Regel ergänzen will, prüft zuerst, ob Compose, Linter oder Hook sie erzwingen können.

## Was von Hand eingerichtet wird

Ein frischer Klon reproduziert das hier nicht. Abgearbeitet in `docs/uebergabe-deploy.md`:

- Umgebung `production` im Repo, Deployment branches auf `master`
- Secrets für Host, Benutzer und Deploy-Schlüssel
- `authorized_keys` auf dem Zielhost mit erzwungenem Kommando ohne Interpolation
- `docker login ghcr.io` als `deploy` mit einem classic PAT mit `read:packages`
- `compose.yaml` und `prod.sh` im Dienstverzeichnis
- alte Auslöser abschalten (Tag-Deploy), sonst rollt ein Tag weiter aus

## Ausnahmen in diesem Repo

Alles über dieser Zeile ist der Standard. Hier steht, was in diesem Repo davon abweicht,
und warum. Eine Ausnahme ohne Begründung ist eine Abweichung, die beim nächsten Mal niemand
mehr erkennt.

- **`master` statt `main`.** Der Default-Branch heißt hier so; `release.yml` lauscht auf
  `push: [master]`, das Environment `production` erlaubt `master`.

- **Host-nginx auf Loopback statt Caddy über das Netz `web`.** Auf vmd92747 gibt es weder
  Caddy noch ein Netz `web`; den Proxy macht ein nginx auf dem Host. Ein Host-Prozess
  erreicht Container nicht unter ihrem Namen, also bleibt ein Port —
  `127.0.0.1:5000:80` statt `0.0.0.0:5000:80`. Die Zusage dahinter bleibt erfüllt: es gibt
  keinen Weg hinein an Proxy und TLS vorbei. Die Freigabe von GraphHopper (`8989`) entfällt
  ersatzlos.

- **Vier Images statt einem.** Backend (auch für den `worker`), Frontend, Datenbank und
  GraphHopper werden je Commit gebaut und tragen dieselbe SHA; `prod.sh` zieht alle vier,
  `deploy.yml` prüft alle vier. `redis` kommt unverändert von Docker Hub.

- **Das Backup liegt in einem One-shot-Dienst des Stacks, nicht im Entrypoint.** Das
  Backend-Image hat kein `pg_dump` in der Version des Servers (Postgres 16). Der Dienst
  `backup` läuft mit dem db-Image, schreibt nach `backups/` und muss mit 0 enden, bevor das
  Backend startet und migriert. Die Zusage — auch ein `up` von Hand sichert vor der
  Migration — bleibt erfüllt.

- **`make test` läuft in Docker-Build-Stufen statt in einem `compose.test.yaml`-Stack.**
  Die Backend-Tests laufen gegen SQLite im Speicher, nicht gegen die echte Datenbank; die
  Tests in `apps/backend/tests/db_related_tests` brauchen PostGIS und pgRouting und laufen
  nur von Hand gegen eine Entwicklungsdatenbank. Ein geschlossenes Testnetz mit
  Socket-Sperre gibt es noch nicht. Beides ist offen und kein Zielzustand: der nächste
  Schritt wäre ein Test-Stack mit dem db-Image.

- **GraphHopper wird nur in `release.yml` gebaut, nicht in `make test`.** Der Build klont
  OpenRailRouting und fährt Maven, das dauert Minuten und ändert sich selten. Scheitert er,
  gibt es zum Commit kein vollständiges Image-Set, und `deploy.yml` lehnt die SHA ab.

- **`prod.sh` liegt unter `/srv/raildashboard/`, nicht unter `/srv/deploy/`.** Auf dem Host
  laufen mehrere Dienste; ein gemeinsamer Pfad wäre mehrdeutig. Im Repo heißt die Datei wie
  im Standard, `deploy/prod.sh`.

- **Tags und `make release-check` bleiben, rollen aber nichts mehr aus.** Ein Tag benennt
  einen Stand, `CHANGELOG.md` beschreibt ihn. Ausgerollt wird per Knopf über die SHA.

- **Die Umgebung `production` ist Ablage, kein Tor.** Required Reviewers gibt es auf Free,
  Pro und Team nur für öffentliche Repositories; in einem privaten Repo legt GitHub die
  Umgebung stillschweigend ohne Regeln an. Das Tor ist der Dispatch.

- **Keine Branch Protection.** Das Repo ist privat und liegt auf einem Konto ohne bezahlten
  Plan; GitHub setzt dort weder Branch Protection noch Rulesets durch. `ci.yml` meldet also,
  sperrt aber nicht. Das Tor vor Produktion steht trotzdem: `release.yml` baut Images nur
  nach grüner Prüfung auf `master`, und `deploy.yml` rollt nur aus, was als Image existiert.
  Ein roter Commit auf `master` bleibt damit unauslieferbar, bis ein grüner nachkommt. Mit
  einem Upgrade wird die Regel nachgezogen (`docs/uebergabe-deploy.md`, Schritt 1).
