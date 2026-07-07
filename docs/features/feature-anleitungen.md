# Feature: Anleitungen (admin guides hub)

Living note for the "Anleitungen" area — step-by-step guides for
database-maintenance workflows, reachable from the admin overview at
`/admin/anleitungen`. Extend this file whenever a new guide (usually a new
data source) is added.

## Architecture

Guides are **data-driven**: each guide page defines a `GuideDef` (markdown
strings + structure) and renders it through a shared renderer. Texts are
**editable in-app** by users with the `guides.edit` capability; edits are
stored server-side as per-section overrides and win over the bundled defaults.

- **Types / content contract**: `apps/frontend/src/features/guides/guideContent.ts`
  (`GuideDef`, `GuideSection`; documents the supported markdown syntax
  incl. `> [!yellow] Titel` alert blocks and `` `Chip` `` inline chips).
- **Renderer**: `features/guides/GuideRenderer.tsx` — standard skeleton
  (back link, headline + chip, editable intro, green "Voraussetzungen" alert,
  numbered steps accordion, contained troubleshooting accordion).
- **Markdown rendering**: `features/guides/GuideMarkdown.tsx` (react-markdown
  + remark-gfm; internal links → router links, inline code → ChronicleDataChip,
  blockquotes → Mantine Alerts).
- **Editing**: `features/guides/GuideSectionBody.tsx` — per-section
  "Bearbeiten" (markdown textarea), "Speichern", "Auf Standardtext
  zurücksetzen", "angepasst" badge. Gated by `can("guides.edit")`.
- **Example views**: `features/guides/guideExamples.tsx` — static,
  non-interactive replicas of the real screens (framed by
  `GuideExampleView.tsx`, "Beispielansicht"). Referenced from `GuideDef`
  sections via `exampleKey`; they are code, not editable.
- **Hub page**: `features/guides/AnleitungenPage.tsx` — `FOUNDATIONS` and
  `WORKFLOWS` card arrays (`{ to, title, description }`).
- **Routing**: `apps/frontend/src/router.tsx` — `lazyWithRetry` import +
  route `admin/anleitungen/<slug>` in a `<Suspense>` wrapper.

### Backend (override storage)

- Model `guide_section_override` (`models/guides.py`), unique per
  `(guide_slug, section_key)`; migration `20260707001`.
- Endpoints `GET/PUT/DELETE /api/v1/guides/{slug}/overrides[/{section_key}]`
  (`endpoints/guides.py`): reading public, writing requires the
  `guides.edit` capability (`core/permissions.py`, group "Inhalte" —
  admins implicitly, grantable to other roles via the roles admin UI).
- Frontend hooks in `shared/api/queries.ts`
  (`useGuideOverrides` / `useSaveGuideOverride` / `useDeleteGuideOverride`).

**Stability rule:** guide `slug`s and section `key`s are the identifiers the
DB overrides hang on — never rename them once shipped, or existing overrides
silently detach.

## Content rules

- Derive content from the **actual feature implementation** (button labels,
  field names, status chips, what confirming does) — never guess. Read the
  feature's pages under `features/<name>/`, the backend task/endpoint, and
  `shared/api/queries.ts` before writing.
- **Don't repeat — link.** Shared concepts live in one guide and are linked
  from the others (e.g. derivation logic → projektfortschritt guide, geometry
  editor → geometrie guide, drafts/wizard → projekt-anlegen guide).
- Every observation-producing source must be placed into the
  project-progress model (source → observation) and cross-link
  `/admin/anleitungen/projektfortschritt`.
- UI strings German; code/comments English.

## How to add a new guide

1. Create `features/guides/<Name>GuidePage.tsx`: a `GuideDef` + default export
   `<GuideRenderer def={DEF} />` (copy an existing guide as template).
2. Optionally add example views to `guideExamples.tsx` and reference them via
   `exampleKey`.
3. In `router.tsx`: add the `lazyWithRetry` import + route
   `admin/anleitungen/<slug>`.
4. In `AnleitungenPage.tsx`: add a card to `WORKFLOWS` (or `FOUNDATIONS`).
5. Add mutual cross-references (markdown links to `/admin/anleitungen/...`).

## Gates (definition of done)

- `cd apps/backend && .venv/bin/python -m pytest` → green (guides API tests)
- `cd apps/frontend && npx tsc --noEmit` → exit 0
- `cd apps/frontend && npm run lint` → 0 errors (warnings ok)
- `cd apps/frontend && npm run build` → exit 0
- New route loads; card appears on `/admin/anleitungen`;
  "← Alle Anleitungen" navigates back.
- Content matches the real UI (field/button names are accurate).

## Existing guides

| Route | Slug | Topic |
|---|---|---|
| `/admin/anleitungen/projektfortschritt` | `projektfortschritt` | Foundations: how the derived planning state works |
| `/admin/anleitungen/projekt-anlegen` | `projekt-anlegen` | Creating projects via the wizard (drafts, subprojects) |
| `/admin/anleitungen/geometrie` | `geometrie` | Creating geometries (routing, points, GeoJSON, drawing) |
| `/admin/haushalt-import/guide` | `haushalt` | Federal budget (VWIB Teil B) import |
| `/admin/anleitungen/fulda` | `fulda` | Fulda-Runde (Kleine Anfrage) import |
| `/admin/anleitungen/bauportal` | `bauportal` | DB Bauportal API import |
| `/admin/anleitungen/vib` | `vib` | VIB report import (OCR → structure preview → review) |
| `/admin/anleitungen/medien` | `medien` | Media/press articles via AI extraction |

Future guides become useful whenever a new data source is added.
