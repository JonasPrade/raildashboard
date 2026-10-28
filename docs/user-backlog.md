# User-Backlog

Roh-Ideen, Bugs und Wünsche — **bevor** sie strukturierte Issues werden. Einfach
als Bulletpoint anhängen (Titel reicht, ein, zwei Sätze Kontext schaden nicht).

Claude Code verarbeitet diese Einträge zu Beginn einer Sitzung oder auf Zuruf
(„arbeite den Backlog ab") zu vollwertigen GitHub-Issues und entfernt den
jeweiligen Bulletpoint dann hier. Details: `docs/github-projects.md` →
Abschnitt „User-Backlog".

Nichts wird gelöscht, ohne vorher in ein Issue überführt zu sein.

---

<!-- Neue Einträge hierunter, einer pro Bulletpoint: -->

- **VIB-PFA: Geometrie als Vorschlagssignal** (vorgemerkt 2026-10-23, `feature-vib-import.md` → Phase 8, P4): Endpunkte der PFA-Örtlichkeit („A–B“) auf Betriebsstellen abbilden (eingegrenzt auf die Bounding Box des Oberprojekts) und prüfen, ob beide nahe an der Linie eines Teilprojekts liegen — hilft, wo Teilprojekte weder Abschnittsnummer noch Ortsnamen tragen.
- **Bauportal-Infos fehlen auf der Projektseite** (vorgemerkt 2026-10-28, `feature-project-progress.md` → „DB-Bauportal (#47)“): Zu einem bestätigt zugeordneten Bauportal-Eintrag zeigt die Projektseite weder den Link auf die Bauportal-Seite noch die dort gefundenen Angaben. In `bauportal_status` liegen `url`, `shorttitle`, `status_raw` (`icon_title`), `projecttime_raw` und `raw_json` vor; sichtbar wird davon nur die abgeleitete BAUPORTAL-Beobachtung im Fortschritt (Notiz „DB-Bauportal: <projecttime>“, ohne URL). Gewünscht: eigene Karte „DB-Bauportal“ auf der Projektdetailseite mit Link + Bauportal-Angaben (Status, Bauzeit, ggf. weitere Felder aus `raw_json`); die Karte erscheint nur, wenn ein Bauportal-Link vorhanden ist.
