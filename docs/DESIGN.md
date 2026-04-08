# Design System Document: Editorial Intelligence for Infrastructure

## 1. Overview & Creative North Star

### The Creative North Star: "The Architectural Chronicle"
This design system moves away from the common "SaaS dashboard" aesthetic of rounded corners and playful accents. Instead, it adopts the persona of a high-end editorial publication—think the *Frankfurter Allgemeine Zeitung* or *The New York Times*. 

The system treats data not just as raw information, but as a narrative of national importance. It is characterized by **authoritative serif typography**, **delicate tonal layering**, and **intentional asymmetry**. By prioritizing "The Architectural Chronicle" vision, we create an environment that feels stable, intellectual, and deeply reliable—essential traits for large-scale railway project management.

---

## 2. Colors

The palette is restrained and sophisticated, utilizing deep charcoals and refined forest greens to anchor the experience against a warm, paper-like background.

### Tonal Foundations
- **Primary (`#041920`):** Use for high-level navigation and primary text. It provides the "ink on paper" authority.
- **Secondary (`#006a6a`):** The "Schienengrün" accent. Used sparingly for data status, successful states, or critical calls to action.
- **Surface (`#fbf9f8`):** An off-white, warm neutral that mimics high-quality recycled paper, reducing eye strain and feeling more "custom" than pure white.

### The "No-Line" Rule
To achieve a premium editorial feel, **1px solid borders are prohibited for sectioning.** Boundaries must be defined through background color shifts.
- A card should not have an outline; it should be a `surface-container-lowest` (`#ffffff`) block sitting on a `surface-container-low` (`#f5f3f3`) background.
- This creates "soft" boundaries that feel like a physical layout rather than a digital wireframe.

### Signature Textures
- **The Gradient Whisper:** For primary CTAs or data hero sections, use a subtle linear gradient from `primary` (`#041920`) to `primary_container` (`#1a2e35`). This adds a "lithographic" depth that flat colors cannot achieve.
- **Glassmorphism:** For floating map controls or overlays, use `surface` at 80% opacity with a `20px` backdrop-blur. This keeps the data (the map or the list) visible beneath the UI, maintaining context.

---

## 3. Typography

The system relies on the tension between a traditional serif and a modern sans-serif.

### Display & Headlines: Noto Serif
The serif font is our "Voice of Authority."
- **Display (Lg/Md/Sm):** Use for major dashboard titles. These should be set with tight letter-spacing (-2%) to feel impactful.
- **Headline (Lg/Md/Sm):** Use for section headers. In an editorial layout, these are the "articles" of your dashboard.

### UI & Data: Inter
Inter is the "Workhorse."
- **Title & Body:** All interactive elements, labels, and paragraph text use Inter. 
- **Label (Md/Sm):** Data points should use `label-md` or `label-sm` with slightly increased letter-spacing (+5%) for maximum legibility in dense tables.

---

## 4. Elevation & Depth

We reject the standard "Material" elevation. Depth in this system is achieved through **Tonal Layering**.

- **The Layering Principle:** Stack surfaces from darkest/lowest to brightest/highest.
    - **Level 0 (Background):** `surface` (`#fbf9f8`)
    - **Level 1 (Sections):** `surface-container-low` (`#f5f3f3`)
    - **Level 2 (Cards/Interaction):** `surface-container-lowest` (`#ffffff`)
- **Ambient Shadows:** Shadows are rare. When a card must float (e.g., a map tooltip), use a highly diffused shadow: `box-shadow: 0 12px 32px -4px rgba(27, 28, 28, 0.06)`. The tint is derived from `on-surface` for a natural look.
- **Ghost Borders:** If a border is required for accessibility, use `outline-variant` (`#c2c7ca`) at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Buttons
- **Primary:** Sharp corners (`rounded-sm`: 0.125rem). Background is the `primary` to `primary_container` gradient. Text is `on_primary`.
- **Tertiary (Ghost):** No background. Text is `secondary`. On hover, apply a `surface-container-high` background shift.

### Input Fields
- **Styling:** Use the "Bottom-Line Only" approach or a very faint `surface-container-highest` background. 
- **Focus:** Transition the bottom line to `secondary` (`#006a6a`). Avoid heavy focus rings; use a 2px offset "Ghost Border" instead.

### Cards & Lists
- **Forbid Dividers:** Do not use horizontal lines between list items. Use 16px or 24px of vertical white space (the "Editorial Gap") to separate content.
- **Header Accents:** A 3px vertical accent of `secondary` (`#006a6a`) on the left side of a card can denote an "active" or "highlighted" railway project.

### Data Chips
- **Style:** Small, rectangular, `0px` or `2px` rounding.
- **Color:** Use `tertiary_container` for a muted, archival feel that doesn't distract from the primary data.

---

## 6. Do's and Don'ts

### Do
- **Do** use generous white space. If you think there is enough space, add 8px more.
- **Do** use `notoSerif` for any text that is meant to be "read" (titles, quotes, insights).
- **Do** align elements to a strict baseline grid to maintain the "newspaper" structure.
- **Do** use `surface-container` shifts to group related railway metrics.

### Don't
- **Don't** use `rounded-lg` or `rounded-xl`. Keep it sharp (`0.125rem`) to maintain the "serious" tone.
- **Don't** use standard blue for links. Use `secondary` (`#006a6a`) or `primary` with an underline.
- **Don't** use high-contrast shadows. If the UI looks like it's "hovering" too much, it loses its grounded, reliable feel.
- **Don't** use icons as primary navigation without labels. The editorial style prizes clarity and literacy.

---

*This design system is a living document. Every update should be measured against the North Star: Does this feel like an authoritative report or a temporary app? Always choose the former.*