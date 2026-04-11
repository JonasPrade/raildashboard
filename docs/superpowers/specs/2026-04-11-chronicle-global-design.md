# Chronicle Design System — Global Rollout

**Date:** 2026-04-11
**Status:** Approved
**Scope:** Full application — all pages, all components

---

## Goal

Make the "Architectural Chronicle" design system the universal standard for the entire application. No page opts in; every page is Chronicle by default. New pages written in the future automatically look correct without any extra wiring.

---

## Architecture

### 1. Token Layer — `:root`

**File:** `apps/frontend/src/components/chronicle/tokens.css`

Move all CSS custom properties from `.chronicle-theme { }` to `:root { }`. Remove the `.chronicle-theme` class entirely. Result: every element in the app has access to `--c-primary`, `--c-secondary`, `--c-surface`, etc. without any wrapper class.

Also remove the `background-color`, `color`, and `font-family` declarations from inside the old class — these move to the global body rule below.

### 2. Global Body Styles

**File:** `apps/frontend/src/app.css`

Add to `app.css`:

```css
body {
    background-color: var(--c-surface);
    color: var(--c-on-surface);
    font-family: var(--font-sans);
}
```

This ensures the warm off-white background and correct text color apply to every page automatically.

### 3. Mantine Theme Alignment

**File:** `apps/frontend/src/theme.ts`

Two changes:
- Fix typo: `"syste-ui"` → `"system-ui"` in `fontFamily`
- Add `defaultRadius: "xs"` — Mantine `xs` = 2px ≈ `--radius-sharp` (0.125rem). All Mantine Cards, Buttons, Modals, Inputs, and Badges become sharp-cornered by default.

The petrol color palette is kept as-is. `petrol[6]` (`#2c8686`) is close to `--c-secondary` (`#006a6a`) and changing it would require touching every `color="petrol"` prop across the codebase.

---

## Page Rollout

### Chronicle component usage rules

| Element type | Chronicle replacement |
|---|---|
| Page/section title | `ChronicleHeadline` (replaces Mantine `Title`) |
| Content container / card | `ChronicleCard` (replaces `Card`, `Paper`) |
| Status label / badge | `ChronicleDataChip` (replaces `Badge`) |
| Primary CTA button | `ChronicleButton` (replaces `Button` for major actions) |
| Section background | `--c-surface-low` (`#f5f3f3`) on containers, `--c-surface-lowest` (`#ffffff`) on cards |

**What stays Mantine:** form inputs (`TextInput`, `Select`, `MultiSelect`, `Checkbox`), data tables (`Table`), review forms, modals content, `Loader`, `Notification`. These inherit sharp corners from `defaultRadius: "xs"` automatically.

**No dividers between sections** — use `--gap-editorial` (1.5rem) spacing instead.

---

### Pages and changes

#### Header (`components/Header.tsx`)
- Background: `--c-primary` (`#041920`) applied to the `AppShell.Header` wrapper
- Title "Schienenprojekte-Dashboard": `ChronicleHeadline as="h1"` with `style={{ color: "var(--c-on-primary)" }}` inside the existing `NavLink`
- Nav link text: `--c-on-primary` (`#ffffff`), 70% opacity when inactive, 100% when active
- Active nav link indicator: 2px `--c-secondary` underline (no background fill)
- "Anmelden" CTA: `ChronicleButton variant="ghost"` with `--c-on-primary` text color override

#### ProjectGroupsPage (`features/projects/ProjectGroupsPage.tsx`)
- Already Chronicle — remove now-redundant `chronicle-theme` class wrapper and `tokens.css` import (tokens are global)

#### MapControls (`features/map/MapControls.tsx`)
- Already Chronicle — remove `tokens.css` import (tokens are global)

#### ProjectDetail (`features/projects/ProjectDetail.tsx`)
- Page title (project name): `ChronicleHeadline as="h1"`
- Section headers (Eigenschaften, Texte, FinVes, VIBs, Changelog): `ChronicleHeadline as="h2"`
- Properties box: `ChronicleCard`
- Remove any `Divider` between sections; use `--gap-editorial` margin

#### FinveOverviewPage (`features/finves/FinveOverviewPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- FinVe cards: `ChronicleCard` (with `accent` for active FinVes)
- Status labels: `ChronicleDataChip`
- Section headers: `ChronicleHeadline as="h2"`

#### UsersPage (`features/admin/UsersPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Content container: `ChronicleCard`
- "Benutzer erstellen" button: `ChronicleButton`

#### ProjectGroupsAdminPage (`features/admin/ProjectGroupsAdminPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Group cards/rows: `ChronicleCard`
- Section headers: `ChronicleHeadline as="h2"`

#### HaushaltsImportPage (`features/haushalt-import/HaushaltsImportPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Upload card: `ChronicleCard`
- Status chips: `ChronicleDataChip`

#### HaushaltsReviewPage (`features/haushalt-import/HaushaltsReviewPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Section headers: `ChronicleHeadline as="h2"`
- Review sections: `ChronicleCard` as outer wrappers; inner review tables stay Mantine `Table`

#### HaushaltsUnmatchedPage (`features/haushalt-import/HaushaltsUnmatchedPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Content wrapper: `ChronicleCard`

#### HaushaltsGuidePage (`features/haushalt-import/HaushaltsGuidePage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Step cards: `ChronicleCard`
- Step labels: `ChronicleDataChip`

#### VibImportPage (`features/vib-import/VibImportPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Upload card: `ChronicleCard`

#### VibReviewPage (`features/vib-import/VibReviewPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Section headers: `ChronicleHeadline as="h2"`
- Entry cards: `ChronicleCard`
- Phase/status labels: `ChronicleDataChip`

#### VibStructurePreviewPage (`features/vib-import/VibStructurePreviewPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Section headers: `ChronicleHeadline as="h2"`
- Entry blocks: `ChronicleCard`

#### DocumentationPage (`features/documentation/DocumentationPage.tsx`)
- Page title: `ChronicleHeadline as="h1"`
- Section headers: `ChronicleHeadline as="h2"`

#### LoginModal (`features/auth/LoginModal.tsx`)
- Modal title: `ChronicleHeadline as="h2"`
- "Anmelden" submit: `ChronicleButton`

---

## Cleanup

- Remove all `import "../../components/chronicle/tokens.css"` lines across the codebase — tokens are global, the import is no longer needed
- Remove all `className="chronicle-theme"` wrapper divs — class no longer exists

---

## What does NOT change

- Mantine form inputs, selects, checkboxes, tables — kept as-is, just inherit sharp corners
- `Loader`, `Notification`, `Drawer`, `Modal` shell — kept as Mantine
- Backend, API, query hooks — untouched
- Routing — untouched

---

## Acceptance Criteria

- [ ] All CSS tokens are defined at `:root`; no `.chronicle-theme` class exists
- [ ] Body has `--c-surface` background and `--c-on-surface` text color globally
- [ ] Mantine `defaultRadius: "xs"` — all Mantine components have sharp corners
- [ ] Every page title uses `ChronicleHeadline`
- [ ] Every major content container uses `ChronicleCard` (no `withBorder` Mantine cards visible)
- [ ] Every status label uses `ChronicleDataChip` (no rounded Mantine badges visible)
- [ ] Header uses Chronicle colors (`--c-primary` background)
- [ ] No `tokens.css` imports or `chronicle-theme` class wrappers remain in the codebase
- [ ] All existing tests pass
