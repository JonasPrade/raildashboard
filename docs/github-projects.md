# GitHub Projects — Steuerung der raildashboard-Roadmap

Dieses Dokument beschreibt, wie die Roadmap von **raildashboard** über ein
**GitHub-Projects-v2-Board** gesteuert wird und wie **Claude Code** mit diesem
Board arbeitet. Es ist die projektspezifische Ausprägung der generischen Vorlage
`~/code/github-projects-template.md`. Verlinkt aus `CLAUDE.md`.

Diese Datei richtet sich an Claude Code als Leser: sie soll befolgt werden, ohne
dass der User die Regeln pro Sitzung wiederholt.

> **Board:** [github.com/users/JonasPrade/projects/3](https://github.com/users/JonasPrade/projects/3)
> (Projekt #3, „raildashboard Roadmap"). Das Workflow-Feld heißt **`Stage`** —
> der Feldname `Status` ist bei GitHub-User-Projects reserviert und ließ sich
> nicht überschreiben. Die GraphQL-IDs stehen unter
> [„GraphQL-IDs cachen"](#graphql-ids-cachen).

## Grundgedanke — drei Ebenen

| Ebene | Bei raildashboard | Rolle |
|---|---|---|
| **Spezifikation** | `docs/features/feature-<name>.md` + `docs/architecture.md` + `docs/models.md` | „Was wird gebaut und warum" — Datenmodelle, Workflows, Designentscheidungen |
| **Roadmap-Übersicht** | `docs/roadmap.md` | Lese-Ansicht: Versionen + Punkte, referenziert Issue-Codes (nicht -Nummern). **Keine** Steuerungs-Semantik mehr |
| **Steuerung** | GitHub-Projects-Board | „Was als nächstes, in welcher Reihenfolge, in welchem Zustand" |
| **Aufgabenpaket** | GitHub Issues | Konkrete Arbeitspakete mit Akzeptanzkriterien |
| **Roh-Ideen** | `docs/user-backlog.md` | Lose Einwürfe des Users, bevor sie strukturierte Issues werden |

raildashboard hat **kein** einzelnes `konzept.md` — die Spezifikation ist auf die
`docs/features/feature-*.md`-Dateien verteilt. Der `## Konzept-Verweis` eines
Issues zeigt auf das passende Feature-Doc.

## Board-Setup

### Status-Spalten (Single-Select-Feld „Stage")

`User-Backlog → Backlog → Ready → In Progress → Needs User Test → Done`

| Status | Bedeutung |
|---|---|
| **User-Backlog** | Roh-Einträge aus `docs/user-backlog.md`, noch nicht zu Issues verarbeitet |
| **Backlog** | Strukturierte Issues, Abhängigkeiten noch offen |
| **Ready** | Alle Abhängigkeiten erfüllt, kann begonnen werden |
| **In Progress** | In Arbeit |
| **Needs User Test** | Implementierung steht, manuelle Verifikation durch den User nötig |
| **Done** | Abgeschlossen |

### Milestones = Release-Versionen

**Abweichung von der Vorlage:** Milestones sind hier **Release-Versionen**
(`v0.0.5`, `v0.0.6`, …), nicht Implementierungs-Phasen. Mehrstufige Features
(z. B. ProjectProgress Phase 1–6) werden über `Depends on:`-Ketten *innerhalb*
eines Milestones modelliert, nicht über mehrere Milestones.

Punkte ohne Versionszuordnung bekommen **keinen** Milestone und liegen in
`Backlog`, bis der User sie einer Version zuweist.

### Labels — zwei orthogonale Achsen (genau ein Wert je Achse)

**`area:*`** — fachlicher Bereich:

| Label | Bereich |
|---|---|
| `area:projects` | Projekt-CRUD, Detail/Liste/Karte, ProjectGroups |
| `area:routing` | GraphHopper-Routing, Geometrie-Management |
| `area:haushalt-import` | Haushaltsberichte-Import, FinVe-Matching |
| `area:vib-import` | VIB-Import, OCR, AI-Extraktion |
| `area:finve` | FinVe-/Budget-Übersicht und -Logik |
| `area:progress` | ProjectProgress (Fortschrittsanzeige) |
| `area:auth` | Benutzerverwaltung, Rollen, Sessions |
| `area:ops` | Docker, Backup/Restore, CI, Infrastruktur |
| `area:design` | Direction-F-Design-System, UI-Komponenten |
| `area:docs` | Dokumentation |
| `area:tests` | Test-Infrastruktur und -Abdeckung |

**`type:*`** — Art der Arbeit: `type:datamodel`, `type:backend`, `type:ui`,
`type:integration`, `type:infra`, `type:docs`.

**Sonder-Labels:**

- `risk:high` — riskante Komponente, früher technischer Durchstich empfohlen.
- `bot:claude-code` — automatisch von Claude Code angelegt/verfeinert.
- `human-task` — **nur vom User** zu erledigen. Claude Code fasst diese Issues
  nicht an (entspricht der AGENT.md-Regel „Never attempt … human task").

### Issue-Format

- **Titel:** Versions-Präfix + prägnante Beschreibung, z. B.
  `v0.0.5 ProjectProgress – Phase 1: Daten + API`. Punkte ohne Version: ohne
  Präfix.
- **Body:**
  - `## Aufgabe` — was zu tun ist, 1–3 Sätze.
  - `## Akzeptanzkriterien` — überprüfbare Checkliste.
  - `## Konzept-Verweis` — Link auf das Feature-Doc
    (`docs/features/feature-<name>.md#…`).
  - `## Abhängigkeiten` — `Depends on: #<n>` (Issue-Nummern im zweiten Durchlauf
    nachtragen).
- **Labels:** genau ein `area:`, genau ein `type:`, ggf. Sonder-Labels.
- **Milestone:** zugehörige Version (oder keiner).

## User-Backlog — `docs/user-backlog.md`

Gewählte Einwurf-Mechanik: eine **Markdown-Datei** `docs/user-backlog.md` mit
Bulletpoints. Praktisch für mobile/offline gesammelte Ideen.

Claude Code verarbeitet Einträge zu Beginn einer Sitzung oder auf Zuruf
(„arbeite den Backlog ab"):

1. Ältesten / priorisierten Eintrag wählen.
2. Verstehen: Feature-Doc + betroffenen Code + Memory prüfen. Bei Unklarheit
   **kompakte Rückfrage mit konkreten Optionen**, keine Suggestivfragen.
3. In Issue-Format gießen (Aufgabe, Akzeptanzkriterien, Konzept-Verweis,
   Abhängigkeiten, Labels, Milestone).
4. Status auf `Backlog` (Abhängigkeit offen) oder `Ready` (sofort startbar).
5. Label `bot:claude-code` setzen.
6. Bulletpoint aus `docs/user-backlog.md` entfernen, Issue-Link im Commit
   erwähnen.

**Nie** einen Roh-Eintrag löschen, ohne ihn vorher in ein Issue überführt zu
haben. Zu vage zum Klären → zurück an den User, nicht raten.

## Wechselwirkung Markdown ↔ Board

| Ort | Rolle | Lebenszyklus |
|---|---|---|
| `docs/features/feature-*.md`, `docs/architecture.md`, `docs/models.md` | **Spezifikation** | langlebig |
| `docs/roadmap.md` | **Roadmap-Übersicht** (Lese-Ansicht, referenziert Issue-Codes) | bei Phasenabschluss gepflegt |
| `docs/manual-tests-backlog.md` | Aufgeschobene manuelle Tests (heute nicht ausführbar) | wächst/schrumpft mit Integrationspfaden |
| `docs/user-backlog.md` | Roh-Einträge vor Issue-Verarbeitung | flüchtig |
| `CLAUDE.md` | Index + kurze Arbeitsregeln | langlebig |
| GitHub Project | **Steuerung** (Status, Reihenfolge) | hochfrequent |
| GitHub Issues | **Aufgabenbeschreibung** | bis Abschluss |

### Konkrete Regeln

- **Konzept-Verweis im Issue** zeigt auf das Feature-Doc — dort wird „was &
  warum" gepflegt, nicht im Issue-Body (keine Doppelpflege).
- **Konzept-Lücken werden Issues**, keine stillen Entscheidungen. Lässt ein
  Feature-Doc beim Umsetzen eine Frage offen → eigenes Issue (`area:`-passend),
  nicht eigenmächtig entscheiden.
- **Aufgeschobene manuelle Tests** → `docs/manual-tests-backlog.md`. Ist ein
  Akzeptanzkriterium heute nicht verifizierbar (fehlendes Setup, externe
  Quelle), Test-Punkt dort eintragen, Issue darf nach `Done`. Das spätere Issue,
  das den Test ermöglicht, zieht den Eintrag in seine Test-Checkliste hoch.
- `docs/roadmap.md` referenziert Issue-**Codes** (z. B. „ProjectProgress Phase
  1"), nicht Issue-Nummern — bleibt stabil bei Umnummerierung.
- **README/CLAUDE.md ergänzen, nicht duplizieren.**

## Release-Gate (ersetzt `review-checklist.md` / `make release-check`)

**Abweichung von der alten raildashboard-Praxis:** Das frühere Gate
(`docs/review-checklist.md` + `make release-check`) wird durch das Board-Modell
abgelöst:

- **Sofort testbare** manuelle Verifikation → Status `Needs User Test` + konkrete
  Test-Checkliste im Issue-Kommentar (was klicken, welches Ergebnis erwarten,
  wie bei Fehler reagieren).
- **Aufgeschobene** Tests → `docs/manual-tests-backlog.md`.
- **Release-Gate:** Eine Version `v0.0.x` wird erst getaggt, wenn ihr Milestone
  **kein** offenes Issue und **kein** Issue in `Needs User Test` mehr hat.

`make release-check` wird auf diese Board-Abfrage umgebaut oder entfernt (siehe
AGENT.md → Release Gate).

## Workflow pro Issue

1. **Vor dem ersten Commit:** Board-Status auf `In Progress`. Feature-Branch vom
   `master` erstellen, Branchname enthält die Issue-Nummer (z. B.
   `feat/42-project-progress-api`).
2. Implementieren + Tests schreiben, lokal prüfen
   (`cd apps/backend && .venv/bin/python -m pytest`, Frontend `pnpm test`).
3. Größere Issues: Body um Task-Checkliste erweitern; sehr umfangreiche →
   Sub-Issues.
4. **Pull Request** mit `Closes #<Nummer>`. Nach Merge schließt das Issue
   automatisch.
5. **Manuelle Verifikation nötig:** Status `Needs User Test`, Issue **nicht**
   selbst schließen, Test-Checkliste als Issue-Kommentar. Nach User-Bestätigung
   weiter zu 6.
6. **Status `Done`.** Bei direktem Push auf `master` (ohne PR): Issue manuell
   `gh issue close <n> --reason completed`, Commit-SHAs im Kommentar
   referenzieren.
7. **Freigeschaltete Folge-Issues:** Status von `Backlog` auf `Ready`.

### GraphQL-IDs (gecacht)

Auch im Projekt-Memory (`memory/github-project-ids.md`) abgelegt.

| Was | ID |
|---|---|
| Project | `PVT_kwHOAsDKH84BadNl` (Projekt #3) |
| Feld `Stage` | `PVTSSF_lAHOAsDKH84BadNlzhVUt7k` |

Option-IDs (`Stage`):

| Wert | Option-ID |
|---|---|
| User-Backlog | `a7be6dd8` |
| Backlog | `8763de08` |
| Ready | `3f33b13c` |
| In Progress | `4670411c` |
| Needs User Test | `3f1c6199` |
| Done | `90a564a1` |

Item-IDs pro Issue zur Laufzeit über `node(...).items` mit
`fieldValueByName(name:"Stage")`.

Mutation-Template für Stage-Wechsel:

```bash
gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAsDKH84BadNl"
    itemId: "<ITEM_ID>"
    fieldId: "PVTSSF_lAHOAsDKH84BadNlzhVUt7k"
    value: { singleSelectOptionId: "<OPTION_ID>" }
  }) { projectV2Item { id } }
}'
```

## Authentifizierung

`gh` CLI ist als `JonasPrade` eingeloggt; Token-Scopes enthalten bereits
`project` und `repo` — Board, Felder, Labels, Milestones und Issues lassen sich
anlegen.

**Achtung:** Der `workflow`-Scope **fehlt** aktuell. Sobald das CI-Issue
(`.github/workflows/*.yml`) umgesetzt wird, vorher:

```bash
gh auth refresh -h github.com -s workflow
```

sonst wird der Push der Workflow-Datei abgelehnt.

## Kurz-Checkliste für Claude Code

Bei jedem Issue-Kontakt:

- [ ] Issue im Board gefunden, aktuellen Status geprüft.
- [ ] Vor dem ersten Commit Status auf `In Progress`.
- [ ] `## Konzept-Verweis` vorhanden — sonst nachfragen oder als Konzept-Lücke
      festhalten.
- [ ] Aufgeschobene manuelle Tests in `docs/manual-tests-backlog.md`, statt das
      Issue endlos in `Needs User Test` zu parken.
- [ ] Nach Abschluss: `Done` (oder `Needs User Test` mit Test-Checkliste),
      Folge-Issues auf `Ready`.
- [ ] `docs/user-backlog.md` regelmäßig sichten, Einträge in Issues überführen,
      bei Unklarheit rückfragen.
- [ ] `human-task`-Issues nicht selbst bearbeiten.
