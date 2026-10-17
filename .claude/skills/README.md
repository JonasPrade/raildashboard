# Skills für das Schienendashboard

Alle Skills des Dashboards liegen hier, **ein Ordner je Skill** (`<name>/SKILL.md`),
immer in der aktuellen Fassung. Claude Code lädt sie in diesem Repo automatisch.
Skills für claude.ai (Arbeit über den Schienendashboard-MCP) werden von hier aus von
Hand hochgeladen.

Regeln (siehe `AGENT.md` → „Skills“):

- Ändert sich ein MCP-Tool, Endpunkt, Ablauf oder Grundsatz, den ein Skill beschreibt,
  wird der Skill **im selben Commit** angepasst.
- Jeder neue Skill kommt in die Tabelle unten.
- Keine Kopien an anderer Stelle im Repo.

| Skill | Zweck | Nutzung |
|---|---|---|
| [`audit-auth`](audit-auth/SKILL.md) | Prüft, welche API-Endpunkte Authentifizierung verlangen, und ob das Frontend damit umgeht | Claude Code |
| [`widerspruchs-check`](widerspruchs-check/SKILL.md) | Findet Widersprüche zwischen Plänen, Grundsätzen und Code und legt sie dem Nutzer zur Entscheidung vor | Claude Code |
| [`fulda-runde`](fulda-runde/SKILL.md) | Liest eine Antwort der Bundesregierung zur Fulda-Runde per MCP ein (Dokument, Einträge, Zuordnung, Bestätigung); braucht `fulda.import` | claude.ai (Upload) |
| `infraplan-import` | Führt einen hochgeladenen Infraplan per MCP bis zur Bestätigung und trägt die Kennzahlen ein (entsteht mit #182) | claude.ai (Upload) |

## Nach claude.ai hochladen

1. Den Ordner des Skills (z. B. `infraplan-import/`) als ZIP packen; `SKILL.md` muss
   oben im ZIP liegen.
2. In claude.ai bei den Skills hochladen bzw. die vorhandene Fassung ersetzen.
3. Nach jeder Änderung am Skill im Repo erneut hochladen — die Fassung hier ist die
   maßgebliche.
