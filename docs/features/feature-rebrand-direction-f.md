# Feature: Rebrand Frontend to Direction F (Bahnhofshalle Tag)

## Goal

Replace the current "Architectural Chronicle" (FAZ-editorial, dark teal, Noto Serif) brand with **Direction F · Bahnhofshalle Tag** — a railway-station-board idiom (Anthracite ink, Gold accent, Prussian-Blue weight, sharp corners, Archivo Narrow + Space Mono + Work Sans). Design source: `docs/DESIGN.md` (rewritten 2026-04-25 from the design-system-f bundle).

**Scope:** Frontend brand layer only. No backend changes. No new business logic.

---

## Constraints & Compatibility

- **Mantine stays.** No framework swap. The brand is delivered through `theme.ts` + `tokens.css` + a small set of new components.
- **Sharp corners are universal.** `defaultRadius: "xs"` is already in `theme.ts` — keep it; bump to `0` where Mantine still rounds.
- **No global dark mode.** Dark surfaces appear only inside the new `Tafel` component family. The rest of the app stays in daylight.
- **Token names continue under `chronicle/`** (path stays for migration safety; semantically these are now the F tokens). New components live under `apps/frontend/src/components/tafel/` to mark them as the dark family.
- **No regressions** in existing 39 files that consume `ChronicleHeadline / ChronicleCard / ChronicleButton / ChronicleDataChip` — those four keep their public props; only their internal styling changes.

---

## File Map

### Touched
```
apps/frontend/src/
├── theme.ts                        # rewrite Mantine theme
├── app.css                         # swap @font-face: drop Noto Serif, add Archivo Narrow + Space Mono
├── components/
│   ├── chronicle/
│   │   ├── tokens.css              # rewrite all custom properties
│   │   ├── ChronicleHeadline.tsx   # Archivo Narrow uppercase, em→Gold
│   │   ├── ChronicleCard.tsx       # sharp corners, hairline border, optional `tone="board"`
│   │   ├── ChronicleButton.tsx     # mono uppercase, primary=Preußenblau, hover=Gold
│   │   └── ChronicleDataChip.tsx   # mono label + LED-dot variant
│   └── tafel/                      # NEW — dark "Tafel" component family
│       ├── MiniBoard.tsx
│       ├── FlapDigit.tsx
│       ├── Ticker.tsx
│       ├── KpiCard.tsx
│       ├── Wordmark.tsx
│       ├── Signet.tsx
│       └── index.ts
└── public/fonts/
    ├── archivo-narrow/             # NEW — self-hosted woff2
    └── space-mono/                 # NEW — self-hosted woff2
```

### Removed
```
public/fonts/noto-serif/            # delete after sweep confirms no remaining `font-serif` use
```

### Untouched
- `dashboard_backend/**` — backend.
- `features/**` — page-level code (consumes Chronicle components, gets new look for free).
- Tests (`*.test.tsx`) — keep prop contracts; update snapshots if any.

---

## Token Migration (`tokens.css`)

| Old token              | Old value | New token       | New value | Note                          |
|------------------------|-----------|-----------------|-----------|-------------------------------|
| `--c-primary`          | `#041920` | `--ink`         | `#0d1013` | Anthracite, slightly warmer.  |
| `--c-secondary`        | `#006a6a` | `--led`         | `#c98a00` | Gold replaces Schienengrün.   |
| `--c-surface`          | `#fbf9f8` | `--bg`          | `#ffffff` | Halle = pure white.           |
| `--c-surface-low`      | `#f5f3f3` | `--bg2`         | `#f3f1ec` | Wartehalle, warm.             |
| `--c-surface-lowest`   | `#ffffff` | `--bg`          | `#ffffff` | Same.                         |
| `--c-surface-high`     | `#e8e5e4` | `--bg3`         | `#e9e6df` | Schiefer.                     |
| `--c-tertiary-container` | `#dff0ef` | _(removed)_   | —         | No teal tint anywhere.        |
| `--c-on-primary`       | `#ffffff` | _(removed)_   | —         | Buttons read direct token.    |
| `--c-on-surface`       | `#041920` | `--ink`         | `#0d1013` | Same role.                    |
| `--font-serif`         | Noto Serif | _(removed)_  | —         | No serif anywhere.            |
| `--font-sans`          | Inter     | `--sans`        | Work Sans | Already loaded.               |
| _(new)_                | —         | `--display`     | Archivo Narrow | Display family.        |
| _(new)_                | —         | `--mono`        | Space Mono | Labels/timestamps.           |
| `--radius-sharp`       | `0.125rem` | _(removed)_  | `0`       | All radii = 0.                |

Add new tokens: `--bg4`, `--rule`, `--ruleHot`, `--ink2`, `--ink3`, `--ledHot`, `--ledDim`, `--info`, `--signal`, `--signalDim`, `--go`, `--goDim`, `--board`, `--board2`, `--boardRule`. Full list in `docs/DESIGN.md` § 2.

A backwards-compat layer keeps `--c-primary`, `--c-secondary`, `--c-surface*` as aliases for the first phase so consuming pages don't break mid-migration. The aliases are removed in Phase 4.

---

## Mantine Theme (`theme.ts`)

```ts
export const theme = createTheme({
  primaryColor: "preussen",
  primaryShade: 8,
  defaultRadius: 0,
  colors: {
    preussen: [/* 10 shades anchored on #0f2347 */],
    gold:     [/* 10 shades anchored on #c98a00 */],
    ink:      [/* 10 grays anchored on #0d1013 */],
  },
  fontFamily: '"Work Sans", -apple-system, BlinkMacSystemFont, sans-serif',
  headings: {
    fontFamily: '"Archivo Narrow", "Oswald", Impact, sans-serif',
    fontWeight: "700",
    sizes: {
      h1: { fontSize: "64px", lineHeight: "0.92" },
      h2: { fontSize: "40px", lineHeight: "0.95" },
      h3: { fontSize: "24px", lineHeight: "1" },
    },
  },
  other: { /* expose F tokens for JS access */ },
});
```

`primaryColor` flips from `petrol` → `preussen`. The Mantine `Button` `color="green"` etc. continue to work; only the brand color shifts.

---

## New Components — `tafel/`

All under `apps/frontend/src/components/tafel/`.

### `<Wordmark size="lg|md|sm" inv?>`
Renders `Schienendashboard` with a Gold dot. Used in header. Replaces the existing text logo.

### `<Signet>`
44×44 Anthracite block with 14×14 Gold inner square. Favicon source.

### `<MiniBoard rows>`
The signature dark live-board (departure-style table). Used for: project status lists, recent changes, route preview. Header LED + label; rows: time | display | gleis | status. Rows accept `state: "go" | "delay" | "info" | "wait"`.

### `<FlapDigit char>` / `<FlapNumber n>`
Section-head numbering (e.g. "01", "02") and inline KPI counters. Sharp 1-px hairline through middle.

### `<Ticker items>`
Amber-background marquee strip. Used at the top of the live status pages to surface incidents / deadlines.

### `<KpiCard label value unit description>`
Preußenblau KPI with left border. Used on the homepage and project summaries.

### Reuse vs. extend
The existing `ChronicleCard` gets a new prop `tone="paper" | "board"`. With `tone="board"` it wraps a `MiniBoard`-style dark surface. Existing call sites stay on `tone="paper"` (default).

---

## Phasing

### Phase 1 — Foundations (no visible regression)
1. Add `Archivo Narrow` and `Space Mono` woff2 to `public/fonts/`. Add `@font-face` blocks to `app.css`.
2. Rewrite `tokens.css` to F tokens **plus alias block** (`--c-primary: var(--ink); --c-secondary: var(--led); ...`).
3. Update `theme.ts` to new families and `preussen` primary.
4. Visual-regression check: existing pages render with new fonts/colors but old structure.

### Phase 2 — Existing Chronicle components
1. `ChronicleHeadline` — switch to Archivo Narrow uppercase; `<em>` → Gold.
2. `ChronicleButton` — Mono uppercase label, Anthracite default, Preußenblau primary, Gold hover.
3. `ChronicleCard` — hairline border (1 px `--rule`), no shadow, padding 24 px; add `tone` prop.
4. `ChronicleDataChip` — Mono uppercase + LED-dot prefix.

### Phase 3 — New Tafel family
1. Build `tafel/` components above with stories/tests.
2. Header: replace text title with `<Wordmark size="md">` + `<Signet>`.
3. Convert one live-data page (recent changes? open assignments?) to `<MiniBoard>` for proof-of-concept.

### Phase 4 — Sweep & cleanup
1. Grep & remove the alias block in `tokens.css`.
2. Remove Noto Serif font files + `@font-face`.
3. Replace any inline Inter font references; "Inter" stays only as a Work Sans fallback if needed.
4. Update `apps/frontend/README.md`, `DocumentationPage.tsx`, `production_setup.md` brand references.
5. Fix the "Abmelden button" contrast issue (roadmap line 89) at the same time — it falls out of the new button rules.
6. Update the in-app `DocumentationPage.tsx`.

### Phase 5 — Visual QA
1. Click through every top-level route. Take screenshots, diff against pre-Phase 1.
2. Re-run the review-checklist.md checks from a clean session.

---

## Acceptance Criteria

- [ ] All four `Chronicle*` components render in F idiom; their public props are unchanged.
- [ ] `tafel/` family exists with `Wordmark`, `Signet`, `MiniBoard`, `FlapDigit`, `Ticker`, `KpiCard`.
- [ ] No reference to `Noto Serif`, `Schienengrün`, `petrol`, or `--c-secondary` remains in shipped frontend code.
- [ ] `make test-frontend` passes; `tsc --noEmit` clean.
- [ ] `apps/frontend/README.md`, `docs/DESIGN.md`, `docs/roadmap.md`, in-app DocumentationPage all reflect Direction F.
- [ ] Manual review-checklist (German) entries added for: header wordmark, headline em-Gold, mini-board appearance, button hover.

---

## Open Questions

1. **Logo finalization.** The bundle reserves a logo slot but ships only a placeholder. Decision needed: keep the wordmark-only approach indefinitely, or commission a mark before Phase 4? *(Suggest: ship Phase 1–4 with wordmark-only; revisit logo separately.)*
2. **Mini-Board for which page first?** Candidates: `/admin/unassigned`, project recent-changes, dashboard home. *(Suggest: `/admin/unassigned` — already a list of "items awaiting action", maps cleanly to a departure board.)*
3. **Scope of Tafel-on-dark.** Only inside the MiniBoard component, or also for the global header band? *(Spec says: Tafel component only. Header stays light. Confirm.)*

---

## Out of Scope

- Backend / API.
- New data, new pages, new business features.
- A finalized SVG logo (handled separately).
- Sharing the brand outside this repo (the design-system-f bundle covers that for the Initiative Deutschlandtakt project).

---

## References

- `docs/DESIGN.md` — full brand spec (Direction F).
- Source bundle (handoff): `/tmp/design-fetch/initiative-deutschlandtakt/project/design-system-f.html` (Direction F prototype, 2068 lines).
- Predecessor: `docs/features/feature-design-system.md` — Chronicle rollout (superseded by this rebrand).
