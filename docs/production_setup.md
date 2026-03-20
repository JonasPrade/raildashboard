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

Der Server benötigt **nur** `docker-compose.yml` und eine `.env` — kein Source-Checkout erforderlich. Docker clont den Code automatisch von GitHub.

```bash
# 1. Nur docker-compose.yml auf den Server übertragen
scp docker-compose.yml user@server:/opt/raildashboard/

# 2. Produktions-Umgebungsvariablen anlegen
cp .env.example .env
# .env öffnen und alle Werte ausfüllen:
#   - APP_VERSION=v1.2.0  ← gewünschtes Release-Tag
#   - DB_PASSWORD, BACKEND_CORS_ORIGINS, etc.
scp .env user@server:/opt/raildashboard/

# 3. Images bauen und Stack starten (auf dem Server)
make docker-prod-build
make docker-prod-up

# 4. Ersten Admin-User anlegen
make docker-create-user USERNAME=admin ROLE=admin
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

# Health-Check des Backends abfragen
curl http://localhost/api/health
```

Der Backend-Container führt beim Start automatisch `alembic upgrade head` aus (`docker-entrypoint.sh`) — Migrationen müssen daher nicht manuell angestoßen werden. Falls Migrationen manuell ausgeführt werden müssen:

```bash
make docker-migrate
```

### Tägliches Backup via Docker

```bash
make docker-backup-db   # schreibt in backups/raildashboard_<timestamp>.dump
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

### Updates einspielen

Kein `git pull` nötig — nur `APP_VERSION` in `.env` auf das neue Tag setzen, dann neu bauen:

```bash
# 1. APP_VERSION in .env aktualisieren, z.B.:
#    APP_VERSION=v1.3.0
nano .env

# 2. Images neu bauen (Docker clont den Code von GitHub) und Stack neu starten
make docker-prod-build   # baut alle Images vom neuen GitHub-Tag
make docker-prod-down
make docker-prod-up      # Migrationen laufen automatisch beim Start
```

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
Dumps werden in `backups/` abgelegt (nicht im Git, durch `.gitignore` ausgeschlossen).

```bash
# Backup erstellen (liest DATABASE_URL aus .env)
make backup-db

# Mit produktionsspezifischer .env-Datei
make backup-db ENV_FILE=.env

# Alle lokalen Dumps auflisten
make list-backups

# Wiederherstellen (fragt zur Sicherheit nach Bestätigung)
make restore-db BACKUP=backups/raildashboard_20260101_020000.dump ENV_FILE=.env
```

Das Skript:
- strippt automatisch den SQLAlchemy-Treiber-Qualifier (`+psycopg2`) aus der URL, den `pg_dump` nicht versteht
- maskiert das Passwort im Output (`postgresql://user:***@host/db`)
- löscht Dumps die älter als 14 Tage sind (lokale Rotation)

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
