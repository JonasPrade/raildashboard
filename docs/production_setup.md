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

Alle Variablen sind in `.env.example` vollständig dokumentiert (README.md → "Configuration").
Für die Produktion eine eigene Datei anlegen:

```bash
cp .env.example .env.prod
```

Folgende Werte **müssen** für die Produktion angepasst werden (Entwicklungsdefaults reichen nicht):

| Variable | Produktionswert (Beispiel) |
|----------|---------------------------|
| `DATABASE_URL` | `postgresql+psycopg2://user:password@localhost:5432/raildashboard` |
| `BACKEND_CORS_ORIGINS` | `["https://deine-domain.de"]` — nicht `*` |
| `VITE_API_BASE_URL` | `https://deine-domain.de/api` — nicht localhost |

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

```bash
# 1. Produktions-Umgebungsvariablen anlegen
cp .env.docker.example .env.prod
# .env.prod öffnen und alle Werte ausfüllen (DB_PASSWORD, BACKEND_CORS_ORIGINS, etc.)

# 2. Images bauen und Stack starten
make docker-prod-build
make docker-prod-up

# 3. Ersten Admin-User anlegen
make docker-create-user USERNAME=admin ROLE=admin
```

Alembic-Migrationen laufen automatisch beim Start des Backend-Containers (via `docker-entrypoint.sh`).

### Datenmigration (einmalig, vor dem ersten Start)

> **Achtung:** Diesen Schritt ausführen, bevor `make docker-prod-up` erstmals gestartet wird.

```bash
# 1. Backup der lokalen Datenbank
make backup-db

# 2. Prod-Stack starten (nur DB, damit das Volume existiert)
docker compose --env-file .env.prod up -d db

# 3. Dump einspielen (DB_URL aus .env.prod verwenden, aber Hostname = localhost)
make restore-db BACKUP=backups/<datei>.dump \
  DB_URL=postgresql://raildashboard:<password>@localhost:5432/raildashboard

# 4. Verifizieren: Anzahl Projekte in lokaler DB == Anzahl im Container
#    Dann Backend + Frontend starten
make docker-prod-up
```

### Tägliches Backup via Docker

```bash
make docker-backup-db   # schreibt in backups/raildashboard_<timestamp>.dump
```

### Updates einspielen

```bash
git pull
make docker-prod-build   # Images neu bauen (inkl. neuem Frontend-Build)
make docker-prod-down
make docker-prod-up      # Migrations laufen automatisch beim Start
```

### Entwicklung: nur DB in Docker

```bash
# DB starten (Port 5433, Daten persistent in Docker-Volume)
make docker-dev-up

# DATABASE_URL in .env anpassen (Vorlage: .env.docker-dev.example)
# Dann lokal weiterentwickeln wie bisher
make dev
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
make backup-db ENV_FILE=.env.prod

# Alle lokalen Dumps auflisten
make list-backups

# Wiederherstellen (fragt zur Sicherheit nach Bestätigung)
make restore-db BACKUP=backups/raildashboard_20260101_020000.dump ENV_FILE=.env.prod
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
EnvironmentFile=/opt/raildashboard/.env.prod
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
2. `BACKUP_REMOTE` in `.env.prod` setzen:
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
EnvironmentFile=/opt/raildashboard/.env.prod
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
