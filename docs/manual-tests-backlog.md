# Manuelle Tests — Backlog

Aufgeschobene manuelle Tests, die **heute nicht ausführbar** sind (z. B. weil sie
einen prod-Rollout, SSH-Zugang oder eine externe Quelle brauchen). Sofort
testbare Verifikation gehört **nicht** hierher, sondern als `Needs User Test` an
das zugehörige Board-Issue (siehe `docs/github-projects.md`).

Lebenszyklus: wächst, wenn ein Akzeptanzkriterium gerade nicht prüfbar ist;
schrumpft, sobald der nötige Pfad existiert — dann wird der Punkt in die
Test-Checkliste des ermöglichenden Issues hochgezogen und hier entfernt.

---

## Legacy — aus `review-checklist.md` migriert (Stand 2026-06-12)

Diese Punkte stammen aus der abgelösten `review-checklist.md`. Sie brauchen
prod-Zugang bzw. einen Release-Rollout und werden beim nächsten passenden
Rollout abgearbeitet, dann hier gestrichen.

### Selektives Löschen einzelner GeoJSON-Features (UI, dev-Stack)

- [ ] In „Geometrie verwalten" erscheint bei vorhandener Geometrie der Toggle „Einzelne Features auswählen & löschen". Bei einem Projekt **ohne** Geometrie wird er nicht angezeigt.
- [ ] Toggle aktivieren → Hint-Text und Counter („0 ausgewählt") erscheinen. Cursor wird beim Hover über existierende Linien/Punkte zur Hand.
- [ ] Klick auf eine Linie/Punkt: Feature wird rot, Counter springt auf 1. Erneut klicken: wieder blau, Counter 0.
- [ ] Mehrere Features auswählen → „Auswahl löschen (N)"-Button. Klick → Toast „N Feature(s) entfernt", Modal schließt sich, Karte zeigt die übrigen Features.
- [ ] Wenn **alle** Features ausgewählt werden und man löscht: `geojson_representation` wird auf null gesetzt (Projekt hat danach keine Geometrie mehr).
- [ ] Toggle „Einzelne Features..." und Toggle „Bestehende Geometrie löschen" sind gegenseitig **disabled** (kein gleichzeitiges Anhaben möglich).
- [ ] Während selectionMode aktiv ist: der untere „Übernehmen"-Footer-Button ist disabled (Aktionen laufen nur über den dedizierten „Auswahl löschen"-Button).
- [ ] „Zurücksetzen" leert die Auswahl wieder.
- [ ] Modal schließen und neu öffnen: selectionMode ist zurückgesetzt (off), Auswahl ist leer.

### Stations als Point-Features beim Route-Confirm (UI, dev-Stack)

- [ ] Auf `/projects/<id>` (als editor/admin) „Geometrie verwalten" öffnen.
- [ ] Im Modal: Start, optional Via, Ziel auswählen → „Route berechnen" → Route erscheint orange-dashed auf der Karte.
- [ ] Direkt „Übernehmen" klicken (ohne über „Betriebsstellen hinzufügen" nochmal die gleichen OPs zu wählen).
- [ ] Nach Refresh der Projektseite: Karte zeigt die Linie **und** die Start/Via/End-Bahnhöfe als Punkte.
- [ ] In der DB: `SELECT geojson_representation FROM project WHERE id=<id>` → FeatureCollection enthält eine LineString-Feature und zusätzlich für jede Station ein Point-Feature mit `properties.feature_type = "operational_point"` und korrektem `op_id`/`name`.
- [ ] Wenn man unter „Betriebsstellen hinzufügen" einen der Routen-Bahnhöfe nochmal manuell auswählt: nach Übernehmen ist die Station **nur einmal** im GeoJSON enthalten (Dedup über `op.id`).
- [ ] Wenn ein Projekt schon Geometrie hat und der Toggle „Bestehende Geometrie löschen" **nicht** aktiv ist: Route wird zwar bestätigt (POST /routes), aber `geojson_representation` bleibt unverändert — das ist bewusst so (Legacy-Verhalten).

### scripts/transfer_db.sh robust (braucht prod-SSH)

**dev → prod**

- [ ] `./scripts/transfer_db.sh dev-to-prod` läuft durch ohne Abbruch. Vorher: Bestätigungs-Prompt erscheint und kann mit `y` quittiert werden.
- [ ] Vor dem destruktiven Step liegt `backups/prod_BEFORE_dev_overwrite_<ts>.dump` (>0 Bytes). Diese Datei nicht löschen, bis das nächste reguläre Backup steht.
- [ ] `backups/dev_to_prod_<ts>.sql` wurde lokal erzeugt und nach Upload auf dem Server unter `/srv/raildashboard/backups/` mit identischer Größe vorhanden.
- [ ] Während des Restore: `docker compose ps backend worker` auf prod zeigt `Exited` (gestoppt, wie erwartet).
- [ ] Am Ende: `docker compose ps backend worker` auf prod wieder `Up` (auch wenn der Restore fehlschlagen würde).
- [ ] Letzte Skript-Zeile: `✓ Done. ... row counts match.` mit identischen Zahlen für `project`/`finve`/`change_log` lokal vs. prod.

**Fehlersimulation (einmalig)**

- [ ] Bewusst kaputten Dump testen: lokal eine SQL-Datei wie `dev_to_prod_BAD.sql` mit ungültigem SQL hinlegen, im Script den `pg_dump`-Aufruf temporär durch `cp` ersetzen, ausführen. Erwartet: `ERROR: Restore failed (exit X). Prod was rolled back automatically...`, Backend+Worker auf prod laufen wieder, prod-Daten unverändert (`SELECT COUNT(*) FROM project` identisch zu vorher).

**prod → dev**

- [ ] `./scripts/transfer_db.sh prod-to-dev` läuft durch, lokale DB hat danach die prod-Counts.
- [ ] Bei künstlich beschädigtem Dump rollt `--single-transaction` lokal sauber zurück (vorhandene lokale Daten bleiben — siehe COUNT-Vergleich vor/nach).

### /api/v1/health + Docker-Healthcheck (prod-Rollout)

- [ ] `curl http://localhost/api/v1/health` (auf prod) gibt `200 {"status":"ok"}` zurück. `curl http://localhost/api/health` (alte Doku-URL) gibt 404 — nicht 200; ist beabsichtigt.
- [ ] `docker compose --env-file .env ps backend` zeigt nach Start die Health-Spalte `(healthy)` (nicht nur `Up`).
- [ ] Beim nächsten Rollout: `docker compose --env-file .env logs worker` zeigt, dass der Worker tatsächlich erst hochfährt **nachdem** backend `healthy` ist (kein `Connection refused` / kein Connecting-to-broker-Loop am Anfang).
- [ ] Wenn das Backend hängt (z. B. DB weg): Healthcheck failt nach `start_period + retries*interval ≈ 110s`, Docker markiert Container als `unhealthy` → `restart: unless-stopped` greift.

### Migrations-Race backend/worker beheben (prod-Rollout)

**⚠ Vorab klären (einmalig)**

- [ ] Auf prod: läuft aktuell ein **lokaler** Celery-Worker (z. B. via tmux/systemd außerhalb von Docker)? Wenn ja, entscheiden:
  - lokalen Worker stoppen → Docker-Worker übernimmt; **oder**
  - Docker-Worker deaktivieren (`docker compose --env-file .env stop worker` und `worker`-Service auskommentieren / `replicas: 0`).
  - Hintergrund: Vor diesem Fix hat der Docker-Worker entgegen Doku **uvicorn** statt celery gestartet (Entrypoint hardcoded). Nach diesem Fix startet er tatsächlich celery → ohne Aufräumen würden zwei Worker parallel aus derselben Redis-Queue konsumieren.

**Beim nächsten Release-Rollout**

- [ ] `make docker-prod-down && make docker-prod-up` mit einer Version, die mindestens eine neue Alembic-Migration enthält.
- [ ] `docker compose --env-file .env logs backend | grep -i alembic` zeigt `Running Alembic migrations...` **genau einmal** und einen sauberen `Running upgrade ...`-Block ohne `UniqueViolation`.
- [ ] `docker compose --env-file .env logs worker | grep -i alembic` zeigt **`SKIP_MIGRATIONS=1 — Alembic step übersprungen.`** (kein `Running Alembic migrations...`).
- [ ] `docker compose --env-file .env ps backend` zeigt `Up` (kein `Restarting`-Loop, kein zweiter Anlauf nötig).

**Worker läuft jetzt wirklich Celery**

- [ ] `make docker-worker-logs` zeigt Celery-Banner (`celery@<hostname> v…`, `[tasks]`-Liste, `Connected to redis://…`). Vorher lief dort versehentlich uvicorn.
- [ ] Ein VIB- oder Haushalt-Import-Upload in der UI läuft durch und wechselt von `PENDING` auf `SUCCESS`. Falls ein paralleler lokaler Worker bisher die Tasks gefressen hat: ihn jetzt stoppen und Test wiederholen.

**Sanity**

- [ ] `docker compose --env-file .env exec backend python -c "from sqlalchemy import create_engine, text; import os; e=create_engine(os.environ['DATABASE_URL']); print(e.connect().execute(text('SELECT version_num FROM alembic_version')).scalar())"` gibt eine einzelne Revision aus (DB-Head).

### Backup um Docker-Volumes erweitert (prod, Shell-only)

**Backup-Lauf (manuell, auf prod)**

- [ ] `cd /srv/raildashboard && make backup-db` (oder via systemd-Trigger: `systemctl start raildashboard-backup.service`) läuft fehlerfrei durch.
- [ ] Im `backups/`-Verzeichnis liegen **zwei** neue Dateien mit identischem Timestamp: `raildashboard_<ts>.dump` und `uploads_<ts>.tar.gz`.
- [ ] `tar tzf backups/uploads_<ts>.tar.gz | head` zeigt mindestens das Verzeichnis `text-attachments/` sowie die tatsächlich hochgeladenen Dateien (nicht leer).
- [ ] `make list-backups` zeigt **beide** Datei-Typen mit Größe.

**Skip-Verhalten**

- [ ] `SKIP_UPLOADS_BACKUP=1 make backup-db` schreibt nur den Dump und gibt „Uploads-Backup übersprungen (SKIP_UPLOADS_BACKUP=1)." aus.
- [ ] Auf einem Rechner ohne Docker (oder ohne das Volume `raildashboard_uploads`) läuft `make backup-db` ohne Fehler weiter und meldet den Skip mit Begründung.

**Retention**

- [ ] Nach mindestens 15 Tagen Laufzeit: alte `raildashboard_*.dump` **und** `uploads_*.tar.gz` (> 14 Tage) werden rotiert. (`find backups -maxdepth 1 \( -name 'raildashboard_*.dump' -o -name 'uploads_*.tar.gz' \) -mtime +14` liefert keine Treffer nach einem Lauf.)

**Restore-Pfad (auf Test-Stack, nicht prod!)**

- [ ] `make restore-db BACKUP=backups/raildashboard_<ts>.dump` erkennt automatisch das paarige `uploads_<ts>.tar.gz` und nennt es im Bestätigungsdialog vor dem Restore.
- [ ] Nach Bestätigung: DB ist restored **und** das Volume `raildashboard_uploads` enthält wieder die Dateien aus dem Tar (per `docker run --rm -v raildashboard_uploads:/data alpine ls -R /data` prüfbar).
- [ ] In der App sind Datei-Anhänge an Projekttexten wieder downloadbar (Klick auf einen Anhang → Datei öffnet sich, kein 404).
- [ ] `UPLOADS=none make restore-db BACKUP=...dump` überspringt den Uploads-Teil; nur die DB wird restored.

**Systemd-Timer (prod)**

- [ ] `journalctl -u raildashboard-backup.service -n 50` nach dem nächsten geplanten Lauf zeigt beide Schritte (DB-Dump + Uploads-Tar) im Log.
