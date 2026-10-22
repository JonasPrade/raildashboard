# Skills für das Schienendashboard

Alle Skills des Dashboards liegen hier, **ein Ordner je Skill** (`<name>/SKILL.md`),
immer in der aktuellen Fassung. Claude Code lädt sie in diesem Repo automatisch.
Skills für die Arbeit über den Schienendashboard-MCP liefert **der MCP-Server selbst aus**
(`list_skills`, `get_skill`) — immer in der Fassung des deployten Images, passend zu den
laufenden Tools. Details: `docs/features/feature-mcp-server.md` → „Skills über MCP“.

Regeln (siehe `AGENT.md` → „Skills“):

- Ändert sich ein MCP-Tool, Endpunkt, Ablauf oder Grundsatz, den ein Skill beschreibt,
  wird der Skill **im selben Commit** angepasst.
- Jeder neue Skill kommt in die Tabelle unten.
- Keine Kopien an anderer Stelle im Repo.

| Skill | Zweck | Nutzung |
|---|---|---|
| [`audit-auth`](audit-auth/SKILL.md) | Prüft, welche API-Endpunkte Authentifizierung verlangen, und ob das Frontend damit umgeht | Claude Code |
| [`widerspruchs-check`](widerspruchs-check/SKILL.md) | Findet Widersprüche zwischen Plänen, Grundsätzen und Code und legt sie dem Nutzer zur Entscheidung vor | Claude Code |
| [`schienendashboard`](schienendashboard/SKILL.md) | Einstieg: verweist auf `list_skills`/`get_skill` des MCP-Servers | claude.ai (einmaliger Upload) |
| [`fulda-runde`](fulda-runde/SKILL.md) | Liest eine Antwort der Bundesregierung zur Fulda-Runde per MCP ein (Dokument, Einträge, Zuordnung, Bestätigung); braucht `fulda.import` | MCP (`mcp: true`) |
| [`vib-import`](vib-import/SKILL.md) | Liest einen Verkehrsinvestitionsbericht (Abschnitt Schienenwege) per MCP ein oder prüft einen vorhandenen Jahrgang (Bericht, Vorhaben, PFA-Tabelle, Zuordnung mit Begründung, Bestätigung); braucht `vib.import` | MCP (`mcp: true`) |
| [`infraplan-import`](infraplan-import/SKILL.md) | Führt einen hochgeladenen Infraplan per MCP bis zur Bestätigung (Vorschläge, gesammelte begründete Zuordnung, Teilprojekte, Arbeitsteilung mit Subagenten) und trägt die Kennzahlen aus dem Seitentext ungeprüft ein; braucht `infraplan.import` | MCP (`mcp: true`) |
| [`gvfg-nacharbeit`](gvfg-nacharbeit/SKILL.md) | Arbeitet eine im Frontend importierte GVFG-Ausgabe per MCP nach (offene Vorhaben zuordnen, Dubletten zusammenführen, Import-Entwürfe prüfen, Zuordnung über alle Ausgaben angleichen); braucht `assignment.manage`, für Bereinigung `project.merge`/`project.create`/`project.edit` | MCP (`mcp: true`) |

## Einen Skill über den MCP ausliefern

Im Frontmatter markieren:

```yaml
---
name: infraplan-import
description: Was der Skill tut und wann er greift (eine Zeile).
metadata:
  mcp: true
---
```

Das Frontmatter bleibt einfach: `key: wert` je Zeile, unter `metadata:` eine eingerückte
Ebene, keine mehrzeiligen Werte. `make test` prüft, dass jeder Skill hier gelesen werden
kann (Name = Ordnername, Beschreibung vorhanden). Begleitdateien im Skill-Ordner (z. B.
`references/…`) liefert `get_skill(name, file=…)` mit aus. Wirksam wird eine Änderung mit
dem nächsten Deploy.

## Einstieg in claude.ai (einmalig)

Nur `schienendashboard/` wird hochgeladen; er ändert sich praktisch nie.

1. Den Ordner `schienendashboard/` als ZIP packen; `SKILL.md` muss im ZIP oben im
   Ordner liegen.
2. In claude.ai unter *Customize → Skills* hochladen.
3. Den Schienendashboard-MCP als Connector verbinden. Alle weiteren Skills holt Claude
   von dort.

claude.ai akzeptiert im Frontmatter nur `name`, `description`, `license`, `compatibility`,
`metadata` und `allowed-tools` — für den Einstiegs-Skill also kein `version`.
