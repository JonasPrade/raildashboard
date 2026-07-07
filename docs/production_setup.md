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

## Deploy-Vertrag (tag-basierte CI/CD)

Build und Betrieb sind getrennte Welten: **GitHub Actions baut** unveränderliche Images und pusht sie nach GHCR, der **Produktivserver zieht** sie nur noch und startet sie. Der Server baut nie selbst.

| Punkt | Wert |
|-------|------|
| Pipeline | `.github/workflows/deploy.yml`, Trigger `on: push: tags: ['v*']` |
| Reihenfolge | Quality-Gates (`pytest`, `tsc`) → Image-Build → GHCR-Push (`:vX.Y.Z` + `:latest`) → SSH-Deploy |
| Registry / Images | `ghcr.io/jonasprade/raildashboard-backend`, `-frontend`, `-db` (jeweils `:${IMAGE_TAG}`) |
| Compose-Datei auf dem Server | `/srv/raildashboard/docker-compose.yml` (nur `image:`-Referenzen, kein `build:`) |
| Deploy-Skript | `/srv/raildashboard/deploy.sh` — von der Pipeline per SSH aufgerufen, `./deploy.sh <tag>` |
| Release-Pin | `IMAGE_TAG` in `.env` (früher `APP_VERSION`); `deploy.sh` setzt ihn automatisch |
| Health-URL (Erfolgskriterium) | Backend-Healthcheck auf `http://backend:8000/api/v1/health` (200 erst nach Alembic + uvicorn); extern `curl http://localhost/api/v1/health` |
| Deploy-User | Eingeschränkter `deploy`-User, dem `/srv/raildashboard/` gehört; Docker-Rechte nötig |

### Ablauf des Deploy-Schritts (in `deploy.sh`, identisch bei Pipeline und manuell)

1. Aktuell laufendes `IMAGE_TAG` als Rollback-Anker merken.
2. **DB-Backup vor der Migration** (`pg_dump -Fc` → `backups/pre-deploy_<tag>_<ts>.dump`). Schlägt das Backup fehl oder ist der Dump leer, **bricht der Deploy ab** — kein Backup, kein Update. Migrationen laufen danach automatisch im Backend-Entrypoint; ein Image-Rollback macht eine Migration **nicht** rückgängig, daher ist der Pre-Deploy-Dump der einzige Rückweg (Restore: siehe *Backup-System* → `make restore-db`).
3. `IMAGE_TAG` in `.env` auf das neue Tag setzen, `docker compose pull`, `docker compose up -d`.
4. Auf `healthy` des Backend-Containers warten (Timeout 180 s).
5. Bei fehlender Health: `IMAGE_TAG` auf den vorherigen Wert zurücksetzen und erneut `up -d` (Rollback auf das unveränderliche `:vX`-Image).

### Benötigte Secrets (GitHub → Repo oder Environment `production`)

Nur als GitHub-Secrets hinterlegen, **niemals** ins Repo committen:

| Secret / Variable | Zweck |
|-------------------|-------|
| `SSH_PRIVATE_KEY` | Privater Schlüssel des `deploy`-Users |
| `SSH_HOST` | Server-Hostname/IP |
| `SSH_USER` | Name des `deploy`-Users |
| `GHCR_TOKEN` *(optional)* | PAT mit `read:packages`, damit der Server private Images ziehen kann. Entfällt, wenn die GHCR-Packages öffentlich sind. |
| `GITHUB_TOKEN` *(automatisch)* | Wird im Build-Job mit `packages: write` zum Pushen nach GHCR genutzt — kein manuelles Secret. |
| `TILE_LAYER_URL` *(Repo-Variable, optional)* | Raster-Kachel-URL, die zur Build-Zeit ins Frontend-Bundle gebacken wird. |

Deploy-Ziel ist das GitHub-Environment `production`. Über einen **Required Reviewer** an diesem Environment lässt sich jeder Deploy zu einem manuellen Freigabe-Gate machen.

### Eingeschränkter Deploy-User (Härtung)

Empfohlen ist ein dedizierter `deploy`-User auf dem Server, dem nur `/srv/raildashboard/` gehört und der Mitglied der `docker`-Gruppe ist. Der von der Pipeline ausgeführte Befehl ist ausschließlich:

```bash
cd /srv/raildashboard && ./deploy.sh <tag>
```

Optional lässt sich der Schlüssel in `~/.ssh/authorized_keys` per `command="…"`-Forced-Command noch enger auf genau diesen Aufruf einschränken; dann müssen `docker-compose.yml`/`deploy.sh` allerdings auf anderem Weg aktualisiert werden (die Pipeline lädt sie sonst per `scp` hoch).

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

### Voraussetzungen

- Docker Engine ≥ 24 und Docker Compose V2 (`docker compose`, nicht `docker-compose`)

### Erstmalige Einrichtung

Der Server benötigt **nur** `docker-compose.yml`, `scripts/deploy.sh` und eine `.env` — kein Source-Checkout und **kein lokaler Build**. Der Server **zieht fertige Images aus der GitHub Container Registry (GHCR)**; gebaut wird ausschließlich in GitHub Actions (siehe *Deploy-Vertrag* unten).

```bash
# 1. Compose-Datei + Deploy-Skript auf den Server übertragen
ssh contabo "mkdir -p /srv/raildashboard"
scp docker-compose.yml contabo:/srv/raildashboard/
scp scripts/deploy.sh   contabo:/srv/raildashboard/   # landet als /srv/raildashboard/deploy.sh

# 2. Produktions-Umgebungsvariablen anlegen (Vorlage: .env.prod.example)
cp .env.prod.example .env
# .env öffnen und alle Werte ausfüllen:
#   - IMAGE_TAG=v1.2.0  ← gewünschtes Release-Tag (GHCR-Image-Tag)
#   - DB_PASSWORD, BACKEND_CORS_ORIGINS, etc.
scp .env contabo:/srv/raildashboard/

# 3. Bei privaten GHCR-Packages einmalig am Registry anmelden (sonst schlägt `pull` fehl)
ssh contabo "docker login ghcr.io -u <github-user>"
#   → alternativ die Packages in GitHub auf "public" stellen, dann entfällt der Login.

# 4. Erst-Deploy des gewünschten Tags (zieht Images, startet Stack, wartet auf Health)
ssh contabo "cd /srv/raildashboard && ./deploy.sh v1.2.0"

# 5. Ersten Admin-User anlegen
ssh contabo "cd /srv/raildashboard && docker compose exec backend python scripts/create_initial_user.py --username admin --role admin"
```

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

### Tägliches Backup via Docker

```bash
make docker-backup-db
# schreibt pro Lauf zwei Dateien mit identischem Timestamp:
#   backups/raildashboard_<timestamp>.dump      (pg_dump -Fc)
#   backups/uploads_<timestamp>.tar.gz          (Inhalt von Volume raildashboard_uploads)
```

### Uploads-Volume (Dateianhänge)

Das Docker-Volume `raildashboard_uploads` (im Compose-Stack als `uploads` deklariert, gemountet unter `/app/uploads` im Backend-Container) enthält alle Dateianhänge von Projekttexten. Es wird seit v0.0.5 **automatisch** zusammen mit dem DB-Dump gesichert — sowohl von `make backup-db` (systemd-Timer-Pfad) als auch von `make docker-backup-db`.

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

Das Docker-Setup hört auf Port 80. Für HTTPS empfiehlt sich ein vorgelagerter Reverse Proxy mit automatischer Zertifikatsverwaltung (z. B. Caddy oder Certbot/nginx):

**Option A – Caddy (einfachste Variante):**

```
# /etc/caddy/Caddyfile
deine-domain.de {
    reverse_proxy localhost:80
}
```

Caddy bezieht und erneuert Let's Encrypt-Zertifikate automatisch.

**Option B – nginx + Certbot:**

```bash
# Zertifikat einmalig ausstellen (nginx muss Port 80 hören)
certbot --nginx -d deine-domain.de
# Automatische Erneuerung via systemd-Timer ist nach certbot-Installation aktiv
```

Danach `BACKEND_CORS_ORIGINS` in `.env` auf die HTTPS-URL aktualisieren und den Stack neu starten:

```bash
make docker-prod-down && make docker-prod-up
```

### Updates einspielen (Regelfall: automatisch per Tag)

Ein Produktions-Update wird **nicht** mehr von Hand auf dem Server gebaut. Es genügt, im Repo einen Release-Tag zu setzen — die Pipeline `.github/workflows/deploy.yml` baut, pusht nach GHCR und deployt per SSH:

```bash
# Im Repo, auf dem Release-Commit:
make release-check MILESTONE=v1.3.0     # muss exit 0 liefern (Release-Gate)
# CHANGELOG.md: [Unreleased] → ## [v1.3.0] - YYYY-MM-DD verschieben, committen
git tag v1.3.0 && git push origin v1.3.0
```

Der Rest läuft automatisiert: Quality-Gates → Image-Build → GHCR-Push (`:v1.3.0` + `:latest`) → SSH-Deploy mit **DB-Backup vor der Migration** (bricht bei Fehler ab), `docker compose pull`, `up -d`, Health-Wait und **automatischem Rollback** auf das vorherige `:vX`-Image bei fehlender Health.

> **Voraussetzung beim Tag-Cut (im Repo, vor `git tag`):** `make release-check` muss exit 0 liefern — sonst hängen noch offene manuelle Verifikationen. Details: `AGENT.md` → Release Gate & Release & Deploy.

**Manuelles Deploy / Rollback** (falls die Pipeline nicht genutzt wird oder ein schneller Rollback nötig ist) — direkt auf dem Server das schon vorhandene Deploy-Skript aufrufen:

```bash
ssh contabo "cd /srv/raildashboard && ./deploy.sh v1.2.0"   # beliebiges bereits gepushtes Tag
```

`deploy.sh` macht dabei exakt dieselben Schritte wie die Pipeline (Backup → Tag setzen → pull → up -d → Health-Wait → Rollback). Ein Rollback ist damit einfach das erneute Deployen des vorherigen unveränderlichen Tags.

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

### Automatisierung via systemd-Timer

Einmalig auf dem Produktionsserver einrichten — danach läuft das Backup täglich automatisch.

**Service-Datei** `/etc/systemd/system/raildashboard-backup.service`:
```ini
[Unit]
Description=Raildashboard Datenbank-Backup
After=network.target

[Service]
Type=oneshot
User=raildashboard
WorkingDirectory=/opt/raildashboard
EnvironmentFile=/opt/raildashboard/.env
ExecStart=/opt/raildashboard/scripts/backup_db.sh
StandardOutput=journal
StandardError=journal
```

**Timer-Datei** `/etc/systemd/system/raildashboard-backup.timer`:
```ini
[Unit]
Description=Tägliches Raildashboard Backup

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

> `Persistent=true` stellt sicher, dass ein verpasster Lauf (z. B. wegen Serverausfall) beim nächsten Start nachgeholt wird.

**Aktivieren:**
```bash
systemctl daemon-reload
systemctl enable --now raildashboard-backup.timer

# Status prüfen
systemctl list-timers raildashboard-backup.timer

# Einmalig manuell testen
systemctl start raildashboard-backup.service
journalctl -u raildashboard-backup.service -n 50
```

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
