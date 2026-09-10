# Feature: Mobile Usability (Smartphone)

## Goal

The whole application must be usable on a smartphone. Today the frontend is
built for wide screens: the map is a fixed 800 px block with a floating control
panel, data tables run far past the viewport, detail rows reserve 200 px for
their label, filter rows are horizontal `Group`s, and drawers/modals keep their
desktop width. On a 360 × 640 phone this produces horizontal page scrolling,
clipped controls and unreachable actions.

"Usable" here means: every route can be reached, read and operated with one
thumb on a 360 px viewport, without pinch-zoom and without sideways scrolling of
the page itself.

## Scope

In scope — every route the router serves, grouped by how far the redesign goes:

| Surface | Target on a phone |
|---|---|
| Header / navigation | Burger drawer with large tap targets, wordmark shrinks to the signet |
| Map view (`/`) | Map fills the visible viewport, controls collapse into a bottom sheet |
| List view (`/?view=list`) | Filters stack, one project card per row |
| Project detail | Single column, stacked detail rows, map below the data, actions in a menu |
| Haushalt / FinVe, Abgeordnete, Aufgaben | Stacked filters, horizontally scrollable tables |
| Admin & import pages | Reachable and operable; wide tables scroll horizontally inside their card |
| Guides & documentation | Reflow to one column, tables scroll |

Out of scope (explicitly): native app packaging, offline mode, service worker,
push notifications, and a redesign of the import wizards beyond making them
operable. Editing long PDF-review tables on a phone stays possible but is not
optimised for comfort — that work happens on a desktop.

## Breakpoints

One shared set, exported from `src/shared/hooks/useBreakpoint.ts`, matching the
Mantine defaults so CSS and JS agree:

| Name | Query | Meaning |
|---|---|---|
| `useIsMobile()` | `max-width: 48em` (768 px) | Phone — single column, bottom sheets |
| `useIsCompact()` | `max-width: 62em` (992 px) | Phone or small tablet — burger nav, stacked filters |

CSS uses the same two values (`48em` / `62em`). Never introduce a third
breakpoint in a component without adding it here first.

## Desired behaviour

### Foundation

- `index.html` viewport gets `viewport-fit=cover`; the fixed header and any
  bottom sheet respect `env(safe-area-inset-*)`.
- Global mobile CSS layer in `src/app.css`:
  - form controls render at 16 px on phones so iOS Safari does not zoom on focus,
  - Mantine modals go full-width (and near full-height) below `48em`,
  - headings scale down (`h1` 40 px → 28 px),
  - `img`/`svg`/`pre` never exceed their container,
  - buttons and inputs keep a ≥ 44 px touch target on coarse pointers.
- Responsive design tokens in `tokens.css`: `--card-pad`, `--page-pad`,
  `--map-height` and `--map-height-detail` shrink on phones. Components read the
  token instead of hard-coding `24px` / `800px`, so a single media query moves
  the whole system.
- `AppShell` padding follows `--page-pad`.

### Tables

Data tables are the main source of horizontal page scroll. A shared
`ResponsiveTable` (`src/shared/ui/ResponsiveTable.tsx`) wraps Mantine's `Table`
in a `Table.ScrollContainer`: the table keeps a sensible minimum width and
scrolls **inside its card** instead of pushing the page sideways. Every data
table in the app uses it; `Table.Thead`/`Tbody`/`Tr`/`Td` stay untouched, so the
change is a one-line swap per table.

### Map

- `MapView` accepts a CSS length for `height` and defaults to the
  `--map-height` token. On the map page the map fills
  `100dvh − header − view toggle`; on project detail it is a shorter block.
- `MapControls` splits by breakpoint:
  - **Desktop** — unchanged floating panel top-right.
  - **Phone** — a slim search field pinned to the top of the map plus a
    "Filter" button that opens a **bottom sheet** holding project groups,
    layer switches and the line/point sliders. The sheet closes on apply.
- The click popup is capped to `min(340px, 100vw − 32px)` so it can never leave
  the screen.
- `ConstituencyPanel` becomes a bottom sheet on phones (full width, max 55 % of
  the viewport height, scrollable) instead of a fixed 340 px left panel.

### Project detail

- Header: title, then the actions. On phones the secondary actions
  ("Zur Karte", "Zur Projektübersicht", "Geometrie verwalten", "Löschen") move
  into a `Menu`, leaving "Bearbeiten" as the single visible button.
- `DetailRow` stacks label above value below `48em` (no 200 px label column).
- The two-column details/map grid collapses to one column (already `base: 12`),
  and the map block uses the shorter mobile height.
- The floating table of contents keeps its left-edge button but the panel is
  capped to `calc(100vw − 64px)`.

### Drawers and modals

- Drawers we own (`GroupFilterDrawer`, `TodoEditDrawer`, `ProgressEditDrawer`,
  `ProjectEdit`, `VibEntryEditDrawer`, header navigation) open at full width on
  phones (`size="100%"`), keeping their desktop size otherwise.
- Modals become full-width through the global CSS layer, so no per-modal change
  is needed; long modal bodies scroll.

### Filter rows

Every `Group` that carries filters (search + select + switch) becomes a
`Stack`/`SimpleGrid` below `62em`. Rule of thumb: a filter row never scrolls
horizontally, it wraps.

## Acceptance criteria

- At a 360 × 640 viewport, `document.documentElement.scrollWidth` equals the
  viewport width on `/`, `/?view=list`, `/projects/:id`, `/finves`,
  `/abgeordnete`, `/tasks`, `/admin` — no horizontal page scroll.
- The map on `/` shows at least ~60 % of the viewport height and its controls
  are reachable without covering more than a slim strip of the map.
- Every data table either fits or scrolls within its own container.
- All primary actions (navigate, search, filter, open a project, create a task)
  are operable with touch, with targets ≥ 44 px.
- No route renders content underneath the fixed header or the iOS home
  indicator.
- `npm run lint`, `npm test` and `npm run build` stay green.

## Technical notes

- Mantine 8 is already responsive-capable (`SimpleGrid cols={{base,sm,lg}}`,
  `Grid.Col span={{...}}`, `visibleFrom` / `hiddenFrom`). Prefer those props
  over `useMediaQuery` where the choice is purely layout; use the hooks when the
  component tree itself differs (bottom sheet vs. floating panel).
- `useMediaQuery` returns `undefined` on the server/first paint; the hooks
  normalise that to `false` so desktop is the fallback and the layout never
  flickers into a mobile shell on a wide screen.
- `100dvh` is used with a `100vh` fallback so older iOS Safari still gets a
  sensible height.
- No new dependency is required.

## Manual test checklist (German, for the board issue)

- [ ] Auf dem Smartphone `/` öffnen: Karte füllt den Bildschirm, keine seitliche
      Verschiebung der Seite beim Wischen.
- [ ] Auf der Karte „Filter" tippen: Bottom-Sheet öffnet sich, Projektgruppen
      lassen sich auswählen, „Übernehmen" schließt das Sheet und die Karte zeigt
      die Auswahl.
- [ ] „Strecken" und „Wahlkreise" im Sheet umschalten: Layer erscheinen bzw.
      verschwinden.
- [ ] Wahlkreis auf der Karte antippen: Panel erscheint unten, ist scrollbar und
      lässt sich schließen.
- [ ] Projekt auf der Karte antippen: Popup bleibt vollständig sichtbar,
      „Auswählen" öffnet die Detailseite.
- [ ] Auf `/?view=list` wechseln: Filter stehen untereinander, Projektkarten
      einspaltig, Suche funktioniert.
- [ ] Projektdetailseite: Titel lesbar, Aktionen über das Menü (⋯) erreichbar,
      Detailzeilen stehen als Label/Wert untereinander, Karte darunter sichtbar.
- [ ] Auf `/finves`, `/abgeordnete`, `/tasks`: Tabellen lassen sich innerhalb
      ihrer Karte seitwärts schieben, die Seite selbst nicht.
- [ ] Menü (Burger) öffnen: alle Navigationspunkte mit dem Daumen treffbar,
      Anmelden/Abmelden funktioniert.
- [ ] Ein Eingabefeld antippen (z. B. Suche): iOS zoomt nicht in die Seite.
