# Design System: Bahnhofshalle Tag (Direction F)

## 1. Overview & Creative North Star

### The Creative North Star: "Bahnhofshalle Tag"
The system translates the typographic clarity of a German railway departure board into a daylit, paper-like interface. Information is rendered like a printed timetable: gridded, ordered, functional. Every row earns its place. No decorative filler.

The persona replaces the prior "Architectural Chronicle" (FAZ editorial, dark teal, Noto Serif) with a station-hall idiom: warm white surfaces, Anthracite ink, Gold accent, Prussian-Blue weight, sharp-cornered components, no gradients, no glow in daylight.

Three principles:

1. **Tafel-Denken** — Information is a timetable: gridded, typographic, functional.
2. **Hell mit Kontrast** — Warm-white as hall, Anthracite as ink, Gold as accent. Dark surfaces are reserved for the "Tafel" component, where status, times, and live info live.
3. **Seriös, nicht steril** — Prussian-Blue gives weight, Gold gives warmth. Signal-Red and Go-Green mark *states*, not mood. No neon, no gradients, no glow.

---

## 2. Colors

All hex values are exposed as CSS custom properties (see `tokens.css`).

### Surfaces — "Hallenlicht"
| Token       | Hex       | Name        | Usage                                            |
|-------------|-----------|-------------|--------------------------------------------------|
| `--bg`      | `#ffffff` | Halle       | Main canvas, side background, cards.             |
| `--bg2`     | `#f3f1ec` | Wartehalle  | Warm section surfaces, KPI cards, alt rows.      |
| `--bg3`     | `#e9e6df` | Schiefer    | Alternating rows in tables/lists.                |
| `--bg4`     | `#dedad0` | Sandstein   | Separator bands, footer strip, hover state.      |
| `--rule`    | `#d6d2c6` | Hairline    | All 1px separators, table grid, card borders.    |
| `--ruleHot` | `#b8b2a3` | Raster hot  | Accented separator under headlines.              |

### Ink — Typography
| Token    | Hex       | Name      | Usage                                          |
|----------|-----------|-----------|------------------------------------------------|
| `--ink`  | `#0d1013` | Anthrazit | Headlines, primary text, buttons, signet.      |
| `--ink2` | `#3d4550` | Fließtext | Body copy, descriptions, secondary text.       |
| `--ink3` | `#7a8390` | Meta      | Labels, timestamps, hairline-text.             |

### Accents
| Token       | Hex       | Name             | Usage                                               |
|-------------|-----------|------------------|-----------------------------------------------------|
| `--led`     | `#c98a00` | Gold · Tag       | Primary accent on light: `<em>`, signet dot, CTA.   |
| `--ledHot`  | `#e8a417` | Gold · Tafel     | Tafel component, status LEDs on dark.               |
| `--ledDim`  | `#7a5300` | Gold dunkel      | Inactive state, hover contrast on gold.             |
| `--info`    | `#0f2347` | Preußenblau      | KPIs, infographics, links. Weight, not warmth.      |

### Status — Signals
| Token         | Hex       | Name        | Usage                                       |
|---------------|-----------|-------------|---------------------------------------------|
| `--signal`    | `#c41a1a` | Signalrot   | Delay, cancellation, urgent warning.        |
| `--signalDim` | `#8a1818` | Signal dunkel | Reduced/border variant.                   |
| `--go`        | `#058a44` | Go-Grün     | On-plan, on-time, signed.                   |
| `--goDim`     | `#03602e` | Go dunkel   | Reduced/border variant.                     |

### Tafel — Dark Component Surfaces
The dark palette is **scoped to the Tafel component family** (live boards, tickers, departure-style displays). It does not bleed into general layout.

| Token         | Hex       | Name      | Usage                                |
|---------------|-----------|-----------|--------------------------------------|
| `--board`     | `#111418` | Tafel     | Tafel base surface.                  |
| `--board2`    | `#1b2028` | Tafel 2   | Tafel inner panels.                  |
| `--boardRule` | `#2a323b` | Tafel-rule | Separators inside Tafel.            |

### Forbidden / Avoid
- DB red (`#ec0016`) — political/brand collision with Deutsche Bahn.
- Party colors (any saturated political flag color).
- Gradients (`linear-gradient`, `radial-gradient`) — flat surfaces only.
- Gold "glow" (`box-shadow` halos) in day mode.
- Rounded corners on data containers — corners are sharp like a board.

---

## 3. Typography

Three families. No serifs.

### Display & Headlines: **Archivo Narrow** (700)
- Compressed sans, station-board feel. Always **uppercase** for display sizes.
- Variable letter-spacing tightens at larger sizes.
- Fallbacks: `'Oswald', Impact, sans-serif`.

| Class               | Size / Line | Tracking  | Use                                  |
|---------------------|-------------|-----------|--------------------------------------|
| `.type-display-xl`  | 96 / 86     | −0.03em   | Hero, page-title.                    |
| `.type-display-l`   | 64 / 59     | −0.02em   | Page H1.                             |
| `.type-display-m`   | 40 / 38     | −0.015em  | Section H2.                          |
| `.type-display-s`   | 24 / 24     | −0.005em  | Card headline, modal title.          |

### Mono: **IBM Plex Mono**
- Labels, timestamps, eyebrows, KPI legends, table meta.
- Wider apertures than Space Mono — more legible at 10–12 px.
- Always uppercase + 0.06–0.18em letter-spacing for eyebrows (looser at small sizes since IBM Plex Mono is naturally wider).
- Fallbacks: `'JetBrains Mono', ui-monospace, monospace`.

| Class             | Size / Line | Tracking | Use                                  |
|-------------------|-------------|----------|--------------------------------------|
| `.type-mono-eye`  | 11 / —      | 0.18em   | Eyebrow above headlines, breadcrumbs. |
| `.type-mono-body` | 13 / 20     | 0.02em   | Mono body, code-like blocks.         |

### Body: **IBM Plex Sans**
- Long-form copy. 400/500/600/700.
- Wide x-height, neutral German rendering, pairs cleanly with IBM Plex Mono — single type family for body + labels.
- Body baseline: 15 px / line-height 1.6 (paragraphs 1.65). Smaller is squished; do not go below 14 px for prose.
- Fallbacks: `'Inter', -apple-system, BlinkMacSystemFont, sans-serif`.

| Class         | Size / Line | Tracking | Use                              |
|---------------|-------------|----------|----------------------------------|
| `.type-body`  | 15 / 25     | 0em      | Body text.                       |
| `.type-small` | 13 / 20     | 0em      | Captions, meta, datestamps.      |

### Em-highlight rule
Inside any display/heading, `<em>` switches to **non-italic, color `--led`** (Gold). It is the brand's punctuation: it carries the dot.

```html
<h1>Vernetzt. <em>Bewegt.</em></h1>
```

---

## 4. Spacing & Grid

Base unit **4 px**. Standard scale: **8 / 16 / 24 / 32 / 48 / 72 / 96 / 120**.

| Token  | Px  | Use                          |
|--------|-----|------------------------------|
| `xs`   | 8   | Inline, icon-text gap.       |
| `s`    | 16  | Small gap.                   |
| `m`    | 24  | Card padding.                |
| `l`    | 32  | Component gap.               |
| `xl`   | 48  | Section gap (vertical).      |
| `2xl`  | 72  | Hero breathing room.         |
| `3xl`  | 96  | Hero padding.                |
| `4xl`  | 120 | Full-bleed.                  |

- Page max-width: `1320px`, page padding `48px 40px 120px`.
- Section vertical padding ≥ 48 px, horizontal page gutter 40 px.
- **Border-radius is `0`** for data containers, cards, buttons, inputs.

---

## 5. Components

### Buttons (`.btn`)
- Mono uppercase label, 0.12em tracking, sharp corners.
- Default: solid Anthracite on white text. Hover: Gold background, Anthracite text.
- Variants: `.primary` (Preußenblau bg), `.outline` (Preußenblau text on white), `.ghost` (transparent).
- Size variant: `.small` (10.5px label, tighter padding).

### LED-Dots (`.led-dot`)
8 px circles for inline status. Variants: default (Gold), `.go`, `.sig`, `.info`. Always paired with mono label.

### Section-Head
A three-column grid: **flap-number** (left, 112×120, sharp, `--bg2` background, hairline separator across middle) + eyebrow + H2 (Archivo Narrow uppercase) + right-aligned descr (Work Sans, max-w 320, `--ink2`).

### Tafel · Live-Board (Mini-Board)
The signature dark component. Header row: status LED + bold label + right-aligned mono context. Body rows: `60px t (Preußenblau bold) | 1fr d (Display, uppercase) | 28px g (Gold, right) | 90px s (status with LED-dot)`. Dashed hairline between rows.

### Split-Flap
Inline 38×48 chips with `--bg2` fill, `--ruleHot` border, Display 30 px, sharp 1-px hairline across middle (mimics flap seam). Used for digits *and* letters.

### Ticker
Mono 11.5 px uppercase 0.1em on **Amber background `#fcecb3`**, Gold border. No animation by default (CSS-driven scroll optional).

### KPI Card
`--bg2` background, 3-px Preußenblau left border. Mono eyebrow → 56-px Display value in Preußenblau (with 28-px secondary unit in `--ink3`) → mono description.

### Wordmark + Signet
- Wordmark: Archivo Narrow uppercase, baseline-aligned `<span class="dot">.</span>` in Gold. Sizes `.lg` 48px / `.md` 28px / `.sm` 18px / `.inv` (white text on `--ink` block).
- Signet: 44×44 Anthracite square containing a 14×14 Gold inner square (with double-shadow). Used as favicon, app-icon, mark-block in slide headers.

### Do / Don't
- ✅ Punkt am Markenende in Gold. Narrow-Display für Headlines. Hellfläche mit Tafel als Gegenpol.
- ❌ Keine Verläufe. Kein Gold-Glow im Tag. Keine Emoji. Keine abgerundeten Ecken.

---

## 6. Logo & Wordmark

The wordmark **always ends with a Gold dot**. The dot is *the arriving train, the set goal, the departure*. It is the only Gold element in many compositions and must never be desaturated.

Clearzone: 1× wordmark height around the mark. Print min-width 20 mm. Digital min-width 100 px. Never rotated, never on a busy photo without an underlying Anthracite plate.

A finalized logo file does **not yet exist** — the design-system bundle reserves a section for it. Until then, the wordmark + signet pair acts as the brand mark.

---

## 7. Motion & Interaction

- Transitions: `0.12s` linear on hover state changes (button, link).
- No spring, no bouncy easing.
- Animated tickers and flap rolls are reserved for the Tafel component family. Outside Tafel, motion is absent.

---

## 8. Dark Mode

There is **no global dark mode**. Dark surfaces appear only inside the Tafel family (mini-board, ticker on dark, departure displays). The rest of the application stays in daylight. This is intentional: dark = live data, light = editorial context.

---

## 9. Accessibility

- Body text contrast ≥ 7:1 (`--ink2` on `--bg`).
- Display contrast ≥ 12:1 (`--ink` on `--bg`).
- Status colors must always carry a textual label (`Verspätung +12 Min`), never color-alone.
- Focus state: 2-px solid `--led` outline, 2-px offset.

---

## 10. Tokens Reference

The complete token list lives in `apps/frontend/src/components/chronicle/tokens.css` (file path retained for migration, content rewritten). Mantine theme exposes the same tokens via `theme.other.*` for components that need JS access.

See `docs/features/feature-rebrand-direction-f.md` for the rollout plan.
