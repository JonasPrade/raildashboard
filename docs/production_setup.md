# Produktions-Setup

Diese Datei beschreibt alles, was beim Aufsetzen der Produktionsumgebung zu beachten ist.
Entwicklungshinweise und laufende Features: siehe `docs/roadmap.md`.
Architekturübersicht: siehe `docs/architecture.md`.

---

## Voraussetzungen

| Komponente | Mindestversion | Hinweis |
|------------|---------------|---------|
| Python | 3.11+ | Für Backend + Alembic |
| Node.js | 20+ | Für Frontend-Build |
| PostgreSQL | 15+ | Mit PostGIS-Erweiterung |
| PostgreSQL-Client-Tools | passend zur DB-Version | `pg_dump`, `pg_restore` |
| nginx (oder caddy) | — | Reverse Proxy vor Backend + Frontend |

---

## Umgebungsvariablen

Das Template für alle Produktionsvariablen liegt unter `.env.example`.
Für die Produktion eine eigene Datei anlegen:

```bash
cp .env.example .env
# Alle Werte in .env ausfüllen (DB_PASSWORD, BACKEND_CORS_ORIGINS, etc.)
```

### Pflichtfelder (Entwicklungsdefaults reichen nicht)

| Variable | Produktionswert (Beispiel) | Hinweis |
|----------|---------------------------|---------|
| `DB_USER` | `raildashboard` | PostgreSQL-Benutzer, den Docker-Compose anlegt |
| `DB_PASSWORD` | Sicheres Passwort | `DATABASE_URL` wird automatisch daraus zusammengesetzt — **nicht** doppelt setzen |
| `BACKEND_CORS_ORIGINS` | `["https://deine-domain.de"]` | **Niemals `*`** — auf die echte Domain setzen |
| `VITE_API_BASE_URL` | Leer lassen (`""`) | nginx proxied `/api/` zum Backend — nur ausfüllen wenn kein nginx |

### Optionale, aber empfohlene Felder

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `ROUTING_BASE_URL` | `http://graphhopper:8989` | GraphHopper-Dienst im Docker-Netzwerk |
| `ROUTING_TIMEOUT_SECONDS` | `20` | Timeout für Routing-Anfragen in Sekunden |
| `GRAPH_VERSION` | `1` | Hochzählen nach neuem OSM-Extrakt (busted Route-Cache) |
| `GH_OSM_URL` | `https://download.geofabrik.de/…` | OSM PBF URL; GraphHopper lädt die Datei beim ersten Start automatisch herunter |
| `REACT_APP_TILE_LAYER_URL` | — | Raster-Kachel-URL für die Kartenansicht |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Redis im Docker-Netzwerk (kein Passwort nötig, da nicht nach außen exponiert) |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Wie `CELERY_BROKER_URL` |
| `IMPORT_STAGING_DIR` | `/app/uploads/import-staging` | Ablage hochgeladener Import-PDFs, bis der Celery-Task sie gelesen hat. Muss im von Backend **und** Worker gemounteten `uploads`-Volume liegen |

### Optionale RINF-API-Zugangsdaten

| Variable | Beschreibung |
|----------|--------------|
| `RINF_API_URL` | ERA RINF API Base-URL (Standard: `https://rinf.era.europa.eu/api`) |
| `RINF_USERNAME` | ERA RINF-Benutzername |
| `RINF_PASSWORD` | ERA RINF-Passwort |

### Optionale LLM-Konfiguration (KI-gestützte Extraktion)

Wird für die KI-gestützte Erkennung im VIB-Import und verwandten Features verwendet.
Leer lassen deaktiviert die Funktion vollständig.

| Variable | Beschreibung |
|----------|--------------|
| `LLM_BASE_URL` | OpenAI-kompatibler Endpunkt (`https://api.openai.com/v1`, Ollama-URL, etc.) |
| `LLM_API_KEY` | API-Schlüssel |
| `LLM_MODEL` | Modellname (Standard: `gpt-4o-mini`) |

---

## Deploy-Vertrag (Dispatch per Commit-SHA)

Der vollständige Vertrag steht in [`DEPLOY.md`](../DEPLOY.md), die Begründungen und die
Ausnahmen dieses Repos in [`docs/workflow.md`](workflow.md), die Handschritte für Server und
GitHub in [`docs/uebergabe-deploy.md`](uebergabe-deploy.md). Kurzfassung:

| Punkt | Wert |
|-------|------|
| Prüfung | `make test` — in `ci.yml` (`pull_request`, Job `Prüfung`) und `release.yml` (`push [master]`), ohne eigene Schritte |
| Images | `ghcr.io/jonasprade/raildashboard-{backend,frontend,db,graphhopper}:<commit-sha>` (+ `:latest`), gebaut von `release.yml` nach grüner Prüfung |
| Auslieferung | `deploy.yml`, von Hand: *Actions → deploy → Run workflow*; SHA leer = `master`, Rollback = frühere SHA |
| Host | Contabo `vmd92747`, `/srv/raildashboard`, Benutzer `deploy` (Gruppe `docker`, kein sudo). Auf dem Host laufen weitere Dienste — nur `/srv/raildashboard` anfassen. |
| Server-Dateien | `compose.yaml`, `prod.sh`, `.env` — von Hand gepflegt, nicht mehr per Pipeline hochgeladen |
| Release-Pin | `IMAGE_TAG=<40-stellige SHA>` in `.env`, gepflegt von `prod.sh` |
| Deploy-Schlüssel | `command="/srv/raildashboard/prod.sh",no-pty,…` in `authorized_keys`, ohne Interpolation |
| Backup vor der Migration | One-shot-Dienst `backup` → `backups/pre-migrate_<zeit>_<sha12>.dump`; ohne Backup startet das Backend nicht |
| Erfolgskriterium | Backend-Healthcheck auf `/healthz` (DB, Schema passt zum Code, Pflicht-Config, Upload-Verzeichnisse), danach `https://dashboard.schienengruen.de/healthz` von außen |
| Weg hinein | Host-nginx (TLS, Certbot) → `127.0.0.1:5000` (Container-nginx) → `backend:8000`. Kein Port auf `0.0.0.0`. |
| Upload-Limit | 50 MB, in drei Schichten gleich: Host-nginx (`client_max_body_size 50m`), Container-nginx (`apps/frontend/nginx.conf`), Backend (`MAX_FILE_SIZE`). Fehlt sie im Proxy, gilt dessen Default von 1 MB und Import-PDFs scheitern mit `413`. |

### Benötigte Secrets (GitHub → Environment `production`)

| Secret / Variable | Zweck |
|-------------------|-------|
| `DEPLOY_HOST` | Server-Hostname/IP |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | Privater Schlüssel, dessen öffentlicher Teil mit erzwungenem Kommando in `authorized_keys` steht |
| `DEPLOY_PORT` *(optional)* | SSH-Port, Default 22 |
| `GITHUB_TOKEN` *(automatisch)* | Push nach GHCR in `release.yml`, `manifest inspect` in `deploy.yml` |
| `TILE_LAYER_URL` *(Repo-Variable)* | Raster-Kachel-URL, die zur Build-Zeit ins Frontend-Bundle gebacken wird (TopPlus). Die Server-`.env` beeinflusst die Kacheln nicht. |

Der Server meldet sich selbst bei GHCR an (classic Token, nur `read:packages`, als `deploy`);
die Pipeline reicht keinen Token mehr durch. **Der Token läuft ab** — daran ist der Release
v0.0.15 am 07.10.2026 gescheitert. Das Environment `production` ist Ablage, kein Tor
(Required Reviewers gibt es für private Repos ohne bezahlten Plan nicht); das Tor ist der
Dispatch.

### Server-Zugang

- **SSH-Whitelist:** `sshd_config` nutzt `AllowUsers` (aktuell `AllowUsers gasteladmin deploy`).
  Backup der Config unter `/etc/ssh/sshd_config.bak.*`. Nach Änderungen `sudo sshd -t` +
  `systemctl reload ssh`.
- **Volumes** `raildashboard_pgdata`, `raildashboard_uploads`, `raildashboard_ghdata`;
  `compose.yaml` setzt `name: raildashboard`, damit die Namen fest bleiben.

---

## Legacy: Erstmalige Einrichtung (ohne Docker)

```bash
# 1. Abhängigkeiten installieren
make install

# 2. Datenbank anlegen und PostGIS aktivieren (als postgres-Superuser)
psql -U postgres -c "CREATE DATABASE raildashboard;"
psql -U postgres -d raildashboard -c "CREATE EXTENSION postgis;"

# 3. Migrationen einspielen
make migrate

# 4. Ersten Admin-User anlegen
make create-user USERNAME=admin ROLE=admin

# 5. Frontend bauen
make build
```

---

---

## Docker Deployment (empfohlen)

Alle Services laufen in Docker. Das Frontend wird von nginx als statische Dateien ausgeliefert; nginx proxied `/api/` an den Backend-Container.

Der Container-nginx (`apps/frontend/nginx.conf`) komprimiert Text-Antworten per
gzip — auch die durchgereichten `/api/`-JSON-Antworten — und liefert die
gehashten Vite-Assets unter `/assets/` mit `Cache-Control: … immutable` aus
(`index.html` mit `no-cache`, damit neue Releases sofort greifen). Das Backend
startet uvicorn mit `--workers 2` (`apps/backend/Dockerfile`), damit synchrone
Import-/Extraktions-Requests andere Anfragen nicht serialisieren. Ein
vorgelagerter TLS-Proxy braucht daher selbst kein gzip/Caching zu übernehmen.
Damit das auch hinter einem Proxy greift, der per HTTP/1.0 weiterleitet (nginx-Default
ohne `proxy_http_version 1.1`), steht in der Container-Konfiguration
`gzip_http_version 1.0`. Zusätzlich komprimiert das Backend selbst per
`GZipMiddleware` (ab 1 KB, nicht für PDFs/Bilder) und sendet für
`/api/v1/project_groups/…` einen `ETag` (unveränderte Antworten → `304`).
Nichts davon erfordert eine Änderung am Host.

**Upload-Limit — drei Stellen, ein Wert.** Der Container-nginx erlaubt
`client_max_body_size 50m`, das Backend weist alles darüber mit `413` ab
(`utils/file_storage.MAX_FILE_SIZE`). Ein vorgelagerter Proxy muss denselben Wert
tragen, sonst greift *sein* Default: nginx lässt ohne die Direktive nur **1 MB**
durch und beantwortet z. B. den Haushaltsbericht Teil B (≈ 3,6 MB) mit
`413 Request Entity Too Large`, bevor der Request die Anwendung überhaupt
erreicht. Caddy hat kein solches Default-Limit.

**MCP-Endpunkt `/mcp`.** Das Backend stellt unter `/mcp` einen MCP-Server
(Streamable HTTP) für KI-Assistenten bereit; Zugriff nur mit persönlichem API-Key
(`Authorization: Bearer rdb_…`, angelegt unter *Administration → API-Keys & MCP*,
vorerst nur für Admins). Der Container-nginx leitet `location = /mcp` mit
`proxy_buffering off` und `proxy_read_timeout 300s` an `backend:8000` weiter. Ein
vorgelagerter Proxy muss nichts Besonderes tun, solange er `/mcp` wie jeden anderen
Pfad durchreicht (Caddy `reverse_proxy` und ein nginx-`location /` tun das); puffert
er Antworten, kommen die JSON-Antworten trotzdem vollständig an. Abschalten:
`MCP_ENABLED=false` in `.env`, dann ist die Route nicht gemountet. Die Tabelle
`api_keys` legt die Migration `20261007001` beim Start automatisch an.

### Voraussetzungen

- Docker Engine ≥ 24 und Docker Compose V2 (`docker compose`, nicht `docker-compose`)

### Erstmalige Einrichtung

Der Server benötigt **nur** `compose.yaml`, `prod.sh` und eine `.env` — kein Source-Checkout
und **kein lokaler Build**. Er **zieht fertige Images aus GHCR**; gebaut wird ausschließlich in
GitHub Actions. Die Schritte für einen bestehenden Server stehen in
[`docs/uebergabe-deploy.md`](uebergabe-deploy.md); für einen neuen Host sinngemäß:

```bash
# Als deploy in /srv/raildashboard (Dateien per Einfüge-Block, nicht per scp):
#   compose.yaml  ← compose.yaml aus dem Repo
#   prod.sh       ← deploy/prod.sh aus dem Repo, chmod +x
#   .env          ← .env.prod.example, alle Werte ausfüllen; IMAGE_TAG=<40-stellige SHA>
mkdir -p backups

# Einmalig bei GHCR anmelden (classic Token, nur read:packages)
read -rs -p "Token: " GHCR_PAT; echo
printf '%s' "$GHCR_PAT" | docker login ghcr.io -u <github-user> --password-stdin
unset GHCR_PAT

# Erst-Deploy: über den Knopf (Actions → deploy) oder von Hand
./prod.sh <40-stellige-sha>

# Ersten Admin-User anlegen
docker compose exec backend python scripts/create_initial_user.py --username admin --role admin
```

Bei einer frischen Datenbank kann der allererste Lauf am Backup scheitern, weil Postgres
während `initdb` kurz bereit meldet und dann neu startet; ein zweiter Lauf geht durch.

Alembic-Migrationen laufen automatisch beim Start des Backend-Containers (via `docker-entrypoint.sh`).

### Datenmigration (einmalig, vor dem ersten Start)

> **Achtung:** Diesen Schritt ausführen, bevor `make docker-prod-up` erstmals gestartet wird.

```bash
# 1. Backup der lokalen Datenbank
make backup-db

# 2. Prod-Stack starten (nur DB, damit das Volume existiert)
docker compose --env-file .env up -d db

# 3. Dump einspielen (DB_URL aus .env verwenden, aber Hostname = localhost)
make restore-db BACKUP=backups/<datei>.dump \
  DB_URL=postgresql://raildashboard:<password>@localhost:5432/raildashboard

# 4. Verifizieren: Anzahl Projekte in lokaler DB == Anzahl im Container
#    Dann Backend + Frontend starten
make docker-prod-up
```

### Späterer dev → prod DB-Transfer (laufender Betrieb)

Wenn die prod-DB nach dem ersten Datenimport nochmal mit dem aktuellen dev-Stand überschrieben werden soll, kann jetzt direkt `scripts/transfer_db.sh dev-to-prod` verwendet werden. Das Skript wurde nach dem v0.0.4-Rollout-Vorfall (2026-04-27, lautlos fehlgeschlagen + halbrestaurierter Zustand möglich) auf folgende Safety Rails aufgerüstet:

- Non-empty-Verifikation des lokalen Dumps **und** der Upload-Zieldatei auf dem Server.
- **Pre-Restore-Safety-Backup von prod** (`backups/prod_BEFORE_dev_overwrite_<ts>.dump`) — Rollback-Artefakt bleibt lokal liegen.
- Backend + Worker werden auf dem Server vor dem Restore gestoppt und am Ende **immer** wieder gestartet, auch bei Restore-Failure.
- `pg_terminate_backend` auf alle verbliebenen DB-Connections.
- Filter `SET transaction_timeout` (PG17 → PG16 Header-Mismatch).
- `psql -v ON_ERROR_STOP=1 --single-transaction` → ein Fehler rollt atomar zurück, prod bleibt im pre-restore Zustand.
- `COUNT(*)`-Vergleich auf `project`/`finve`/`change_log` lokal vs. prod nach dem Restore; ungleiche Zahlen → Exit ≠ 0.

```bash
./scripts/transfer_db.sh dev-to-prod   # mit Bestätigungs-Prompt vor dem Schreib-Schritt
./scripts/transfer_db.sh prod-to-dev   # umgekehrt; gleiche Safety-Rails
```

Bei einem Fehler bleibt der Dump immer in `backups/` liegen, sodass der manuell beschriebene Pfad unten als Fallback weiterhin nutzbar ist.

**Manueller Pfad — falls das Skript nicht passt oder ein Step debuggt werden muss:**

```bash
# === Auf dem Laptop ===
cd ~/code/raildashboard

# 1. Frischen Plain-SQL-Dump aus dev erzeugen
DUMP="backups/dev_to_prod_$(date +%Y%m%d_%H%M%S).sql"
LOCAL_URL=$(grep ^DATABASE_URL .env | cut -d= -f2- | tr -d '"' \
  | sed -E 's|^postgresql\+[a-z0-9]+://|postgresql://|')
pg_dump --format=plain --clean --if-exists --no-owner --no-privileges \
  "$LOCAL_URL" > "$DUMP"
ls -lh "$DUMP"

# 2. Sicherheits-Backup der prod-DB ziehen (vor dem Überschreiben!)
ssh contabo "cd /srv/raildashboard && \
  docker compose exec -T db pg_dump -U raildashboard -Fc raildashboard" \
  > "backups/prod_BEFORE_dev_overwrite_$(date +%Y%m%d_%H%M%S).dump"

# 3. Dump auf den Server schieben
scp "$DUMP" contabo:/srv/raildashboard/backups/

# === Auf dem Server (oder via ssh contabo "...") ===
cd /srv/raildashboard
DUMP=backups/dev_to_prod_<TIMESTAMP>.sql   # exakten Namen aus Schritt 3 einsetzen

# 4. Backend + Worker stoppen — sonst blockieren offene Connections die DROPs
docker compose stop backend worker

# 5. Aktive Verbindungen zur DB hart kappen (Sicherheitsgurt)
docker compose exec -T db psql -U raildashboard -d postgres -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE datname = 'raildashboard' AND pid <> pg_backend_pid();
"

# 6. Restore mit Fehlerstopp + Transaktion. transaction_timeout filtern,
#    weil pg_dump ab Postgres 17 dieses Setting in den Header schreibt,
#    Postgres 16 (im prod-Image) es aber nicht kennt.
grep -v '^SET transaction_timeout' "$DUMP" | \
  docker compose exec -T db psql -U raildashboard -d raildashboard \
    -v ON_ERROR_STOP=1 --single-transaction

# 7. Backend + Worker wieder starten
docker compose up -d backend worker

# 8. PFLICHT: Verifizieren, dass dev-Stand wirklich angekommen ist
docker compose exec -T db psql -U raildashboard -d raildashboard -c "
  SELECT 'projects' AS tbl, COUNT(*) FROM project
  UNION ALL SELECT 'change_log',   COUNT(*) FROM change_log
  UNION ALL SELECT 'project_text', COUNT(*) FROM project_text;
"
```

Auf dem Laptop denselben `COUNT(*)`-Vergleich gegen dev laufen lassen — die Zahlen müssen exakt übereinstimmen. Tun sie das nicht, ist der Restore nicht durchgelaufen (z. B. Schritt 6 mit Fehler abgebrochen → durch `--single-transaction` automatisch zurückgerollt → prod im alten Stand). Output von `psql` analysieren, Fehler beheben, Schritt 6 wiederholen.

**Hinweis:** `scripts/transfer_db.sh dev-to-prod` macht genau diese Schritte mittlerweile selbst — der manuelle Pfad bleibt hier als Fallback / Debug-Referenz dokumentiert.

### Nutzerverwaltung (Docker)

```bash
# Neuen Nutzer anlegen
make docker-create-user USERNAME=admin ROLE=admin
# Rollen: viewer | editor | admin

# Nutzer auflisten (lokale venv-Umgebung nötig)
make list-users

# Passwort ändern (läuft im Backend-Container)
docker compose --env-file .env exec backend python scripts/change_password.py --username <name>
```

### Logs und Monitoring

```bash
# Alle Logs des Stacks (live)
docker compose --env-file .env logs -f

# Nur Backend
docker compose --env-file .env logs -f backend

# Celery-Worker (PDF-Parsing, Hintergrundaufgaben)
make docker-worker-logs

# Health-Check des Backends abfragen (200 + {"status":"ok"} bei healthy)
curl http://localhost/api/v1/health
```

Der Backend-Container führt beim Start automatisch `alembic upgrade head` aus (`docker-entrypoint.sh`) — Migrationen müssen daher nicht manuell angestoßen werden. Der Worker-Container überspringt diesen Schritt via `SKIP_MIGRATIONS=1` und wartet zusätzlich per `depends_on.backend.condition: service_healthy` (Backend-Healthcheck pollt `/api/v1/health`, gibt 200 erst zurück nachdem alembic fertig ist und uvicorn lauscht), damit beide Container nicht parallel auf derselben Migration rennen (das führte beim v0.0.4-Rollout zu `psycopg2.errors.UniqueViolation: pg_class_relname_nsp_index`). Falls Migrationen manuell ausgeführt werden müssen:

```bash
make docker-migrate
```

### Hängt ein Import? Worker prüfen

Importe (Haushalt, VIB, Fulda, Bauportal) laufen als Celery-Aufträge. Läuft kein Worker, nimmt die
Anwendung den Upload trotzdem an — Celery meldet dauerhaft `PENDING` und die Import-Seite wartet
endlos. Die Oberfläche benennt diesen Fall selbst: Die Import-Seite zeigt nach ~15 s
den Grund, und **Administration → Systemstatus** (`/admin/system`, Recht `settings.manage`) zeigt
Broker, Worker und Warteschlange direkt an. Dieselbe Auskunft per API:

```bash
curl -u <user>:<pass> http://localhost/api/v1/tasks/workers
```

Auf dem Server nachsehen und neu starten:

```bash
docker compose --env-file .env ps worker
docker compose --env-file .env logs --tail=50 worker
docker compose --env-file .env up -d worker
```

Ein Auftrag, der während eines Worker-Neustarts hochgeladen wurde, ist verloren — die Datei danach
einfach erneut hochladen.

### Tägliches Backup via Docker

```bash
make docker-backup-db
# schreibt pro Lauf zwei Dateien mit identischem Timestamp:
#   backups/raildashboard_<timestamp>.dump      (pg_dump -Fc)
#   backups/uploads_<timestamp>.tar.gz          (Inhalt von Volume raildashboard_uploads)
```

### Uploads-Volume (Dateianhänge)

Das Docker-Volume `raildashboard_uploads` (im Compose-Stack als `uploads` deklariert, gemountet unter `/app/uploads` in Backend- **und** Worker-Container) enthält alle Dateianhänge von Projekttexten (`text-attachments/`).

Seit #149 liegen dort außerdem unter `import-staging/` die gerade hochgeladenen Import-PDFs (Haushalt, VIB, Fulda): Der Backend-Endpunkt legt die Datei ab und übergibt dem Celery-Task nur den Dateinamen, damit keine PDF-Inhalte mehr durch Redis gehen. Der Task löscht die Datei nach dem Lauf, auch im Fehlerfall; was ein Task nie abgeholt hat, wird nach 24 h beim nächsten Upload aufgeräumt. Der Ordner ist also flüchtig. Landet er in einem Backup, schadet das nicht. Der Worker braucht deshalb dasselbe Volume wie das Backend (`compose.yaml`), sonst scheitert jeder PDF-Import mit `FileNotFoundError`. `make backup-db` und `make docker-backup-db` sichern das Volume zusammen mit dem DB-Dump — aber nur, wenn sie jemand aufruft. **Das nächtliche Borg-Backup auf vmd92747 nimmt das Volume derzeit nicht mit** (siehe *Nächtliches Backup auf vmd92747*).

**Warum das wichtig ist:** Ohne paariges Uploads-Tar zeigen nach einem Restore alle `text_attachment`-Zeilen auf nicht vorhandene Dateien.

**Verhalten beim Backup:**
- DB-Dump und Uploads-Tar erhalten denselben Timestamp → sie bilden ein Paar.
- Retention 14 Tage gilt für beide Datei-Typen separat.
- Steht Docker nicht zur Verfügung oder existiert das Volume nicht (z. B. lokales Setup gegen Postgres ohne Docker), wird der Uploads-Schritt mit Hinweis übersprungen — der DB-Dump läuft weiter.
- Manuell unterdrückbar: `SKIP_UPLOADS_BACKUP=1 make backup-db`.
- Anderes Volume: `UPLOADS_VOLUME=other_name make backup-db`.

**Verhalten beim Restore:** `make restore-db BACKUP=backups/raildashboard_<ts>.dump` sucht automatisch nach `uploads_<ts>.tar.gz` im selben Verzeichnis und restored es ins Volume (Inhalt wird vorher geleert, damit gelöschte Dateien nicht erhalten bleiben). Steuerung:
- `UPLOADS=none` → nur DB restoren, Volume nicht anfassen.
- `UPLOADS=backups/uploads_other.tar.gz` → explizit anderes Tar verwenden.

Manueller Einzelschritt (z. B. nur Uploads zurückspielen):

```bash
docker run --rm \
  -v raildashboard_uploads:/data \
  -v $(pwd)/backups:/out:ro \
  alpine sh -c "rm -rf /data/* /data/.[!.]* 2>/dev/null; \
                tar xzf /out/uploads_<timestamp>.tar.gz -C /data"
```

### HTTPS / TLS (empfohlen für Produktion)

Das Docker-Setup gibt das Frontend nur auf `127.0.0.1:5000` frei. Für HTTPS braucht es einen vorgelagerten Reverse Proxy auf demselben Host (auf vmd92747: nginx + Certbot, Option B) mit automatischer Zertifikatsverwaltung (z. B. Caddy oder Certbot/nginx):

**Option A – Caddy (einfachste Variante):**

```
# /etc/caddy/Caddyfile
deine-domain.de {
    reverse_proxy localhost:5000
}
```

Caddy bezieht und erneuert Let's Encrypt-Zertifikate automatisch. Caddy begrenzt
den Request-Body nicht von sich aus — ein eigenes `request_body max_size` also nur
setzen, wenn es bewusst enger als 50 MB sein soll.

**Option B – nginx + Certbot:**

```bash
# Zertifikat einmalig ausstellen (nginx muss Port 80 hören)
certbot --nginx -d deine-domain.de
# Automatische Erneuerung via systemd-Timer ist nach certbot-Installation aktiv
```

certbot schreibt nur die TLS-Zeilen in den Server-Block — das Upload-Limit muss
von Hand nachgetragen werden, sonst bleibt es beim nginx-Default von 1 MB:

```nginx
server {
    server_name deine-domain.de;
    client_max_body_size 50m;   # deckungsgleich mit apps/frontend/nginx.conf

    location / {
        proxy_pass http://localhost:5000;
        # …
    }
    # … listen/ssl_* von certbot …
}
```

Danach `sudo nginx -t && sudo systemctl reload nginx`. Ob die *laufende*
Konfiguration die Direktive trägt — nicht nur die Datei — zeigt
`sudo nginx -T | grep client_max_body_size`.

Danach `BACKEND_CORS_ORIGINS` in `.env` auf die HTTPS-URL aktualisieren und den Stack neu starten:

```bash
make docker-prod-down && make docker-prod-up
```

### Updates einspielen

Jeder Merge nach `master` baut nach grünem `make test` die Images zu seinem Commit. Ausgerollt
wird per Knopf: *Actions → deploy → Run workflow*, SHA leer = aktueller Stand von `master`.
`prod.sh` zieht die Images, schaltet `IMAGE_TAG` um, startet den Stack (Backup → Migration →
App), wartet auf `/healthz` und rollt sonst automatisch auf den vorherigen SHA zurück.

**Rollback:** derselbe Knopf mit einer früheren SHA. Von Hand auf dem Server (als `deploy`):

```bash
cd /srv/raildashboard && ./prod.sh <40-stellige-sha>
```

Ein Version-Tag (`make release-check MILESTONE=vX.Y.Z`, `CHANGELOG.md`, `git tag`) benennt
einen Stand, rollt aber nichts aus.

### Entwicklung: nur DB in Docker

```bash
# DB starten (Port 5433, Daten persistent in Docker-Volume)
make docker-dev-up

# DATABASE_URL in .env anpassen (Vorlage: .env.docker-dev.example)
# Dann lokal weiterentwickeln wie bisher
make dev
```

### GraphHopper (Routing-Microservice)

GraphHopper ist als optionaler Service im Compose-Stack integriert. Kein lokales `data/`-Verzeichnis erforderlich — OSM-Daten und Graph-Cache werden in einem named Docker Volume (`ghdata`) gespeichert.

**Einrichtung:** `GH_OSM_URL` in `.env` setzen:
```dotenv
# Beispiel: Deutschland-Extrakt (~4 GB)
GH_OSM_URL=https://download.geofabrik.de/europe/germany-latest.osm.pbf
# Für Tests reicht ein kleinerer Regionalextrakt, z.B. Bayern (~500 MB):
# GH_OSM_URL=https://download.geofabrik.de/europe/germany/bayern-latest.osm.pbf
```

**Erster Start** — GraphHopper lädt die PBF-Datei automatisch herunter und baut den Graphen (dauert 5–30 min je nach Größe):
```bash
# GraphHopper startet automatisch mit dem restlichen Stack:
make docker-prod-up
# Logs verfolgen:
docker compose --env-file .env logs -f graphhopper
```

Folgestarts nutzen den Cache im Volume und starten in wenigen Sekunden.

**OSM-Extrakt aktualisieren:** `GRAPH_VERSION` in `.env` hochzählen (busted Route-Cache), dann den Stack neu starten. Das Volume `ghdata` löschen, damit GraphHopper die neue PBF herunterlädt:
```bash
docker compose --env-file .env down
docker volume rm raildashboard_ghdata   # erzwingt Neu-Download + Graph-Rebuild
make docker-prod-up
```

---

## Backup-System

### Manuell (sofort einsatzbereit)

Die Skripte `scripts/backup_db.sh` und `scripts/restore_db.sh` sind im Repo vorhanden.
Dumps und Uploads-Tarballs werden in `backups/` abgelegt (nicht im Git, durch `.gitignore` ausgeschlossen).

```bash
# Backup erstellen (DB-Dump + Uploads-Volume-Tar; liest DATABASE_URL aus .env)
make backup-db

# Mit produktionsspezifischer .env-Datei
make backup-db ENV_FILE=.env

# Nur DB, ohne Uploads (z. B. lokales Setup ohne Docker)
SKIP_UPLOADS_BACKUP=1 make backup-db

# Alle lokalen Backups auflisten (Dumps + Uploads-Tars)
make list-backups

# Wiederherstellen — paariges uploads_<ts>.tar.gz wird automatisch mit-restored
make restore-db BACKUP=backups/raildashboard_20260101_020000.dump ENV_FILE=.env

# Nur DB restoren, Uploads-Volume nicht anfassen
UPLOADS=none make restore-db BACKUP=backups/raildashboard_20260101_020000.dump
```

Das Backup-Skript:
- erstellt zwei Dateien pro Lauf mit identischem Timestamp: `raildashboard_<ts>.dump` (pg_dump -Fc) und `uploads_<ts>.tar.gz` (tar.gz des Docker-Volumes `raildashboard_uploads`)
- strippt automatisch den SQLAlchemy-Treiber-Qualifier (`+psycopg2`) aus der URL, den `pg_dump` nicht versteht
- maskiert das Passwort im Output (`postgresql://user:***@host/db`)
- löscht Backups die älter als 14 Tage sind — DB-Dumps und Uploads-Tars separat (lokale Rotation)
- überspringt den Uploads-Teil mit Hinweis, wenn Docker fehlt oder das Volume nicht existiert

### Nächtliches Backup auf vmd92747 (Borg)

Auf dem Produktionshost sichert `/root/create_backup.sh` (root-Crontab, täglich 04:05) den
ganzen Host nach Borg; Log unter `/var/log/borg/backup.log`. Für raildashboard heißt das:

1. `docker exec raildashboard-db-1 pg_dump -U raildashboard raildashboard | gzip` →
   `/srv/db_dumps/raildashboard.sql.gz` (konsistenter Dump im laufenden Betrieb).
2. Alle laufenden Container werden gestoppt.
3. `borg create` über `/root`, `/srv`, `/home`, `/etc`,
   `/var/lib/docker/volumes/raildashboard_pgdata` (u. a.). `/srv` enthält auch
   `/srv/raildashboard/backups/` mit den Pre-Migrate-Dumps des Deploys.
4. Die zuvor laufenden Container werden wieder gestartet.

**Nicht gesichert wird das Volume `raildashboard_uploads`** (Textanhänge). Bis es in die
`borg create`-Liste aufgenommen ist, bleibt `make docker-backup-db` der einzige Weg, es zu
sichern. Weil das Skript Container mit Namen anspricht (`raildashboard-db-1`), bleibt der
Compose-Projektname fest `raildashboard` (DEPLOY.md, „Backup & Restore").

Der früher hier beschriebene systemd-Timer (`/opt/raildashboard`, Benutzer `raildashboard`)
stammt aus der Zeit ohne Docker und ist auf vmd92747 nicht eingerichtet.

### Optionaler Remote-Upload via rclone

Für eine zweite Sicherheitskopie (Schutz bei Datenverlust auf dem Server selbst):

1. `rclone` installieren und konfigurieren: `rclone config`
2. `BACKUP_REMOTE` in `.env` setzen:
   ```dotenv
   BACKUP_REMOTE=s3:mein-bucket/raildashboard/
   # oder: sftp:backup-server/raildashboard/
   # oder: b2:bucket-name/raildashboard/
   ```
3. `scripts/backup_db.sh` am Ende ergänzen:
   ```bash
   if [ -n "${BACKUP_REMOTE:-}" ]; then
       echo "→ Upload nach $BACKUP_REMOTE ..."
       rclone copy "$DUMP_FILE" "$BACKUP_REMOTE"
       rclone delete --min-age 30d "$BACKUP_REMOTE"
   fi
   ```

### Retention-Strategie (GFS)

| Ebene       | Aufbewahrung | Speicherort    |
|-------------|-------------|----------------|
| Täglich     | 14 Tage     | lokal          |
| Wöchentlich | 8 Wochen    | lokal + remote |
| Monatlich   | 12 Monate   | remote         |

Die wöchentliche/monatliche Ebene erfordert noch ein erweitertes Rotationsskript — vorerst manuell handhabbar.

### Backup verifizieren

Monatlich oder nach größeren Migrationen gegen eine Test-Datenbank prüfen:
```bash
make restore-db BACKUP=backups/raildashboard_YYYYMMDD_HHMMSS.dump ENV_FILE=.env.test
```

---

## Legacy: Reverse Proxy (nginx, ohne Docker)

Beispielkonfiguration für nginx — Backend unter `/api/`, Frontend-Build als statische Dateien:

```nginx
server {
    listen 443 ssl;
    server_name deine-domain.de;

    # Ohne diese Zeile greift der nginx-Default von 1 MB und große
    # Import-PDFs scheitern mit 413.
    client_max_body_size 50m;

    # Frontend (statische Dateien aus apps/frontend/dist)
    root /opt/raildashboard/apps/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend-Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Legacy: Backend als systemd-Service (ohne Docker)

```ini
# /etc/systemd/system/raildashboard-backend.service
[Unit]
Description=Raildashboard Backend (FastAPI)
After=network.target postgresql.service

[Service]
Type=simple
User=raildashboard
WorkingDirectory=/opt/raildashboard/apps/backend
EnvironmentFile=/opt/raildashboard/.env
ExecStart=/opt/raildashboard/apps/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now raildashboard-backend.service
```

---

## Legacy: Updates einspielen (ohne Docker)

```bash
git pull

# Backend-Abhängigkeiten aktualisieren (falls nötig)
make install-backend

# Migrationen einspielen
make migrate

# Frontend neu bauen
make build

# Backend neu starten
systemctl restart raildashboard-backend.service
```
