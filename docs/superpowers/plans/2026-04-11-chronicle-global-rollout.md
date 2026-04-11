# Chronicle Design System — Global Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Chronicle design system the universal default for every page in the app — no per-page opt-in required.

**Architecture:** Move CSS tokens to `:root`, update Mantine `theme.ts` to align with Chronicle values, then apply `ChronicleHeadline`/`ChronicleCard`/`ChronicleDataChip`/`ChronicleButton` to every page. No backend changes. No new components needed.

**Tech Stack:** React, TypeScript, Mantine 7, CSS custom properties, Vitest

---

## File Map

| Action | File | Change |
|---|---|---|
| Modify | `apps/frontend/src/components/chronicle/tokens.css` | `:root` instead of `.chronicle-theme` |
| Modify | `apps/frontend/src/app.css` | Global body styles |
| Modify | `apps/frontend/src/theme.ts` | Fix typo, add `defaultRadius` |
| Modify | `apps/frontend/src/components/Header.tsx` | Chronicle header bar |
| Modify | `apps/frontend/src/features/projects/ProjectGroupsPage.tsx` | Remove wrapper class + import |
| Modify | `apps/frontend/src/features/map/MapControls.tsx` | Remove import |
| Modify | `apps/frontend/src/features/projects/ProjectDetail.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/finves/FinveOverviewPage.tsx` | Chronicle titles + cards + chips |
| Modify | `apps/frontend/src/features/admin/UsersPage.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/admin/ProjectGroupsAdminPage.tsx` | Chronicle titles + cards + chips |
| Modify | `apps/frontend/src/features/haushalt-import/HaushaltsImportPage.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/haushalt-import/HaushaltsReviewPage.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/haushalt-import/HaushaltsUnmatchedPage.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/haushalt-import/HaushaltsGuidePage.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/vib-import/VibImportPage.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/vib-import/VibReviewPage.tsx` | Chronicle titles + cards + chips |
| Modify | `apps/frontend/src/features/vib-import/VibStructurePreviewPage.tsx` | Chronicle titles + cards |
| Modify | `apps/frontend/src/features/auth/LoginModal.tsx` | ChronicleButton submit |
| Modify | `apps/frontend/src/features/documentation/DocumentationPage.tsx` | Chronicle titles |

---

## Task 1: Move tokens to `:root` + global body styles + theme alignment

**Files:**
- Modify: `apps/frontend/src/components/chronicle/tokens.css`
- Modify: `apps/frontend/src/app.css`
- Modify: `apps/frontend/src/theme.ts`

- [ ] **Step 1: Replace `.chronicle-theme` scope with `:root` in `tokens.css`**

Replace the entire file with:

```css
/* Chronicle Design System — global token layer
   Tokens are available on every element. No wrapper class needed. */

:root {
    /* --- Colors --- */
    --c-primary:             #041920;
    --c-secondary:           #006a6a;
    --c-surface:             #fbf9f8;
    --c-surface-low:         #f5f3f3;
    --c-surface-lowest:      #ffffff;
    --c-surface-high:        #e8e5e4;
    --c-tertiary-container:  #dff0ef;
    --c-outline-ghost:       rgba(194, 199, 202, 0.15);
    --c-shadow:              rgba(27, 28, 28, 0.06);
    --c-on-primary:          #ffffff;
    --c-on-surface:          #041920;

    /* --- Typography --- */
    --font-serif: "Noto Serif", Georgia, serif;
    --font-sans:  "Inter", system-ui, -apple-system, sans-serif;

    --font-size-display:  2rem;
    --font-size-headline: 1.25rem;
    --font-size-label:    0.75rem;

    --letter-spacing-tight: -0.02em;
    --letter-spacing-data:   0.05em;

    /* --- Shape & Depth --- */
    --radius-sharp:   0.125rem;
    --shadow-float:   0 12px 32px -4px var(--c-shadow);
    --border-accent:  3px solid var(--c-secondary);
    --gap-editorial:  1.5rem;
}
```

- [ ] **Step 2: Add global body styles to `app.css`**

Add after the existing `/* Self-hosted fonts */` block (append at end of file):

```css
/* Chronicle global base */
body {
    background-color: var(--c-surface);
    color: var(--c-on-surface);
    font-family: var(--font-sans);
    margin: 0;
}
```

- [ ] **Step 3: Update `theme.ts`**

Replace the entire file with:

```ts
import { createTheme } from '@mantine/core';

export const theme = createTheme({
    primaryColor: "petrol",
    primaryShade: 6,
    defaultRadius: "xs",
    colors: {
        petrol: [
            "#e3f6f6", "#c6ecec", "#a0dfdf", "#76d0d1", "#54c2c3",
            "#3aabab", "#2c8686", "#1f6161", "#173f40", "#0f2a2a"
        ]
    },
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif'
});
```

- [ ] **Step 4: Run tests to verify nothing broke**

```bash
cd apps/frontend && pnpm test --run
```

Expected: all existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/components/chronicle/tokens.css apps/frontend/src/app.css apps/frontend/src/theme.ts
git commit -m "feat(design): make Chronicle tokens global — move to :root, align Mantine theme"
```

---

## Task 2: Clean up existing `chronicle-theme` wrappers

**Files:**
- Modify: `apps/frontend/src/features/projects/ProjectGroupsPage.tsx`
- Modify: `apps/frontend/src/features/map/MapControls.tsx`

- [ ] **Step 1: Remove `tokens.css` import and `chronicle-theme` class from `ProjectGroupsPage.tsx`**

Remove this import line:
```tsx
import "../../components/chronicle/tokens.css";
```

Remove the `<div className="chronicle-theme">` wrapper and its closing `</div>` around the `<Container>`. The `<Container size="xl" py="xl">` becomes the top-level element again.

- [ ] **Step 2: Remove `tokens.css` import from `MapControls.tsx`**

Remove this import line:
```tsx
import "../../components/chronicle/tokens.css";
```

- [ ] **Step 3: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/features/projects/ProjectGroupsPage.tsx apps/frontend/src/features/map/MapControls.tsx
git commit -m "chore(design): remove redundant chronicle-theme class wrappers and tokens.css imports"
```

---

## Task 3: Header — Chronicle styling

**Files:**
- Modify: `apps/frontend/src/components/Header.tsx`

- [ ] **Step 1: Update `Header.tsx` imports**

Change the import block to:

```tsx
import React from "react";
import { Burger, Drawer, Group, Stack } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { NavLink } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";
import { ChronicleButton, ChronicleHeadline } from "../components/chronicle";
```

(Removed: `Button`, `Text`, `Title` from Mantine — replaced by Chronicle components)

- [ ] **Step 2: Update `baseStyle` and add nav/header styles**

Replace the `baseStyle` constant with:

```tsx
const navLinkStyle: React.CSSProperties = {
    textDecoration: "none",
    color: "rgba(255,255,255,0.75)",
    padding: "6px 12px",
    borderRadius: 2,
    fontWeight: 500,
    fontSize: "0.9375rem",
    transition: "color 0.15s",
};

const navLinkActiveStyle: React.CSSProperties = {
    ...navLinkStyle,
    color: "#ffffff",
    borderBottom: "2px solid var(--c-secondary)",
};
```

- [ ] **Step 3: Update `navLinks` JSX**

Replace each `NavLink` style prop from `({ isActive }) => ({ ...baseStyle, backgroundColor: ... })` to `({ isActive }) => isActive ? navLinkActiveStyle : navLinkStyle`. Apply to all four NavLinks (Projekte, Haushalt, Haushalts-Import, VIB-Import, Administration).

- [ ] **Step 4: Update `authSection`**

Replace with:

```tsx
const authSection = user ? (
    <Group gap="xs">
        <span style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.875rem" }}>
            {user.username}
        </span>
        <ChronicleButton
            variant="ghost"
            onClick={logout}
            style={{ color: "var(--c-on-primary)", borderColor: "rgba(255,255,255,0.2)", fontSize: "0.875rem", padding: "4px 12px" }}
        >
            Abmelden
        </ChronicleButton>
    </Group>
) : (
    <ChronicleButton
        variant="ghost"
        onClick={() => { closeDrawer(); openLogin(); }}
        style={{ color: "var(--c-on-primary)", borderColor: "rgba(255,255,255,0.2)" }}
    >
        Anmelden
    </ChronicleButton>
);
```

- [ ] **Step 5: Update the outer `Group` wrapper to add dark background and update title**

Replace:
```tsx
<Group justify="space-between" px="md" py="xs">
    <NavLink to="/" className="header-title-link"><Title order={2}>Schienenprojekte-Dashboard</Title></NavLink>
```

With:
```tsx
<Group
    justify="space-between"
    px="md"
    py="xs"
    style={{ backgroundColor: "var(--c-primary)", height: "100%" }}
>
    <NavLink to="/" className="header-title-link">
        <ChronicleHeadline as="h1" style={{ color: "var(--c-on-primary)", fontSize: "1.25rem" }}>
            Schienenprojekte-Dashboard
        </ChronicleHeadline>
    </NavLink>
```

Also update `.header-title-link` hover in `app.css` — keep it as-is, it still works.

- [ ] **Step 6: Update Drawer nav links**

In the Drawer's `navLinks` for mobile, use `navLinkStyle` but with dark text (the Drawer has white background):

Add a separate `drawerNavLinkStyle`:

```tsx
const drawerNavLinkStyle: React.CSSProperties = {
    textDecoration: "none",
    color: "var(--c-on-surface)",
    padding: "6px 12px",
    borderRadius: 2,
    fontWeight: 500,
    fontSize: "0.9375rem",
};

const drawerNavLinkActiveStyle: React.CSSProperties = {
    ...drawerNavLinkStyle,
    color: "var(--c-secondary)",
    borderBottom: "2px solid var(--c-secondary)",
};
```

Create two separate JSX snippets — `desktopNavLinks` (uses light-on-dark styles) and `drawerNavLinks` (uses dark-on-light styles). Use `desktopNavLinks` in the `Group` and `drawerNavLinks` in the `Drawer`.

- [ ] **Step 7: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

- [ ] **Step 8: Commit**

```bash
git add apps/frontend/src/components/Header.tsx apps/frontend/src/app.css
git commit -m "feat(design): apply Chronicle styling to Header — dark bar, sharp nav links"
```

---

## Task 4: ProjectDetail — Chronicle titles and cards

**Files:**
- Modify: `apps/frontend/src/features/projects/ProjectDetail.tsx`

- [ ] **Step 1: Add Chronicle imports to `ProjectDetail.tsx`**

After existing imports, add:
```tsx
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
```

Remove `Title`, `Badge`, `Card` from the Mantine import (keep `Button`, `Alert`, `Container`, `Grid`, `Group`, `Loader`, `Stack`, `Text`, `Collapse`).

- [ ] **Step 2: Replace project title (around line 412)**

Replace:
```tsx
<Title order={2}>{project.name}</Title>
{project.project_number && (
    <Badge color="gray" variant="light">
        {project.project_number}
    </Badge>
)}
```

With:
```tsx
<ChronicleHeadline as="h1">{project.name}</ChronicleHeadline>
{project.project_number && (
    <ChronicleDataChip>{project.project_number}</ChronicleDataChip>
)}
```

- [ ] **Step 3: Replace section `Title` elements**

Find every `<Title order={3}>` or `<Title order={4}>` used as a section header inside the return JSX (e.g. "Projekteigenschaften", "Begründung", "Eigenschaften", "SV-FinVes") and replace with `<ChronicleHeadline as="h2">` or `<ChronicleHeadline as="h3">` respectively.

- [ ] **Step 4: Replace `<Card withBorder ...>` with `<ChronicleCard>`**

Find any `<Card withBorder` or `<Card shadow` in this file and replace the opening tag with `<ChronicleCard>` and the closing `</Card>` with `</ChronicleCard>`.

- [ ] **Step 5: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

- [ ] **Step 6: Commit**

```bash
git add apps/frontend/src/features/projects/ProjectDetail.tsx
git commit -m "feat(design): apply Chronicle to ProjectDetail — titles, cards, chips"
```

---

## Task 5: FinveOverviewPage — Chronicle layout

**Files:**
- Modify: `apps/frontend/src/features/finves/FinveOverviewPage.tsx`

- [ ] **Step 1: Add Chronicle imports**

```tsx
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
```

Remove `Title`, `Badge`, `Card`, `Paper` from Mantine imports (keep `Alert`, `Box`, `Collapse`, `ColorSwatch`, `Container`, `Group`, `Loader`, `SegmentedControl`, `Stack`, `Table`, `Tabs`, `Text`, `TextInput`, `UnstyledButton`).

- [ ] **Step 2: Replace page title**

Find `<Title` used as the page heading (e.g. "Finanzierungsvereinbarungen") and replace with:
```tsx
<ChronicleHeadline as="h1">Finanzierungsvereinbarungen</ChronicleHeadline>
```

- [ ] **Step 3: Replace FinVe cards**

Find `<Card` or `<Paper` elements wrapping FinVe list items and replace with `<ChronicleCard>` / `</ChronicleCard>`.

- [ ] **Step 4: Replace `<Badge>` chips**

Replace `<Badge` elements (type labels, "Sammel-FinVe" tags) with `<ChronicleDataChip>` (remove `color`, `variant` props).

- [ ] **Step 5: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

- [ ] **Step 6: Commit**

```bash
git add apps/frontend/src/features/finves/FinveOverviewPage.tsx
git commit -m "feat(design): apply Chronicle to FinveOverviewPage"
```

---

## Task 6: Admin pages — Chronicle layout

**Files:**
- Modify: `apps/frontend/src/features/admin/UsersPage.tsx`
- Modify: `apps/frontend/src/features/admin/ProjectGroupsAdminPage.tsx`

- [ ] **Step 1: Add Chronicle imports to `UsersPage.tsx`**

```tsx
import { ChronicleHeadline, ChronicleCard, ChronicleButton } from "../../components/chronicle";
```

Remove `Title`, `Card`, `Button` from Mantine imports where replaced (keep `Alert`, `Container`, `Group`, `Loader`, `Select`, `SimpleGrid`, `Stack`, `Table`, `Text`).

- [ ] **Step 2: Replace in `UsersPage.tsx`**

- `<Title` → `<ChronicleHeadline as="h1">Benutzerverwaltung</ChronicleHeadline>`
- `<Card withBorder` → `<ChronicleCard>`
- `</Card>` → `</ChronicleCard>`
- "Benutzer erstellen" `<Button` → `<ChronicleButton onClick={openCreate}>Benutzer erstellen</ChronicleButton>`

- [ ] **Step 3: Add Chronicle imports to `ProjectGroupsAdminPage.tsx`**

```tsx
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
```

Remove `Title`, `Badge`, `Card`, `Divider` from Mantine imports.

- [ ] **Step 4: Replace in `ProjectGroupsAdminPage.tsx`**

- `<Title` → `<ChronicleHeadline as="h1">Projektgruppen</ChronicleHeadline>`
- `<Card` → `<ChronicleCard>`
- `</Card>` → `</ChronicleCard>`
- `<Badge` → `<ChronicleDataChip>` (remove `color`/`variant`)
- `<Divider` → remove; use `style={{ marginTop: "var(--gap-editorial)" }}` on the next element

- [ ] **Step 5: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

- [ ] **Step 6: Commit**

```bash
git add apps/frontend/src/features/admin/UsersPage.tsx apps/frontend/src/features/admin/ProjectGroupsAdminPage.tsx
git commit -m "feat(design): apply Chronicle to admin pages (Users, ProjectGroups)"
```

---

## Task 7: Haushalt import pages — Chronicle layout

**Files:**
- Modify: `apps/frontend/src/features/haushalt-import/HaushaltsImportPage.tsx`
- Modify: `apps/frontend/src/features/haushalt-import/HaushaltsReviewPage.tsx`
- Modify: `apps/frontend/src/features/haushalt-import/HaushaltsUnmatchedPage.tsx`
- Modify: `apps/frontend/src/features/haushalt-import/HaushaltsGuidePage.tsx`

**Pattern for all four files:**

- [ ] **Step 1: Add Chronicle imports to each file**

```tsx
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip, ChronicleButton } from "../../components/chronicle";
```

(Adjust the relative path if the file is in a sub-folder — `HaushaltsGuidePage` may need `"../../../components/chronicle"` — check the existing import depth.)

- [ ] **Step 2: Replace `HaushaltsImportPage.tsx`**

- Remove `Title`, `Paper` from Mantine imports
- `<Title` → `<ChronicleHeadline as="h1">Haushaltsberichte Import</ChronicleHeadline>`
- `<Paper` → `<ChronicleCard>`; `</Paper>` → `</ChronicleCard>`

- [ ] **Step 3: Replace `HaushaltsReviewPage.tsx`**

- Remove `Title`, `Card`, `Paper`, `Badge` from Mantine imports
- `<Title order={2}` or `<Title order={3}` → `<ChronicleHeadline as="h1">` / `<ChronicleHeadline as="h2">` as appropriate
- `<Card` → `<ChronicleCard>`; `</Card>` → `</ChronicleCard>`
- `<Paper` → `<ChronicleCard>`; `</Paper>` → `</ChronicleCard>`
- `<Badge` → `<ChronicleDataChip>` (remove color/variant props)

- [ ] **Step 4: Replace `HaushaltsUnmatchedPage.tsx`**

- Remove `Title`, `Card`, `Paper` from Mantine imports
- `<Title` → `<ChronicleHeadline as="h1">Nicht zugeordnete Einträge</ChronicleHeadline>`
- `<Card` / `<Paper` → `<ChronicleCard>`

- [ ] **Step 5: Replace `HaushaltsGuidePage.tsx`**

- Remove `Title`, `Card`, `Paper`, `Badge` from Mantine imports
- `<Title` → `<ChronicleHeadline as="h1">` / `<ChronicleHeadline as="h2">`
- `<Card` / `<Paper` → `<ChronicleCard>`
- `<Badge` → `<ChronicleDataChip>`

- [ ] **Step 6: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/features/haushalt-import/
git commit -m "feat(design): apply Chronicle to all Haushalt import pages"
```

---

## Task 8: VIB import pages — Chronicle layout

**Files:**
- Modify: `apps/frontend/src/features/vib-import/VibImportPage.tsx`
- Modify: `apps/frontend/src/features/vib-import/VibReviewPage.tsx`
- Modify: `apps/frontend/src/features/vib-import/VibStructurePreviewPage.tsx`

**Pattern for all three files:**

- [ ] **Step 1: Add Chronicle imports**

```tsx
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
```

- [ ] **Step 2: Replace `VibImportPage.tsx`**

- Remove `Title`, `Paper` from Mantine imports
- `<Title` → `<ChronicleHeadline as="h1">VIB-Import</ChronicleHeadline>`
- `<Paper` → `<ChronicleCard>`; `</Paper>` → `</ChronicleCard>`

- [ ] **Step 3: Replace `VibReviewPage.tsx`**

- Remove `Title`, `Card`, `Paper`, `Badge` from Mantine imports
- `<Title order={2}` → `<ChronicleHeadline as="h1">`; `<Title order={3}` → `<ChronicleHeadline as="h2">`
- `<Card` / `<Paper` → `<ChronicleCard>`
- `<Badge` → `<ChronicleDataChip>` (remove color/variant)

- [ ] **Step 4: Replace `VibStructurePreviewPage.tsx`**

- Remove `Title`, `Card`, `Paper`, `Badge` from Mantine imports
- `<Title` → `<ChronicleHeadline as="h1">` / `<ChronicleHeadline as="h2">`
- `<Card` / `<Paper` → `<ChronicleCard>`
- `<Badge` → `<ChronicleDataChip>`

- [ ] **Step 5: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

- [ ] **Step 6: Commit**

```bash
git add apps/frontend/src/features/vib-import/
git commit -m "feat(design): apply Chronicle to all VIB import pages"
```

---

## Task 9: LoginModal + DocumentationPage

**Files:**
- Modify: `apps/frontend/src/features/auth/LoginModal.tsx`
- Modify: `apps/frontend/src/features/documentation/DocumentationPage.tsx`

- [ ] **Step 1: Update `LoginModal.tsx`**

Add import:
```tsx
import { ChronicleButton } from "../../components/chronicle";
```

Remove `Button` from Mantine imports (keep `Alert`, `Modal`, `PasswordInput`, `Stack`, `TextInput`).

Replace the submit button:
```tsx
// Before:
<Button type="submit" loading={loading} fullWidth mt="xs">
    Anmelden
</Button>

// After:
<ChronicleButton type="submit" disabled={loading} style={{ width: "100%", marginTop: "0.5rem" }}>
    {loading ? "…" : "Anmelden"}
</ChronicleButton>
```

- [ ] **Step 2: Update `DocumentationPage.tsx`**

Read the file first, then add:
```tsx
import { ChronicleHeadline } from "../../components/chronicle";
```

Replace any `<Title` with `<ChronicleHeadline as="h1">` / `<ChronicleHeadline as="h2">`. Remove `Title` from Mantine imports.

- [ ] **Step 3: Run tests**

```bash
cd apps/frontend && pnpm test --run
```

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/features/auth/LoginModal.tsx apps/frontend/src/features/documentation/DocumentationPage.tsx
git commit -m "feat(design): apply Chronicle to LoginModal and DocumentationPage"
```

---

## Task 10: Final verification + roadmap update

- [ ] **Step 1: Search for any remaining `tokens.css` imports**

```bash
grep -r "chronicle/tokens.css" apps/frontend/src/
```

Expected: no output. If any found, remove those import lines.

- [ ] **Step 2: Search for any remaining `chronicle-theme` class usage**

```bash
grep -r "chronicle-theme" apps/frontend/src/
```

Expected: no output (only the now-removed `.chronicle-theme` CSS class in tokens.css was the source — that's gone). If found in JSX, remove the `className`.

- [ ] **Step 3: Run full test suite**

```bash
cd apps/frontend && pnpm test --run
```

Expected: all tests pass.

- [ ] **Step 4: Update roadmap**

In `docs/roadmap.md`, mark:
```
- [x] integrate the new design described in `docs/DESIGN.md`
```

Move it to the Finished > UI/UX section with description:
```
- [x] **Chronicle design system — full rollout** — All pages use ChronicleHeadline/ChronicleCard/ChronicleDataChip/ChronicleButton; tokens at `:root`; Mantine `defaultRadius: "xs"`; dark header bar
```

- [ ] **Step 5: Final commit**

```bash
git add docs/roadmap.md
git commit -m "docs: mark Chronicle full rollout complete"
```

- [ ] **Step 6: Push**

```bash
git push origin master
```
