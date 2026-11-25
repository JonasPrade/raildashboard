# CI-Runner auf Hetzner (Self-hosted)

`ci.yml` (`Prüfung`) und die beiden Jobs in `release.yml` (`Prüfung`, Image-Build) laufen
auf einem Self-hosted Runner auf Hetzner, sobald die Repo-Variable `CI_RUNNER` gesetzt ist.
Ohne die Variable laufen sie wie bisher auf `ubuntu-latest`. `deploy.yml` bleibt immer auf
`ubuntu-latest`: Es hält den Deploy-Schlüssel und läuft nie auf einem Server, der fremden
Code ausführt.

Der Grund für einen eigenen Runner: Der Docker-Layer-Cache bleibt lokal auf der Platte warm
(zusätzlich zum Registry-Cache in GHCR), und `make test` hängt nicht an der Laufzeit der
GitHub-Runner.

## Voraussetzungen

- Hetzner-Server **`linux/amd64`** (Cloud-Typen CX/CPX/CCX; **nicht** die ARM-Reihe CAX). Der
  Prod-Host ist amd64, `release.yml` baut ohne `platforms:`.
- Ubuntu 24.04 oder Debian 12, mindestens 4 vCPU, 8 GB RAM, 80 GB Platte (Layer-Cache,
  GraphHopper-/Maven-Builds).
- Docker mit buildx (`docker buildx version`).
- Das Repo ist privat. Ein Self-hosted Runner führt jeden PR-Code aus; er gehört nie an ein
  öffentliches Repo und nie auf einen Host mit Prod-Daten oder -Schlüsseln.

## Einrichten (einmalig)

1. Registrierungs-Token holen: GitHub → Repo → Settings → Actions → Runners →
   *New self-hosted runner* → Linux x64. Nur das Token aus dem Befehl `./config.sh … --token`
   kopieren; es gilt eine Stunde.
2. Auf dem Hetzner-Server als root, das Skript aus dem Repo per Einfüge-Block ablegen und
   ausführen:

   ```bash
   RUNNER_TOKEN=<token> bash hetzner-runner.sh
   ```

   Das Skript (`deploy/hetzner-runner.sh`) legt den Benutzer `gh-runner` an (Gruppe `docker`),
   installiert den Runner unter `/opt/actions-runner` mit dem Label `hetzner` als
   systemd-Dienst und richtet einen täglichen Docker-Prune ein (älter als 7 Tage).
3. Prüfen: GitHub → Settings → Actions → Runners zeigt den Runner als *Idle*.
4. Umschalten: Settings → Secrets and variables → Actions → *Variables* →
   `CI_RUNNER` = `hetzner`.
5. Einen PR anlegen oder neu starten: Der Job `Prüfung` muss auf dem Runner laufen (im Lauf
   unter „Set up job“ steht der Runner-Name `<host>-ci`).

## Zurück auf GitHub-Runner

Variable `CI_RUNNER` löschen. Der nächste Lauf nimmt wieder `ubuntu-latest`; der Runner kann
stehen bleiben.

## Betrieb

- Dienst: `systemctl status 'actions.runner.*'`, Logs: `journalctl -u 'actions.runner.*' -e`.
- Runner-Update: GitHub aktualisiert den Runner selbst; ein Neuinstallieren geht mit
  `./svc.sh uninstall`, `./config.sh remove --token <token>` und erneutem Skriptlauf.
- Platte voll: `docker system df`, dann `docker builder prune -af`. Der Cache baut sich über
  GHCR (`…:pruefcache-*`) wieder auf.
- Der Benutzer in der Gruppe `docker` ist root-gleich auf diesem Server. Deshalb keine
  weiteren Dienste, Schlüssel oder Daten auf dem Host.
