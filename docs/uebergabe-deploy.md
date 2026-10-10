# Übergabe: was von Hand einzurichten ist

Ein frischer Klon reproduziert das hier nicht. Die Liste folgt „Was von Hand
eingerichtet wird" aus [`docs/workflow.md`](workflow.md), ausgefüllt für dieses Repo und
den Contabo-Host `vmd92747`. Vorlage war die Umstellung von `JonasPrade/dtakt_mitglied`
am 08.10.2026; deren Lehren sind hier eingearbeitet.

**Stand 09.10.2026:** Bestandsaufnahme erledigt (siehe unten), Repo umgebaut, Schritte 2–7
offen. Produktion läuft auf **v0.0.14** (`2e85d73`); der Release v0.0.15 ist am 07.10.2026
an einem abgelaufenen GHCR-Token gescheitert (`denied: denied`) und wird mit dem ersten
Deploy über den Knopf nachgeholt.

Reihenfolge einhalten: **Schritt 5 (Server) vor dem ersten Ausrollen**, und die
`authorized_keys`-Zeile (Schritt 3) erst, wenn `prod.sh` auf dem Server liegt und die
Gegenprobe bestanden hat.

## Bedienung (aus dem ersten Lauf beim mitglieder-service)

- `sudo -iu deploy` schluckt mit eingefügte Folgezeilen in der Passwortabfrage. Erst
  wechseln, dann die Befehle in einem eigenen Block.
- Nach `sudo -iu deploy` liegt man in `~`. Jeder Block beginnt mit `cd /srv/raildashboard`.
- In der deploy-Shell kein `sudo`, `deploy` hat kein Passwort. Admin-Benutzer auf diesem
  Host ist `gasteladmin`.

---

## Bestandsaufnahme (09.10.2026)

| | |
|---|---|
| Host | `vmd92747.contaboserver.net`, `x86_64` — nicht dtakt-cloud |
| Dienstverzeichnis | `/srv/raildashboard`, Eigentümer `deploy`: `.env`, `docker-compose.yml`, `deploy.sh`, `backups/` |
| Compose-Datei | `docker-compose.yml` (Label `config_files`); Inhalt bereits v0.0.15 (`989cae39…`), weil der gescheiterte Lauf sie vor dem Login-Fehler per `scp` hochlud. Die Container laufen aus der v0.0.14-Fassung. |
| Laufender Stand | `IMAGE_TAG=v0.0.14`, Container `raildashboard-<dienst>-1`, Projekt `raildashboard`, Netz `raildashboard_raildashboard-net` |
| Proxy | nginx auf dem Host (systemd), `dashboard.schienengruen.de` → `http://localhost:5000`, TLS per Certbot, `client_max_body_size 50m`. Kein Caddy, kein Netz `web`. |
| Ports | `0.0.0.0:5000` (frontend) und `0.0.0.0:8989` (graphhopper), beide an nginx vorbei erreichbar |
| Routing | `ROUTING_BASE_URL=http://graphhopper:8989` — über das Compose-Netz, die Freigabe 8989 braucht niemand |
| Backups | `pre-deploy_v0.0.14_20260928_112121.dump`, `pre-deploy_v0.0.13_…`, `manual_pre_cicd_20260707_114308.dump` |
| Alte Images | v0.0.5 … v0.0.14 je Dienst, dazu `raildashboard-*:latest` von vor fünf Monaten |
| Nächtliches Backup | `/root/create_backup.sh` (root-Crontab `5 4 * * *`), Borg: `pg_dump` aus `raildashboard-db-1` nach `/srv/db_dumps/`, dann alle Container gestoppt, Archiv von `/root /srv /home /etc` + Volume `raildashboard_pgdata`, Container wieder gestartet. Seit 10.10.2026 auch `raildashboard_uploads` (vorher fehlte es). |
| Überwachung | `/root/check_containers.sh` stündlich gegen `/root/expected_containers.txt` (frontend, backend, worker, db, redis; graphhopper seit 10.10.2026); `/root/monitored_software.yaml` fragt `raildashboard-redis-1` ab |

---

## 1. Branch Protection auf `master` — entfällt vorerst

**Nicht einrichtbar ohne bezahlten Plan.** GitHub setzt Branch Protection und Rulesets
für private Repositories erst ab einem bezahlten Plan durch (beim mitglieder-service am
08.10.2026 ausprobiert). Warum Produktion trotzdem geschützt ist: [`DEPLOY.md`](../DEPLOY.md),
„GitHub-Konfiguration". Nach einem Upgrade: Settings → Branches → Regel für `master`,
*Require a pull request*, *Require status checks* → **`Prüfung`** (Job-Name; der Name
stammt aus einem echten Lauf, nicht aus der Datei).

## 2. Environment `production`

Settings → Environments → `production`:

- *Deployment branches*: `master`
- Secrets darin: `DEPLOY_HOST`, `DEPLOY_USER` (= `deploy`), `DEPLOY_SSH_KEY`, optional
  `DEPLOY_PORT`. Der Schlüssel kann der bisherige CI-Schlüssel des `deploy`-Benutzers sein
  (öffentlicher Teil in `/home/deploy/.ssh/authorized_keys`); entscheidend ist die neue
  Einschränkung in Schritt 3.
- Die alten Repo-Secrets `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `GHCR_TOKEN` erst nach
  dem zweiten erfolgreichen Deploy löschen.

Die Umgebung ist **Ablage und Protokoll, kein Tor** (Required Reviewers nur für
öffentliche Repositories auf Free/Pro/Team). Das Tor ist der Dispatch.

## 3. `authorized_keys` auf vmd92747 einschränken

Bisher trägt der CI-Schlüssel **kein** erzwungenes Kommando; die Pipeline rief `mkdir`,
`scp`, `chmod` und `deploy.sh` frei auf. Neu, **erst nach Schritt 5 und der Gegenprobe**:

```
command="/srv/raildashboard/prod.sh",no-pty,no-agent-forwarding,no-port-forwarding,no-X11-forwarding ssh-ed25519 AAAA… <kommentar>
```

Vorher eine Sicherung anlegen, andere Zeilen nicht anfassen. Prüfen mit abgekürzten
Schlüsseln:

```bash
sudo grep -n 'command=' /home/deploy/.ssh/authorized_keys | sed -E 's/(ssh-[a-z0-9-]+ [A-Za-z0-9+\/]{12})[A-Za-z0-9+\/=]+/\1…/'
```

## 4. GHCR-Login auf dem Server

Als Benutzer `deploy` mit einem Pull des neuen Images prüfen:

```bash
docker pull ghcr.io/jonasprade/raildashboard-backend:<merge-sha>
```

Bei `denied` einen neuen **classic** Token (nur `read:packages`) anlegen, kein
fine-grained, und so anmelden:

```bash
read -rs -p "Token: " GHCR_PAT; echo
printf '%s' "$GHCR_PAT" | docker login ghcr.io -u <github-user> --password-stdin
unset GHCR_PAT
```

Ablaufdatum notieren (Todoist-Erinnerung eine Woche vorher, mit dieser Anleitung im
Kommentar).

## 5. Server-Dateien austauschen

Als `deploy` in `/srv/raildashboard/`, per Einfüge-Block (`cat <<'EOF'`), nicht per `scp`;
SHA-256 jeder Datei gegen das Repo prüfen:

- `compose.yaml` ← `compose.yaml` aus dem Repo
- `prod.sh` ← `deploy/prod.sh` aus dem Repo, `chmod +x`
- `docker-compose.yml` → `docker-compose.yml.alt`, `deploy.sh` → `deploy.sh.alt`
  (umbenennen, nicht löschen; neben `compose.yaml` würde Compose die alte Datei
  ignorieren, aber warnen)

Danach `docker compose config`: keine `WARN`-Zeile, nur `127.0.0.1:5000`, kein `8989`.

**Rückweg sichern.** `IMAGE_TAG` steht auf `v0.0.14`, unter einer SHA liegt in GHCR davon
nichts. Deshalb die vier laufenden Images lokal auf die Commit-SHA von v0.0.14 taggen und
`IMAGE_TAG` darauf setzen (`.env` vorher sichern):

```bash
for s in backend frontend db graphhopper; do
  docker tag ghcr.io/jonasprade/raildashboard-$s:v0.0.14 ghcr.io/jonasprade/raildashboard-$s:2e85d736181b5559d7a0f2b87581b2bf98d04fce
done
```

Jeweils prüfen, dass beide Tags dieselbe Image-ID haben. `prod.sh` rollt nur auf eine
vorherige **SHA** zurück; steht dort noch `v0.0.14`, meldet es bei einem Fehlschlag
`CRITICAL` statt zurückzurollen.

**Achtung:** v0.0.14 hat noch kein `db_ahead.py` und mappt `project.centroid`, das die
Migration `20260928001` löscht. Der automatische Rückweg greift beim ersten Deploy also
nur, wenn die Migration nicht gelaufen ist (Backup gescheitert, Pull gescheitert). Ist sie
gelaufen, braucht der Rückweg auf v0.0.14 den Restore des `pre-migrate_*`-Dumps
(`DEPLOY.md`, „Backup & Restore").

**Vorprüfung für `/healthz`.** Das neue Tor verlangt mehr als `SELECT 1`. Was es prüft,
vorher am laufenden Stand nachsehen (als `deploy`), sonst rollt der erste Deploy zurück,
obwohl der Code stimmt:

```bash
cd /srv/raildashboard
docker compose -f docker-compose.yml exec -T backend sh -c 'for d in /app/uploads/text-attachments /app/uploads/import-staging; do mkdir -p "$d" && touch "$d/.probe" && rm "$d/.probe" && echo "ok $d"; done'
grep -c '^SESSION_SECRET_KEY=change-me' .env
```

Erwartet: zweimal `ok …` und `0`.

**Gegenprobe**, als `gasteladmin`:

```bash
sudo -u deploy env SSH_ORIGINAL_COMMAND='x kaputt' /srv/raildashboard/prod.sh; echo "exit=$?"
```

→ `exit=2`.

## 6. Alte Auslöser abschalten

Der Tag-Deploy ist mit diesem PR aus `deploy.yml` verschwunden. **Vorhandene Tags lösen
nichts mehr aus**, und `git tag vX.Y.Z && git push` rollt ab jetzt auch nichts mehr aus.
Die alte `deploy.sh` auf dem Server erst entfernen, wenn zwei Deploys über `prod.sh`
geklappt haben.

## 7. Erster Lauf

1. PR mergen → `release.yml` läuft, baut die vier Images zum Merge-Commit.
2. Actions → *deploy* → *Run workflow*, SHA leer lassen.
3. Woran das **neue** `prod.sh` zu erkennen ist: die Zeile `==> Deploy <alt> -> <neu>` und
   ein Pull mit je einer Zeile pro Image (`--quiet`). Ein Pull mit Fortschritt je Layer
   käme vom alten Skript.
4. Danach prüfen: Container healthy, nur `127.0.0.1:5000` freigegeben, neuer
   `backups/pre-migrate_*`-Dump, Migrationen `20261007001` und `20260928001` im
   Backend-Log, `https://dashboard.schienengruen.de/healthz` von außen.

Der Knopf erscheint **erst nach dem Merge**.

## 8. Nacharbeiten (nach zwei erfolgreichen Deploys)

- `docker-compose.yml.alt`, `deploy.sh.alt`, `.env`-Sicherung löschen — die Dateien gehören
  `deploy`, also `sudo -u deploy rm …`.
- Alte Images entfernen bis auf den laufenden Stand und den Rückweg; dazu die
  `raildashboard-*:latest` von vor fünf Monaten.
- `/etc/nginx/sites-available/dashboard.schienengruen.de.bak-20260914` (nicht verlinkt).
- Alte Repo-Secrets (Schritt 2).
- In `DEPLOY.md` → „Rollback" die erste über den Knopf erreichbare SHA eintragen.

---

## Was dabei aufgefallen ist und nicht in diesem PR steckt

- **Erledigt am 10.10.2026, außerhalb des Repos:**
  - `/var/lib/docker/volumes/raildashboard_uploads` steht jetzt in der `borg create`-Liste
    von `/root/create_backup.sh` (Sicherung: `create_backup.sh.bak-2026-10-10`). Vorher
    hatten die Textanhänge kein Backup; das Volume war zu dem Zeitpunkt noch leer.
  - `raildashboard-graphhopper-1` steht jetzt in `/root/expected_containers.txt`
    (Sicherung: `expected_containers.txt.bak-2026-10-10`); `check_containers.sh` lief
    danach mit Rückgabewert 0.
  - Offen: im Borg-Log nach dem nächsten Lauf (04:05) prüfen, dass er ohne Fehler durchlief.
- **Der letzte Borg-Lauf endete mit `Error: failed to start containers: rm-auth`.** Der
  Fallback per `docker compose up -d` hat den Container danach gestartet; betrifft den
  remarkable-mcp-Stack, nicht raildashboard. Sollte trotzdem jemand ansehen, weil ein
  gescheiterter Neustart nach dem nächtlichen Stopp sonst einen Dienst bis zum Morgen
  unten lässt.
- **`docs/production_setup.md` beschrieb einen systemd-Backup-Timer** unter
  `/opt/raildashboard`, den es auf vmd92747 nicht gibt; ersetzt durch den echten
  Borg-Ablauf.
- **`ENVIRONMENT` ist in der Server-`.env` nicht gesetzt**, die App läuft damit als
  `development`. Zu prüfen, ob das irgendwo Verhalten ändert.
- **`BACKEND_CORS_ORIGINS` fehlt in der Server-`.env`** (Default `http://localhost:5173`).
  Unkritisch, solange das Frontend same-origin spricht.
- **Backend-Tests laufen nicht gegen die echte Datenbank** (`docs/workflow.md`, Ausnahmen).
