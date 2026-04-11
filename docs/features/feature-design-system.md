# Feature: Chronicle Design System Rollout

## Goal

Roll out the "Architectural Chronicle" design system (defined in `docs/DESIGN.md`) to the two highest-visibility pages — **Projects** and **Map** — without changing the look of any other page.

## Approach

**Design Token Layer (Option A):** Introduce a `chronicle/` component folder and a `tokens.css` file with CSS custom properties scoped under a `.chronicle-theme` CSS class. Custom Chronicle components replace Mantine components only on showcase pages. `theme.ts` is untouched. Zero visual regressions on non-showcase pages.

---

## Scope

### In scope
- Self-host Noto Serif font (add `@font-face` to `app.css`)
- `src/components/chronicle/tokens.css` — all design tokens as CSS custom properties
- Four Chronicle components: `ChronicleCard`, `ChronicleButton`, `ChronicleHeadline`, `ChronicleDataChip`
- Apply Chronicle components to **Projects page** and **Map page** only

### Out of scope
- Changes to `theme.ts` or any Mantine configuration
- Any page other than projects and map
- Backend changes

---

## File Structure

```
apps/frontend/src/
├── components/
│   └── chronicle/
│       ├── tokens.css
│       ├── ChronicleCard.tsx
│       ├── ChronicleButton.tsx
│       ├── ChronicleHeadline.tsx
│       ├── ChronicleDataChip.tsx
│       └── index.ts
├── app.css           ← add Noto Serif @font-face
└── features/
    ├── projects/     ← adopt Chronicle components
    └── map/          ← adopt Chronicle components
```

---

## Design Tokens (`tokens.css`)

All properties are scoped to `.chronicle-theme`:

### Colors
| Token | Value | Use |
|---|---|---|
| `--c-primary` | `#041920` | Headlines, nav, ink |
| `--c-secondary` | `#006a6a` | CTAs, focus, accent |
| `--c-surface` | `#fbf9f8` | Page background |
| `--c-surface-low` | `#f5f3f3` | Section grouping |
| `--c-surface-lowest` | `#ffffff` | Cards |
| `--c-surface-high` | `#e8e5e4` | Hover states |
| `--c-tertiary-container` | `#dff0ef` | Chip backgrounds (muted archival) |
| `--c-outline-ghost` | `rgba(194,199,202,0.15)` | Accessibility borders |
| `--c-shadow` | `rgba(27,28,28,0.06)` | Floating shadow |
| `--c-on-primary` | `#ffffff` | Text on primary bg |
| `--c-on-surface` | `#041920` | Body text |

### Typography
| Token | Value |
|---|---|
| `--font-serif` | `'Noto Serif', Georgia, serif` |
| `--font-sans` | `'Inter', system-ui, sans-serif` |
| `--font-size-display` | `2rem` |
| `--font-size-headline` | `1.25rem` |
| `--font-size-label` | `0.75rem` |
| `--letter-spacing-tight` | `-0.02em` |
| `--letter-spacing-data` | `+0.05em` |

### Shape & Depth
| Token | Value |
|---|---|
| `--radius-sharp` | `0.125rem` |
| `--shadow-float` | `0 12px 32px -4px var(--c-shadow)` |
| `--border-accent` | `3px solid var(--c-secondary)` |
| `--gap-editorial` | `1.5rem` |

---

## Components

### `ChronicleCard`
- Background: `--c-surface-lowest`, no border
- Optional `accent` prop: adds `--border-accent` on left side (for active/highlighted projects)
- Shadow only when `float` prop is set: `--shadow-float`
- Padding: 24px

### `ChronicleButton`
- **Primary variant:** background gradient `#041920` → `#1a2e35`, text `--c-on-primary`, border-radius `--radius-sharp`
- **Ghost variant:** no background, text `--c-secondary`, hover adds `--c-surface-high` background

### `ChronicleHeadline`
- Font: `--font-serif`, letter-spacing: `--letter-spacing-tight`
- `as` prop accepts `h1`–`h3` (maps to `--font-size-display`, `--font-size-headline`)

### `ChronicleDataChip`
- Rectangular (`--radius-sharp` or 0px), small padding
- Background: `--c-tertiary-container`
- Font: `--font-sans`, `--font-size-label`, `--letter-spacing-data`

---

## Showcase Page Changes

### Projects page
1. Wrap page root in `<div className="chronicle-theme">`
2. Set page background to `--c-surface`
3. Replace section headers with `ChronicleHeadline`
4. Replace project cards with `ChronicleCard` (add `accent` prop for active projects)
5. Replace status badges with `ChronicleDataChip`
6. Remove all `<Divider>` components; use `--gap-editorial` spacing instead

### Map page
1. Wrap floating control panels/sidebars in `.chronicle-theme`
2. Apply glassmorphism to floating overlays: `background: rgba(251,249,248,0.8); backdrop-filter: blur(20px)`
3. Replace Mantine cards in sidebar/legend with `ChronicleCard`
4. Replace any status chips with `ChronicleDataChip`

---

## Font Setup

Download Noto Serif variable font and place in `apps/frontend/public/fonts/noto-serif/`. Add `@font-face` declaration to `app.css` matching the existing Work Sans / Inter pattern.

---

## Acceptance Criteria

- [x] Projects page renders with Chronicle design; no layout regressions
- [x] Map page floating panels use Chronicle design; map itself is unaffected
- [x] All other pages look identical to before
- [x] Noto Serif loads from self-hosted source (no Google Fonts request)
- [x] No changes to `theme.ts` or any Mantine configuration

---

*See also: `docs/DESIGN.md` for the full design system reference.*
