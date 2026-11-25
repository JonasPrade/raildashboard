# CI-Runner auf Hetzner (Self-hosted)

Der Job `Prüfung` in `ci.yml` läuft auf dem Self-hosted Runner auf dem Hetzner-Dev-Server
(`ubuntu-8gb-fsn1-1`, **linux/arm64**, 8 GB RAM), weil GitHub-gehostete Jobs nicht starten,
solange das Actions-Kontingent erschöpft ist. Der Runner ist derselbe Dienst-Typ wie der
für `JonasPrade/obs_ai`; dessen Anleitung (`docs/self-hosted-runner.md` dort) gilt für den
Host, diese Datei nur für `raildashboard`.

`release.yml` (Image-Build nach GHCR) und `deploy.yml` laufen weiter auf `ubuntu-latest`:
Sie schreiben nach GHCR bzw. halten den Deploy-Schlüssel, beides gehört nicht auf einen
Runner, der PR-Code ausführt. Außerdem ist Prod `linux/amd64`, ein Image-Build auf dem
arm64-Runner ergäbe die falsche Architektur. Solange das Kontingent aus ist, starten diese
beiden Workflows nicht; das ist eine Billing-Frage, keine Runner-Frage.

## Was im Job anders ist als auf GitHub-Runnern

| Punkt | Wert |
|-------|------|
| `runs-on` | `[self-hosted, linux, ARM64]` |
| Rechte | `contents: read`, kein GHCR-Login, kein Secret |
| Checkout | ohne gespeicherte Zugangsdaten (`persist-credentials: false`) |
| Grenzen | 45 Minuten, ein Lauf je PR (`concurrency`, ältere werden abgebrochen) |
| Layer-Cache | nur der lokale Docker-Cache des Hosts (`CACHE_REF` bleibt leer) |
| Aufräumen | `docker builder prune -f --filter until=168h` am Ende, auch nach Fehler; nie `docker system prune` (der Host gehört auch anderen Projekten) |

## Einrichten für raildashboard (einmalig)

Der Runner `hetzner-dev` ist an `JonasPrade/obs_ai` gebunden. Ein Runner gehört bei einem
persönlichen Account genau einem Repo, deshalb bekommt `raildashboard` eine zweite Instanz
neben der ersten. Als `phips` (hat sudo) auf dem Dev-Server:

1. Token holen: GitHub → `JonasPrade/raildashboard` → Settings → Actions → Runners →
   *New self-hosted runner* → Linux **ARM64**. Nur den Wert hinter `--token` kopieren, er gilt
   eine Stunde.
2. Zweites Verzeichnis anlegen und den Runner entpacken. Download-Befehl und Version stehen
   auf derselben GitHub-Seite; als Benutzer `gh-runner`:

   ```bash
   sudo -u gh-runner mkdir /home/gh-runner/actions-runner-raildashboard
   ```

   Dann in dieses Verzeichnis wechseln (`sudo -u gh-runner -s`, `cd …`) und die Befehle
   `curl` und `tar` von der GitHub-Seite ausführen.
3. Registrieren, mit den gleichen Labels wie der bestehende Runner:

   ```bash
   ./config.sh --unattended --url https://github.com/JonasPrade/raildashboard \
     --token <token> --name hetzner-dev-raildashboard --labels linux,ARM64 --work _work
   ```

4. Als Dienst installieren und starten, als `phips`:

   ```bash
   sudo bash -c 'cd /home/gh-runner/actions-runner-raildashboard && ./svc.sh install gh-runner && ./svc.sh start'
   ```

5. Prüfen: `sudo bash -c 'cd /home/gh-runner/actions-runner-raildashboard && ./svc.sh status'`
   zeigt den Dienst `actions.runner.JonasPrade-raildashboard.hetzner-dev-raildashboard`; unter
   Settings → Actions → Runners steht er auf *Idle*.
6. Einen PR anlegen oder neu starten. Unter „Set up job“ steht der Runner-Name.

## Zu beobachten beim ersten Lauf

- **arm64 statt amd64:** `make test` lief bisher nur auf amd64. Ob alle Basis-Images
  (`imresamu/postgis`, pgRouting-Pakete, GraphHopper-Build) auf arm64 laufen, zeigt erst der
  erste Lauf. Scheitert ein Image an der Architektur, entscheidet ihr: Dockerfile anpassen
  oder die Prüfung auf einen amd64-Host legen.
- **Speicher:** Der Host hat 8 GB, Swap war schon einmal voll. Ein paralleles
  `docker buildx bake` (Maven, Frontend, Backend) kann ihn erschöpfen. Dann in
  `docker-bake.hcl` die Gruppe `pruefung` aufteilen oder `--set *.output` seriell fahren.
- **Docker-Zugriff:** `gh-runner` ist in der Gruppe `docker`, das ist root-gleich auf dem Host.
  Der Dev-Server gilt als Test-Host; liegt dort etwas Schützenswertes, Rootless Docker für
  `gh-runner` einrichten.
- **buildx:** Der Job nutzt den vorhandenen Builder des Hosts und kein `setup-buildx-action`,
  damit der lokale Cache zwischen Läufen erhalten bleibt.

## Zurück auf GitHub-Runner

In `ci.yml` `runs-on` wieder auf `ubuntu-latest` setzen, `docker/setup-buildx-action` und den
GHCR-Login (`packages: write`, `CACHE_REF`) wiederherstellen; der Stand davor steht in der
Git-Historie von `ci.yml`.
