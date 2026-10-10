# Deploy-Vertrag — raildashboard

Drei Workflow-Dateien, ohne `if`-Verzweigungen darin
(Begründungen: [`docs/workflow.md`](docs/workflow.md)):

```
.github/workflows/ci.yml        on: pull_request      — die Prüfung (Job „Prüfung")
.github/workflows/release.yml   on: push [master]     — Prüfung und Build, ohne Auslieferung
.github/workflows/deploy.yml    on: workflow_dispatch — Auslieferung, von Hand gestartet
```

Leitsatz: *Jeder Commit auf `master` hat seine Images; ausgeliefert wird nichts, bis
jemand den Knopf drückt.*

## Ablauf

```
PR öffnen
   │  ci.yml: make test   (derselbe Befehl, den du lokal fährst)
   ▼
Merge nach master
   │  release.yml: make test noch einmal (anderer SHA nach dem Merge)
   │               -> ghcr.io/jonasprade/raildashboard-{backend,frontend,db,graphhopper}:<commit-sha> + :latest
   ▼
Actions -> deploy -> Run workflow        ← das Tor
   │  SHA leer = aktueller Stand von master · Rollback = frühere SHA eintragen
   │  docker manifest inspect: gibt es alle vier Images?
   │  SSH -> /srv/raildashboard/prod.sh <sha>
   ▼  prod.sh (auf vmd92747, Benutzer `deploy`)
   │  SHA prüfen -> vier Images ziehen -> IMAGE_TAG in .env -> up -d
   ▼  compose.yaml
   │  db healthy -> `backup` (One-shot): pg_dump nach backups/ (schlägt er fehl -> Abbruch)
   │  -> backend-Entrypoint: alembic upgrade head (außer die DB ist weiter: Rollback) -> uvicorn
   ▼
prod.sh wartet auf „healthy" (/healthz); sonst automatischer Rollback auf den vorherigen SHA.
deploy.yml ruft danach https://dashboard.schienengruen.de/healthz von außen auf.
```

**Es gibt keinen automatischen Auslöser.** Bis v0.0.15 rollte ein Version-Tag
(`v*`) Test, Build und Ausrollen in einem Zug aus. Das nahm den Moment weg, in dem
jemand „jetzt" sagt, und band die Auslieferung an eine Versionsnummer, obwohl das
Image am Commit hängt. Tags, `make release-check` und `CHANGELOG.md` bleiben
nützlich, um Stände zu benennen; ausgerollt wird über den SHA.

## Server-Layout (`/srv/raildashboard/` auf vmd92747, Benutzer `deploy`)

| Datei | Herkunft | Zweck |
|---|---|---|
| `compose.yaml` | aus dem Repo kopiert | referenziert `ghcr.io/jonasprade/raildashboard-<dienst>:${IMAGE_TAG}`, der Server baut nie selbst |
| `.env` | von Hand angelegt, nie im Repo | alle Werte aus `.env.prod.example` **mit echten Werten** + `IMAGE_TAG` (pflegt `prod.sh`) |
| `prod.sh` | `deploy/prod.sh` aus dem Repo, `chmod +x` | wird von der Pipeline per SSH aufgerufen |
| `backups/` | Bind-Mount des `backup`-Dienstes | `pre-migrate_<zeit>_<sha12>.dump`, dazu ältere `pre-deploy_*.dump` aus der Zeit vor der Umstellung |

Volumes `raildashboard_pgdata`, `raildashboard_uploads`, `raildashboard_ghdata`;
`compose.yaml` setzt `name: raildashboard`, damit die Namen nicht vom Verzeichnis
abhängen. `compose.override.yaml` (lokaler Build) gehört **nicht** auf den Server,
`prod.sh` verweigert sonst den Dienst.

### Weg hinein: Host-nginx auf Loopback

Auf vmd92747 terminiert ein **nginx auf dem Host** (systemd, kein Container) TLS für
`dashboard.schienengruen.de` und leitet auf `http://localhost:5000` weiter
(`/etc/nginx/sites-available/dashboard.schienengruen.de`, `client_max_body_size 50m`).
Ein Host-Prozess erreicht Container nicht über ein Docker-Netz unter ihrem Namen,
deshalb bleibt **ein** Port — aber nur auf Loopback:

```yaml
frontend:
  ports:
    - "127.0.0.1:5000:80"
```

Bis zur Umstellung stand dort `0.0.0.0:5000` (Weg an nginx und TLS vorbei) und
`0.0.0.0:8989` für GraphHopper (Routing-Dienst offen im Netz, von niemandem genutzt;
das Backend spricht ihn über `graphhopper:8989`). Beides ist weg. Abweichung vom
Standard „Caddy über Netz `web`": `docs/workflow.md`, Ausnahmen.

## GitHub-Konfiguration

- **Environment `production`** (Settings → Environments), Deployment branches auf
  `master`. Ablage und Protokoll, kein Tor: *Required Reviewers* gibt es auf Free,
  Pro und Team nur für öffentliche Repositories; in einem privaten Repo legt GitHub
  die Umgebung stillschweigend ohne Regeln an. Das Tor ist der Dispatch.
- **Secrets** (im Environment `production`): `DEPLOY_HOST`, `DEPLOY_USER` (`deploy`),
  `DEPLOY_SSH_KEY`, optional `DEPLOY_PORT`. Die alten `SSH_HOST`, `SSH_USER`,
  `SSH_PRIVATE_KEY`, `GHCR_TOKEN` braucht nichts mehr.
- **Repo-Variable** `TILE_LAYER_URL`: wird in `release.yml` ins Frontend-Bundle gebacken.
- **Branch Protection: nicht verfügbar.** GitHub setzt Branch Protection und Rulesets
  in privaten Repositories erst mit einem bezahlten Plan durch. Ein Merge an einer
  roten PR-Prüfung vorbei ist deshalb möglich. **In Produktion kommt trotzdem nichts
  Ungeprüftes:** `release.yml` baut Images erst nach grünem `make test` auf `master`,
  und `deploy.yml` bricht ab, wenn es zur SHA kein Image gibt. Mit einem Upgrade:
  Regel auf `master`, Pflicht-Check **`Prüfung`** (der Job-Name, nicht der Dateiname).

### Eingeschränkter Deploy-Schlüssel

In `/home/deploy/.ssh/authorized_keys`:

```
command="/srv/raildashboard/prod.sh",no-pty,no-agent-forwarding,no-port-forwarding,no-X11-forwarding ssh-ed25519 AAAA… github-actions-deploy
```

**Ohne Interpolation.** `prod.sh` liest `SSH_ORIGINAL_COMMAND` selbst, nimmt das letzte
Wort und verlangt eine vollständige Commit-SHA (`^[0-9a-f]{40}$`); alles andere endet
mit Rückgabewert 2, bevor irgendetwas passiert. Bis zur Umstellung trug der Schlüssel
**kein** erzwungenes Kommando: die Pipeline rief `mkdir`, `scp` und `chmod` frei auf.
Dateien kommen deshalb nicht mehr per Pipeline auf den Server, sondern von Hand
(`docs/uebergabe-deploy.md`, Schritt 5).

### GHCR-Zugriff des Servers

Das Repo ist privat, also sind auch die Images privat. Einmalig auf dem Server:

```bash
# als Benutzer deploy; der Token wird verdeckt abgefragt
read -rs -p "Token: " GHCR_PAT; echo
printf '%s' "$GHCR_PAT" | docker login ghcr.io -u <github-user> --password-stdin
unset GHCR_PAT
```

- Es muss ein **classic** Token mit `read:packages` sein. Fine-grained Tokens nimmt
  GHCR nicht an; `docker login` endet dann mit `denied`.
- **Der Token läuft ab.** Danach scheitert jeder Deploy beim Pull. Am 07.10.2026 ist
  der Release v0.0.15 genau daran gescheitert (`denied: denied`). Ablaufdatum notieren.
- Fehlt oder verfällt der Login, bricht `prod.sh` beim Pull ab, **bevor** es die
  `.env` anfasst; der laufende Stand bleibt unberührt.
- Früher meldete `deploy.sh` den Server bei jedem Lauf mit einem Token aus den
  GitHub-Secrets an, der dabei in der Befehlszeile stand. Das entfällt.

## Healthcheck

- `GET /healthz` (Backend, über den Container-nginx als `location = /healthz`
  durchgereicht) liefert `200` nur, wenn
  - die Datenbank erreichbar ist,
  - eine vollständige `Project`-Zeile ladbar ist (alle gemappten Spalten existieren —
    `SELECT 1` bliebe grün, wenn Schema und Code nicht zusammenpassen),
  - `SESSION_SECRET_KEY` gesetzt und kein Platzhalter aus `.env.prod.example` ist,
  - `UPLOAD_DIR` und `IMPORT_STAGING_DIR` beschreibbar sind;

  sonst `503` mit Problemliste. `/api/v1/health` bleibt als reine Erreichbarkeitsprobe.
- Ohne die `location = /healthz` im Container-nginx beantwortete der SPA-Fallback den
  Pfad mit `index.html` und `200` — der Außen-Check wäre bei totem Backend grün.
- `prod.sh` wartet darauf (180 s, inklusive Backup und Migration) und rollt bei
  Misserfolg auf den vorherigen SHA zurück.
- Extern: `https://dashboard.schienengruen.de/healthz`. `deploy.yml` ruft sie nach dem
  Ausrollen auf. Der Container-Healthcheck sieht den Host-nginx nicht; zeigt der ins
  Leere, wäre der Deploy sonst grün bei einer toten Seite. Dieser Schritt rollt nicht
  zurück, er macht den Lauf rot.

## Backup & Restore

1. **Vor jeder Migration** zieht der One-shot-Dienst `backup` (`docker/db/backup.sh`,
   im db-Image) einen `pg_dump -Fc` nach `backups/pre-migrate_<zeit>_<sha12>.dump`.
   Das Backend — dessen Entrypoint `alembic upgrade head` fährt — startet erst, wenn
   `backup` mit 0 endete (`depends_on: condition: service_completed_successfully`).
   Kein Backup, kein Update. Retention: die neuesten `BACKUP_KEEP` (Default 10)
   `pre-migrate_*`-Dumps; andere Dateien in `backups/` bleiben unberührt.
   Der Dienst sitzt im Stack, damit er auch bei einem `docker compose up -d` von Hand
   greift, und im db-Image, damit `pg_dump` exakt zur Server-Version passt.
   **Scheitert das Backup**, endet `up` mit Fehler — Compose hat den alten
   Backend-Container zu diesem Zeitpunkt aber schon ersetzt. `prod.sh` rollt dann
   zurück, und zwar mit `BACKUP_SKIP=1`: der Rückweg braucht keinen neuen Dump
   (entweder lief keine Migration, oder der Dump vom Vorwärtslauf liegt schon da),
   und ein dauerhaft scheiterndes Backup (Platte voll) hielte sonst auch den
   vorherigen Stand unten. Mit echtem Docker durchgespielt (PR-Beschreibung).
   Bei einer **frischen** Datenbank kann der allererste Lauf scheitern, weil Postgres
   während `initdb` kurz bereit meldet und dann neu startet; ein zweites `up` geht durch.
2. **Nächtlich um 04:05** sichert `/root/create_backup.sh` (root-Crontab) den Host nach
   **Borg** (Log `/var/log/borg/backup.log`):
   - vorher `docker exec raildashboard-db-1 pg_dump … | gzip` nach
     `/srv/db_dumps/raildashboard.sql.gz`,
   - dann stoppt es **alle** laufenden Container, archiviert `/root`, `/srv`, `/home`,
     `/etc`, `/var/lib/docker/volumes/raildashboard_pgdata`,
     `/var/lib/docker/volumes/raildashboard_uploads` (und `streckeninfo_daten`) und
     startet die zuvor laufenden Container wieder.

   `/srv` enthält `/srv/raildashboard/backups/`, die `pre-migrate_*`-Dumps landen also
   mit im Archiv. Das `uploads`-Volume (Textanhänge) steckt nicht im Pre-Migrate-Dump,
   wohl aber seit dem 10.10.2026 im Borg-Lauf (vorher fehlte es dort).

   **Daran hängen die Container-Namen.** Backup-Skript (`raildashboard-db-1`),
   `/root/check_containers.sh` mit `/root/expected_containers.txt` (frontend, backend,
   worker, db, redis, graphhopper) und `/root/monitored_software.yaml` (`raildashboard-redis-1`)
   sprechen die Container mit Namen an. `compose.yaml` setzt deshalb
   `name: raildashboard`; Projektname oder Dienstnamen nicht ändern, ohne diese drei
   Stellen mitzuziehen. Der One-shot `raildashboard-backup-1` steht nach jedem Lauf auf
   `exited`; er ist dort nicht eingetragen und darf es auch nicht werden.

   **Nicht gegen 04:05 ausrollen**: in diesem Fenster sind alle Container gestoppt.

**Restore** (als `deploy`, nach jeder Änderung am Backup-Mechanismus erneut testen):

```bash
cd /srv/raildashboard
docker compose stop frontend worker backend
docker compose exec -T db pg_restore -U raildashboard -d raildashboard \
    --clean --if-exists --single-transaction < backups/pre-migrate_<zeit>_<sha12>.dump
./prod.sh <sha>          # Code-Stand passend zur DB
```

Ein **Image-Rollback rollt nur den Code zurück, nicht die Datenbank.** Nach einem
automatischen Rollback wegen fehlgeschlagener Migration prüfen, ob die Migration
Teiländerungen hinterlassen hat — dann zusätzlich den Dump von direkt davor einspielen.

Damit ein Rollback **nach** einer gelaufenen Migration überhaupt hochkommt, prüft der
Backend-Entrypoint vor `alembic upgrade head`, ob die Datenbank auf einer Revision
steht, die der Code nicht kennt (`apps/backend/scripts/db_ahead.py`). Dann ist sie
weiter als der Code, und die Migration wird übersprungen; ohne diese Weiche bräche das
ältere Image an der unbekannten Revision ab. Das greift erst für Images, die diese
Prüfung enthalten. Und es trägt nur, solange Migrationen rückwärtskompatibel sind
(Expand/Contract): eine Migration, die eine Spalte löscht, die der ältere Code noch
mappt, macht dessen `/healthz` rot (`schema`) — dann hilft nur der Restore.

## Rollback

Actions → deploy → Run workflow, frühere SHA eintragen. Jeder Commit auf `master` liegt
unveränderlich in GHCR. Deshalb nie über `latest` ausrollen — der SHA ist der Rückweg.

Der älteste SHA, der so erreichbar ist, ist der Merge-Commit dieser Umstellung (wird
nach dem ersten Lauf hier eingetragen). Für ältere Stände gibt es in GHCR nur
Version-Tags (`v0.0.14` …), und `deploy.yml` lässt nur SHAs durch. Auf dem Server ist
v0.0.14 zusätzlich lokal auf seine Commit-SHA `2e85d736181b5559d7a0f2b87581b2bf98d04fce`
getaggt; erreichbar ist das nur von Hand mit `./prod.sh 2e85d73…`, nicht über den Knopf.

**Achtung beim Rückweg auf v0.0.14:** Der erste Deploy fährt die Migration
`20260928001`, die `project.centroid` löscht. v0.0.14 mappt die Spalte noch, und sein
Entrypoint kennt `db_ahead.py` nicht. Ein Rückweg auf v0.0.14 nach dem ersten Deploy
braucht deshalb den Restore des Dumps von direkt davor (`backups/pre-migrate_…`).

## Konventionen für Änderungen (Definition of Done)

- [ ] `make test` ist grün (fährt auch die Image-Builds, also: Build gelingt allein aus dem Repo).
- [ ] `compose.yaml` referenziert GHCR-Images über `${IMAGE_TAG}`, kein `build:`.
- [ ] Neue Konfiguration in `.env.prod.example`; neue Pflicht-Felder in `Settings`
      zusätzlich mit Default in `apps/backend/tests/conftest.py`.
- [ ] `/healthz` deckt neue Pflicht-Abhängigkeiten mit ab.
- [ ] Migrationen: Alembic, rückwärtskompatibel (Expand/Contract). Spalten erst im
      Release **nach** dem löschen, ab dem der Code sie nicht mehr mappt.
- [ ] Kein Zustand im Containerlayer (Uploads/DB/Backups → Volumes bzw. `backups/`).
- [ ] `CHANGELOG.md` ergänzt.
- [ ] `apps/backend/requirements.txt` bleibt exakt (`==`) gepinnt.
- [ ] Bei Änderungen am Deploy-Ablauf: diese Datei und `docs/production_setup.md`
      aktualisieren.
