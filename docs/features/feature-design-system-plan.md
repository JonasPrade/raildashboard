# Chronicle Design System Rollout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce the "Architectural Chronicle" design system on the Projects and Map pages without touching any other page or Mantine config.

**Architecture:** A `.chronicle-theme` CSS class scopes all design tokens. Custom components (`ChronicleCard`, `ChronicleButton`, `ChronicleHeadline`, `ChronicleDataChip`) live in `src/components/chronicle/` and only activate under that class. `theme.ts` is untouched.

**Tech Stack:** React, TypeScript, Vitest + @testing-library/react (jsdom), CSS custom properties, Mantine (kept intact)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `apps/frontend/public/fonts/noto-serif/NotoSerif-VariableFont_wdth,wght.ttf` | Self-hosted Noto Serif font file |
| Modify | `apps/frontend/src/app.css` | Add `@font-face` for Noto Serif |
| Create | `apps/frontend/src/components/chronicle/tokens.css` | All CSS custom properties scoped to `.chronicle-theme` |
| Create | `apps/frontend/src/components/chronicle/ChronicleHeadline.tsx` | Serif headline component |
| Create | `apps/frontend/src/components/chronicle/ChronicleHeadline.test.tsx` | Vitest tests for ChronicleHeadline |
| Create | `apps/frontend/src/components/chronicle/ChronicleDataChip.tsx` | Rectangular status chip |
| Create | `apps/frontend/src/components/chronicle/ChronicleDataChip.test.tsx` | Vitest tests for ChronicleDataChip |
| Create | `apps/frontend/src/components/chronicle/ChronicleCard.tsx` | No-border tonal card |
| Create | `apps/frontend/src/components/chronicle/ChronicleCard.test.tsx` | Vitest tests for ChronicleCard |
| Create | `apps/frontend/src/components/chronicle/ChronicleButton.tsx` | Sharp-corner gradient/ghost button |
| Create | `apps/frontend/src/components/chronicle/ChronicleButton.test.tsx` | Vitest tests for ChronicleButton |
| Create | `apps/frontend/src/components/chronicle/index.ts` | Barrel export |
| Modify | `apps/frontend/src/features/projects/ProjectGroupsPage.tsx` | Apply Chronicle to Projects page + ProjectCard |
| Modify | `apps/frontend/src/features/map/MapControls.tsx` | Apply Chronicle to floating map controls panel |

---

## Task 1: Download and add Noto Serif font

**Files:**
- Create: `apps/frontend/public/fonts/noto-serif/NotoSerif-VariableFont_wdth,wght.ttf`
- Modify: `apps/frontend/src/app.css`

- [ ] **Step 1: Download Noto Serif variable font**

```bash
mkdir -p apps/frontend/public/fonts/noto-serif
curl -L "https://fonts.gstatic.com/s/notoserif/v25/ga6Iaw1J5X9T9RW6j9bNTFAcaRi_bMQ.ttf" \
  -o "apps/frontend/public/fonts/noto-serif/NotoSerif-VariableFont.ttf"
```

If the curl fails (font URL may rotate), download "Noto Serif" from https://fonts.google.com/noto/specimen/Noto+Serif, unzip, and place the `.ttf` file at the path above.

- [ ] **Step 2: Verify file exists**

```bash
ls -lh apps/frontend/public/fonts/noto-serif/
```
Expected: one `.ttf` file, ~1-2 MB.

- [ ] **Step 3: Add `@font-face` to `app.css`**

In `apps/frontend/src/app.css`, append at the end:

```css
/* Noto Serif — self-hosted for Chronicle design system */
@font-face {
    font-family: "Noto Serif";
    src: url("/fonts/noto-serif/NotoSerif-VariableFont.ttf") format("truetype");
    font-weight: 100 900;
    font-style: normal;
    font-display: swap;
}
```

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/public/fonts/noto-serif/ apps/frontend/src/app.css
git commit -m "feat(design): self-host Noto Serif variable font"
```

---

## Task 2: Create design token CSS

**Files:**
- Create: `apps/frontend/src/components/chronicle/tokens.css`

- [ ] **Step 1: Create the file**

```css
/* Chronicle Design System — token layer
   All properties are scoped to .chronicle-theme.
   Pages without this class are completely unaffected. */

.chronicle-theme {
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

    /* Apply surface color to the page root */
    background-color: var(--c-surface);
    color: var(--c-on-surface);
    font-family: var(--font-sans);
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/components/chronicle/tokens.css
git commit -m "feat(design): add Chronicle design tokens CSS"
```

---

## Task 3: ChronicleHeadline component

**Files:**
- Create: `apps/frontend/src/components/chronicle/ChronicleHeadline.tsx`
- Create: `apps/frontend/src/components/chronicle/ChronicleHeadline.test.tsx`

- [ ] **Step 1: Write the failing test**

`apps/frontend/src/components/chronicle/ChronicleHeadline.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ChronicleHeadline from "./ChronicleHeadline";

describe("ChronicleHeadline", () => {
    it("renders children as h1 by default", () => {
        render(<ChronicleHeadline>Haupttitel</ChronicleHeadline>);
        expect(screen.getByRole("heading", { level: 1, name: "Haupttitel" })).toBeInTheDocument();
    });

    it("renders as h2 when as='h2'", () => {
        render(<ChronicleHeadline as="h2">Abschnitt</ChronicleHeadline>);
        expect(screen.getByRole("heading", { level: 2, name: "Abschnitt" })).toBeInTheDocument();
    });

    it("renders as h3 when as='h3'", () => {
        render(<ChronicleHeadline as="h3">Unterabschnitt</ChronicleHeadline>);
        expect(screen.getByRole("heading", { level: 3, name: "Unterabschnitt" })).toBeInTheDocument();
    });

    it("applies extra className when provided", () => {
        const { container } = render(
            <ChronicleHeadline className="my-class">Titel</ChronicleHeadline>
        );
        expect(container.firstChild).toHaveClass("my-class");
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleHeadline.test.tsx
```
Expected: FAIL — "Cannot find module './ChronicleHeadline'"

- [ ] **Step 3: Implement ChronicleHeadline**

`apps/frontend/src/components/chronicle/ChronicleHeadline.tsx`:

```tsx
import type { ReactNode } from "react";

type HeadingLevel = "h1" | "h2" | "h3";

type Props = {
    as?: HeadingLevel;
    children: ReactNode;
    className?: string;
    style?: React.CSSProperties;
};

const sizeMap: Record<HeadingLevel, string> = {
    h1: "var(--font-size-display)",
    h2: "var(--font-size-headline)",
    h3: "var(--font-size-headline)",
};

export default function ChronicleHeadline({ as: Tag = "h1", children, className, style }: Props) {
    return (
        <Tag
            className={className}
            style={{
                fontFamily: "var(--font-serif)",
                fontSize: sizeMap[Tag],
                letterSpacing: "var(--letter-spacing-tight)",
                color: "var(--c-primary)",
                fontWeight: Tag === "h1" ? 700 : 600,
                margin: 0,
                ...style,
            }}
        >
            {children}
        </Tag>
    );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleHeadline.test.tsx
```
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/components/chronicle/ChronicleHeadline.tsx \
        apps/frontend/src/components/chronicle/ChronicleHeadline.test.tsx
git commit -m "feat(design): add ChronicleHeadline component"
```

---

## Task 4: ChronicleDataChip component

**Files:**
- Create: `apps/frontend/src/components/chronicle/ChronicleDataChip.tsx`
- Create: `apps/frontend/src/components/chronicle/ChronicleDataChip.test.tsx`

- [ ] **Step 1: Write the failing test**

`apps/frontend/src/components/chronicle/ChronicleDataChip.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ChronicleDataChip from "./ChronicleDataChip";

describe("ChronicleDataChip", () => {
    it("renders label text", () => {
        render(<ChronicleDataChip>Elektrifizierung</ChronicleDataChip>);
        expect(screen.getByText("Elektrifizierung")).toBeInTheDocument();
    });

    it("applies extra className", () => {
        const { container } = render(
            <ChronicleDataChip className="extra">Label</ChronicleDataChip>
        );
        expect(container.firstChild).toHaveClass("extra");
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleDataChip.test.tsx
```
Expected: FAIL — "Cannot find module './ChronicleDataChip'"

- [ ] **Step 3: Implement ChronicleDataChip**

`apps/frontend/src/components/chronicle/ChronicleDataChip.tsx`:

```tsx
import type { ReactNode } from "react";

type Props = {
    children: ReactNode;
    className?: string;
    style?: React.CSSProperties;
};

export default function ChronicleDataChip({ children, className, style }: Props) {
    return (
        <span
            className={className}
            style={{
                display: "inline-block",
                padding: "2px 8px",
                backgroundColor: "var(--c-tertiary-container)",
                color: "var(--c-on-surface)",
                fontFamily: "var(--font-sans)",
                fontSize: "var(--font-size-label)",
                letterSpacing: "var(--letter-spacing-data)",
                borderRadius: "var(--radius-sharp)",
                fontWeight: 500,
                lineHeight: "1.6",
                ...style,
            }}
        >
            {children}
        </span>
    );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleDataChip.test.tsx
```
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/components/chronicle/ChronicleDataChip.tsx \
        apps/frontend/src/components/chronicle/ChronicleDataChip.test.tsx
git commit -m "feat(design): add ChronicleDataChip component"
```

---

## Task 5: ChronicleCard component

**Files:**
- Create: `apps/frontend/src/components/chronicle/ChronicleCard.tsx`
- Create: `apps/frontend/src/components/chronicle/ChronicleCard.test.tsx`

- [ ] **Step 1: Write the failing test**

`apps/frontend/src/components/chronicle/ChronicleCard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ChronicleCard from "./ChronicleCard";

describe("ChronicleCard", () => {
    it("renders children", () => {
        render(<ChronicleCard>Inhalt</ChronicleCard>);
        expect(screen.getByText("Inhalt")).toBeInTheDocument();
    });

    it("renders as a div by default", () => {
        const { container } = render(<ChronicleCard>Karte</ChronicleCard>);
        expect(container.firstChild?.nodeName).toBe("DIV");
    });

    it("applies accent style when accent prop is true", () => {
        const { container } = render(<ChronicleCard accent>Aktiv</ChronicleCard>);
        const el = container.firstChild as HTMLElement;
        expect(el.style.borderLeft).toBeTruthy();
    });

    it("applies float shadow when float prop is true", () => {
        const { container } = render(<ChronicleCard float>Float</ChronicleCard>);
        const el = container.firstChild as HTMLElement;
        expect(el.style.boxShadow).toBeTruthy();
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleCard.test.tsx
```
Expected: FAIL — "Cannot find module './ChronicleCard'"

- [ ] **Step 3: Implement ChronicleCard**

`apps/frontend/src/components/chronicle/ChronicleCard.tsx`:

```tsx
import type { ReactNode, CSSProperties } from "react";

type Props = {
    children: ReactNode;
    accent?: boolean;
    float?: boolean;
    className?: string;
    style?: CSSProperties;
};

const baseStyle: CSSProperties = {
    backgroundColor: "var(--c-surface-lowest)",
    borderRadius: "var(--radius-sharp)",
    padding: "24px",
    color: "inherit",
    display: "block",
};

export default function ChronicleCard({ children, accent, float, className, style }: Props) {
    const combined: CSSProperties = {
        ...baseStyle,
        ...(accent ? { borderLeft: "var(--border-accent)" } : {}),
        ...(float ? { boxShadow: "var(--shadow-float)" } : {}),
        ...style,
    };

    return (
        <div className={className} style={combined}>
            {children}
        </div>
    );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleCard.test.tsx
```
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/components/chronicle/ChronicleCard.tsx \
        apps/frontend/src/components/chronicle/ChronicleCard.test.tsx
git commit -m "feat(design): add ChronicleCard component"
```

---

## Task 6: ChronicleButton component

**Files:**
- Create: `apps/frontend/src/components/chronicle/ChronicleButton.tsx`
- Create: `apps/frontend/src/components/chronicle/ChronicleButton.test.tsx`

- [ ] **Step 1: Write the failing test**

`apps/frontend/src/components/chronicle/ChronicleButton.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ChronicleButton from "./ChronicleButton";

describe("ChronicleButton", () => {
    it("renders label", () => {
        render(<ChronicleButton>Projektgruppen</ChronicleButton>);
        expect(screen.getByRole("button", { name: "Projektgruppen" })).toBeInTheDocument();
    });

    it("calls onClick when clicked", async () => {
        const handler = vi.fn();
        render(<ChronicleButton onClick={handler}>Klick</ChronicleButton>);
        await userEvent.click(screen.getByRole("button"));
        expect(handler).toHaveBeenCalledOnce();
    });

    it("is disabled when disabled prop is set", () => {
        render(<ChronicleButton disabled>Gesperrt</ChronicleButton>);
        expect(screen.getByRole("button")).toBeDisabled();
    });

    it("renders ghost variant without gradient background", () => {
        const { container } = render(<ChronicleButton variant="ghost">Ghost</ChronicleButton>);
        const btn = container.firstChild as HTMLElement;
        expect(btn.style.background).toBe("");
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleButton.test.tsx
```
Expected: FAIL — "Cannot find module './ChronicleButton'"

- [ ] **Step 3: Implement ChronicleButton**

`apps/frontend/src/components/chronicle/ChronicleButton.tsx`:

```tsx
import type { ReactNode, CSSProperties, MouseEventHandler } from "react";

type Variant = "primary" | "ghost";

type Props = {
    children: ReactNode;
    variant?: Variant;
    onClick?: MouseEventHandler<HTMLButtonElement>;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
    className?: string;
    style?: CSSProperties;
};

const primaryStyle: CSSProperties = {
    background: "linear-gradient(135deg, #041920 0%, #1a2e35 100%)",
    color: "var(--c-on-primary)",
    border: "none",
};

const ghostStyle: CSSProperties = {
    background: "",
    color: "var(--c-secondary)",
    border: "1px solid var(--c-outline-ghost)",
};

export default function ChronicleButton({
    children,
    variant = "primary",
    onClick,
    disabled,
    type = "button",
    className,
    style,
}: Props) {
    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={className}
            style={{
                ...(variant === "primary" ? primaryStyle : ghostStyle),
                borderRadius: "var(--radius-sharp)",
                fontFamily: "var(--font-sans)",
                fontSize: "0.875rem",
                fontWeight: 500,
                padding: "8px 16px",
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.5 : 1,
                letterSpacing: "0.01em",
                ...style,
            }}
        >
            {children}
        </button>
    );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/ChronicleButton.test.tsx
```
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/components/chronicle/ChronicleButton.tsx \
        apps/frontend/src/components/chronicle/ChronicleButton.test.tsx
git commit -m "feat(design): add ChronicleButton component"
```

---

## Task 7: Barrel export

**Files:**
- Create: `apps/frontend/src/components/chronicle/index.ts`

- [ ] **Step 1: Create barrel**

`apps/frontend/src/components/chronicle/index.ts`:

```ts
export { default as ChronicleCard } from "./ChronicleCard";
export { default as ChronicleButton } from "./ChronicleButton";
export { default as ChronicleHeadline } from "./ChronicleHeadline";
export { default as ChronicleDataChip } from "./ChronicleDataChip";
```

- [ ] **Step 2: Run all Chronicle tests to confirm everything passes**

```bash
cd apps/frontend && npx vitest run src/components/chronicle/
```
Expected: All tests PASS (no failures)

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/components/chronicle/index.ts
git commit -m "feat(design): add Chronicle component barrel export"
```

---

## Task 8: Apply Chronicle to ProjectCard

**Files:**
- Modify: `apps/frontend/src/features/projects/ProjectGroupsPage.tsx`

The `ProjectCard` component (lines 191–253) uses `Card withBorder shadow="xs" radius="md"`. Replace with `ChronicleCard`. The `Badge` components for project attributes become `ChronicleDataChip`.

- [ ] **Step 1: Add import at top of `ProjectGroupsPage.tsx`**

After the existing imports, add:

```tsx
import { ChronicleCard, ChronicleDataChip, ChronicleHeadline } from "../../components/chronicle";
import "../../components/chronicle/tokens.css";
```

- [ ] **Step 2: Replace `ProjectCard` function (lines 191–253)**

Replace the entire `ProjectCard` export with:

```tsx
export function ProjectCard({ project }: { project: Project }) {
    const lengthValue = typeof project.length === "number" ? `${project.length.toLocaleString("de-DE")}` : null;
    const hasProjectId = typeof project.id === "number" && Number.isFinite(project.id);

    const cardContent = (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-editorial)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: "1rem", color: "var(--c-on-surface)" }}>
                    {project.name}
                </span>
                {project.project_number && (
                    <span style={{ fontFamily: "var(--font-sans)", fontSize: "0.8125rem", color: "var(--c-secondary)", opacity: 0.8 }}>
                        Projektnummer: {project.project_number}
                    </span>
                )}
            </div>

            {project.description ? (
                <p style={{ fontFamily: "var(--font-sans)", fontSize: "0.875rem", color: "var(--c-on-surface)", opacity: 0.7, margin: 0, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                    {project.description}
                </p>
            ) : (
                <p style={{ fontFamily: "var(--font-sans)", fontSize: "0.875rem", fontStyle: "italic", color: "var(--c-on-surface)", opacity: 0.5, margin: 0 }}>
                    Keine Projektbeschreibung vorhanden.
                </p>
            )}

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {lengthValue && <ChronicleDataChip>Länge: {lengthValue} km</ChronicleDataChip>}
                {project.elektrification && <ChronicleDataChip>Elektrifizierung</ChronicleDataChip>}
                {project.second_track && <ChronicleDataChip>Zweigleisiger Ausbau</ChronicleDataChip>}
                {project.new_station && <ChronicleDataChip>Neuer Bahnhof</ChronicleDataChip>}
            </div>
        </div>
    );

    if (hasProjectId) {
        return (
            <Link to={`/projects/${project.id}`} style={{ textDecoration: "none", display: "block" }}>
                <ChronicleCard accent>
                    {cardContent}
                </ChronicleCard>
            </Link>
        );
    }
    return (
        <ChronicleCard>
            {cardContent}
        </ChronicleCard>
    );
}
```

`Link` from react-router-dom (already imported in this file) is used for SPA client-side navigation. `ChronicleCard` does not need an `href` prop.

- [ ] **Step 3: Run the dev server and visually verify the Projects list page**

```bash
cd apps/frontend && npm run dev
```
Open http://localhost:5173 and navigate to the Projects list. Confirm:
- Cards have no visible border
- Project attribute chips are small rectangular chips (not rounded Mantine badges)
- Active/linked cards have a green left accent bar
- No layout breakage

- [ ] **Step 4: Run existing tests to confirm no regression**

```bash
cd apps/frontend && npx vitest run
```
Expected: All pre-existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/projects/ProjectGroupsPage.tsx
git commit -m "feat(design): apply Chronicle to ProjectCard"
```

---

## Task 9: Apply Chronicle page wrapper to ProjectGroupsPage

**Files:**
- Modify: `apps/frontend/src/features/projects/ProjectGroupsPage.tsx`

The page title "Projekte nach Projektgruppen" and the group info card should use Chronicle styles. The page root gets `.chronicle-theme`.

- [ ] **Step 1: Wrap the `ProjectGroupsPage` return in `.chronicle-theme`**

In `ProjectGroupsPage` (the default export, around line 73), change:

```tsx
return (
    <Container size="xl" py="xl">
```

to:

```tsx
return (
    <div className="chronicle-theme">
    <Container size="xl" py="xl">
```

And close the wrapper before the final closing tag:

```tsx
    </Container>
    </div>
);
```

- [ ] **Step 2: Replace page title `<Title order={2}>` with `ChronicleHeadline`**

Change (around line 77):

```tsx
<Title order={2}>Projekte nach Projektgruppen</Title>
```

to:

```tsx
<ChronicleHeadline as="h2">Projekte nach Projektgruppen</ChronicleHeadline>
```

- [ ] **Step 3: Replace the group info `<Card>` with `ChronicleCard`**

Around line 105, change:

```tsx
<Card withBorder radius="md" padding="lg" shadow="xs">
    <Stack gap="xs">
        <Group justify="space-between" align="flex-start">
            <Stack gap={4}>
                <Title order={3}>{selectedGroup.name}</Title>
```

to:

```tsx
<ChronicleCard>
    <Stack gap="xs">
        <Group justify="space-between" align="flex-start">
            <Stack gap={4}>
                <ChronicleHeadline as="h3">{selectedGroup.name}</ChronicleHeadline>
```

And close with `</ChronicleCard>` instead of `</Card>`.

- [ ] **Step 4: Replace the "Projekte" section title `<Title order={3}>` with `ChronicleHeadline`**

Around line 162:

```tsx
<Title order={3}>Projekte</Title>
```

→

```tsx
<ChronicleHeadline as="h3">Projekte</ChronicleHeadline>
```

- [ ] **Step 5: Remove unused `Card` and `Title` from Mantine imports if no longer used**

Check the import at the top of `ProjectGroupsPage.tsx` — remove `Card` and `Title` from the `@mantine/core` import if they are no longer referenced elsewhere in the file.

- [ ] **Step 6: Run all tests**

```bash
cd apps/frontend && npx vitest run
```
Expected: PASS

- [ ] **Step 7: Visually verify the Projects page**

Open http://localhost:5173/projects. Confirm:
- Page background is warm off-white (`#fbf9f8`)
- Section headers use Noto Serif
- Group info card has no border, sits on lighter background
- All other pages (map, finves, admin, etc.) look identical to before

- [ ] **Step 8: Commit**

```bash
git add apps/frontend/src/features/projects/ProjectGroupsPage.tsx
git commit -m "feat(design): apply Chronicle layout to ProjectGroupsPage"
```

---

## Task 10: Apply Chronicle to MapControls floating panel

**Files:**
- Modify: `apps/frontend/src/features/map/MapControls.tsx`

`MapControls` renders a floating `<Paper>` with `withBorder`. Replace with a Chronicle glassmorphic panel.

- [ ] **Step 1: Add imports to `MapControls.tsx`**

After existing imports, add:

```tsx
import { ChronicleButton } from "../../components/chronicle";
import "../../components/chronicle/tokens.css";
```

- [ ] **Step 2: Replace `<Paper>` wrapper with a Chronicle floating panel**

Replace (around line 40):

```tsx
<Paper p="sm" radius="md" shadow="sm" withBorder>
```

with:

```tsx
<div
    className="chronicle-theme"
    style={{
        background: "rgba(251, 249, 248, 0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderRadius: "var(--radius-sharp)",
        boxShadow: "var(--shadow-float)",
        padding: "12px",
        border: "1px solid var(--c-outline-ghost)",
    }}
>
```

And change the closing `</Paper>` to `</div>`.

- [ ] **Step 3: Replace the Mantine `<Button>` with `ChronicleButton`**

Change (around line 62):

```tsx
<Button size="sm" color="petrol" onClick={onOpenFilters}>
    Projektgruppen
</Button>
```

to:

```tsx
<ChronicleButton onClick={onOpenFilters}>
    Projektgruppen
</ChronicleButton>
```

- [ ] **Step 4: Remove `Paper` and `Button` from Mantine imports in `MapControls.tsx` if no longer used**

Check the `@mantine/core` import at the top and remove `Paper` and `Button` if not referenced elsewhere.

- [ ] **Step 5: Run all tests**

```bash
cd apps/frontend && npx vitest run
```
Expected: PASS

- [ ] **Step 6: Visually verify the Map page**

Open http://localhost:5173 (map is the default view). Confirm:
- The floating controls panel on the top-right has a frosted-glass appearance
- "Projektgruppen" button uses the dark gradient Chronicle style
- The map itself is unaffected
- The panel does not cover or obscure map tiles awkwardly

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/features/map/MapControls.tsx
git commit -m "feat(design): apply Chronicle glassmorphic panel to MapControls"
```

---

## Task 11: Final regression check

- [ ] **Step 1: Run the full test suite**

```bash
cd apps/frontend && npx vitest run
```
Expected: All tests PASS (no regressions)

- [ ] **Step 2: Spot-check non-showcase pages**

Open each of these pages and confirm they look identical to before this branch:
- `/finves` — FinVe overview
- `/haushalt-import` — Haushalt import
- `/vib-import` — VIB import
- `/admin` — Admin panel

No Chronicle styles should appear on any of these.

- [ ] **Step 3: Update roadmap**

In `docs/roadmap.md`, mark the Chronicle design system rollout as in progress / complete per project convention.

- [ ] **Step 4: Final commit**

```bash
git add docs/roadmap.md
git commit -m "docs: mark Chronicle design system rollout (showcase pages) complete"
```

---

*See also: `docs/DESIGN.md` (design system reference), `docs/features/feature-design-system.md` (spec)*
