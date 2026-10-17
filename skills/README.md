# Skills für das Schienendashboard

Dieser Ordner enthält Skills für Agenten, die **mit dem Dashboard** arbeiten — über den
MCP-Server unter `/mcp` (siehe `docs/features/feature-mcp-server.md`). Jeder Unterordner ist
ein Skill mit einer `SKILL.md`.

Abgrenzung: `.claude/skills/` enthält Skills für die Arbeit **am Repository** (Code,
Dokumentation, Widerspruchs-Check). Was hier liegt, braucht kein Repository, sondern einen
API-Key mit den passenden Rechten.

| Skill | Zweck | Rechte |
|---|---|---|
| [`fulda-runde`](fulda-runde/SKILL.md) | Antworten der Bundesregierung zur Fulda-Runde einlesen | `fulda.import` (+ `project.create` für fehlende Teilprojekte) |

Die Anbindung an claude.ai (Hochladen als Skill, MCP-Connector) ist ein Handschritt und
nicht Teil des Repositorys.
