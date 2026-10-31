---
name: widerspruchs-check
description: Find contradictions between a new or changed plan (feature doc, issue, design decision) and the existing plans, principles and code of this repository, then ask the user to resolve each one. Use before writing or changing any docs/features/feature-*.md, when two feature plans touch the same data or UI, or when the user says "Widersprüche prüfen", "check for conflicts", "passt das zu den anderen Plänen", "Konsistenz prüfen".
version: 1.0.0
---

# Widerspruchs-Check

Surfaces contradictions between plans instead of resolving them silently. The output
is a numbered list of conflicts with options and a recommendation; **the user decides**,
then all affected documents are updated in the same change.

Why this exists: two feature plans written in parallel (Infraplan import and GVFG import,
2026-10) made opposite decisions on the same data — whether GVFG Lph/commissioning
feed the planning state, and whether parent projects show sums. Nobody noticed until
the second plan was merged.

## 1. Scope the check

Determine the **subject**: the plan being written or changed (a feature doc, an issue,
or a decision from the conversation). Then collect what it can collide with — use an
Explore subagent so the main context stays clean:

- `docs/architecture.md` → section "Principles (Grundsätze)" — project-wide rules.
- `AGENT.md`, `CLAUDE.md` — working rules.
- Every `docs/features/feature-*.md` that mentions the same **entities** (models,
  tables, sources, project groups), **fields** (e.g. Lph, Inbetriebnahme, costs,
  `project_number`, `parl_befassung_relevant`), **UI places** (menu items, project
  detail sections, admin pages) or **mechanisms** (progress derivation, forecast
  precedence, MCP scope, permissions).
- `docs/models.md` and the actual code for the touched areas (models, `services/progress_*`,
  `mcp/tools`, `core/permissions.py`, router/menu) — a plan can contradict reality,
  not only another plan.
- Open GitHub issues of the same `area:` label.

## 2. Look for these kinds of contradictions

| Kind | Example |
|---|---|
| Same fact, different source of truth | Plan A: Lph only at the GVFG entry. Plan B: Lph from the Infraplan feeds the planning state. |
| Violates a principle | A plan shows no sums for parent projects although "parent projects always aggregate" is a principle. |
| Precedence / trust conflicts | Two plans rank the same sources differently in the forecast. |
| Ownership of a field | Two importers write the same field, or an importer writes a field reserved for manual input. |
| Identity / matching | Two plans use different keys or normalisations for the same external ID. |
| UI collisions | Same route, menu entry or project-detail slot claimed twice; renamed menu in one plan, old name in another. |
| Scope rules | A plan puts imports into MCP although the MCP doc excludes them (or vice versa) without recording the exception. |
| Plan vs. code | The plan assumes a field/table/behaviour that does not exist or works differently. |
| Plan vs. open decision | A plan builds on something another doc still lists as open. |

Report only real conflicts with evidence. Overlaps that fit together (synergies) are
listed separately in one line each — they are useful, not problems.

## 3. Present the conflicts and ask

Answer in German. One round, numbered, every conflict independent of the others
(conflicts that depend on another answer go into a later round).

**Always present the conflicts directly as decision cards** (skill `entscheidungskarten`,
user's standing wish since 2026-10-31): one card per W-point, filed in the shared vault and
shown as clickable choices — never only as a text list. Each card carries the fields below
(question, evidence from both sides, consequence if nothing happens, options,
recommendation with certainty). If the decision-card skill is not available, fall back to
the text format:

```
❗ **W1 – <kurzer Titel>**
- **Plan A** (`docs/features/feature-x.md` → „Abschnitt“): <Zitat oder knappe Wiedergabe>
- **Plan B / Grundsatz / Code** (`pfad` → „Abschnitt“ bzw. `datei.py:zeile`): <…>
- **Folge, wenn nichts passiert:** <was konkret schiefgeht>
- **Optionen:** (a) … (b) … (c) …

➡️ <Empfehlung mit kurzer Begründung>
```

End with: "Synergien" (one line each) and the explicit request to decide each W-point.
If nothing conflicts, say so in one sentence and list what was checked.

**Never** pick an option yourself, edit documents before the user answered, or bury a
conflict in a "notes" section.

## 4. After the user decided

1. Update **every** affected document in the same change — both feature docs, and
   `docs/architecture.md` → "Principles" if the decision is project-wide ("Grundsatz").
   Write the decision with date, replacing the superseded statement (no contradicting
   leftovers).
2. Update the acceptance criteria of affected GitHub issues.
3. Add the decision to the decision table of the subject feature doc, if it has one.
4. Record the decisions on the cards (and in the project note's „Entscheidungen“) as the
   decision-card skill describes, and reference the card IDs in the feature doc.
5. Commit with a message that names the resolved conflicts.
