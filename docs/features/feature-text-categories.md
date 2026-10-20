# Feature: Kategorien und Sichtbarkeit für Projekttexte

## Goal

Project texts can carry a **category** such as „Info“ or „Warnung“ that changes
how the text is displayed, so that a warning about a project stands out from a
plain note. Categories are extensible: editors can add new ones.

Texts can also be marked **internal** („nur für Eingeloggte“), so that a warning
meant for the team is not shown to anonymous visitors.

## Scope

- **Category is a second dimension next to the text type.** The type says *what*
  a text is („Kommentar“, „Kleine Anfrage“), the category says *how urgent* it is
  („Info“, „Warnung“). Both are independent; a „Kommentar“ can be a „Warnung“.
- A category has a `name` (unique) and a **style** chosen from a fixed set. The
  style alone decides the display; there are no free colours or icons, so the
  page stays consistent and readable at 360 px.
- Every text has exactly one category. Existing texts get „Info“.
- **The category belongs to the text**, not to the text–project link. A text
  linked to several projects (`text_to_project` is m:n) shows the same category
  everywhere.
- **Visibility**: a text is either public (default, as before) or internal.
  Internal texts and their attachments are only delivered to signed-in users.
- Out of scope: renaming or deleting categories, sorting or filtering texts by
  category, categories for other entities, per-role visibility.

### Styles

| style | colour token | icon | left border | seeded category |
|---|---|---|---|---|
| `neutral` | `--text-cat-neutral` → `--ink3` | `IconNote` | no | – |
| `info` | `--text-cat-info` → `--info` | `IconInfoCircle` | no | „Info“ |
| `warning` | `--text-cat-warning` → `--warn` (new) | `IconAlertTriangle` | yes | „Warnung“ |
| `critical` | `--text-cat-critical` → `--signal` | `IconAlertOctagon` | yes | – |

**Colours are switchable in one place.** Components never use a base token
directly for a category: they use the semantic tokens `--text-cat-*`, which
`tokens.css` maps to base tokens. Icon, border and token per style live in one
TypeScript map (`textCategoryStyles.ts`). Changing a colour = one line in
`tokens.css`; changing icon or border = one line in the map.

`--warn` is a new base token (dark amber) because `--led` (Gold) is the brand and
CTA accent and must not double as a warning colour (`docs/DESIGN.md` §2).

## Desired behaviour

### Display (project detail page, section „Texte“)
- Only `warning` and `critical` cards get a 3 px left border in the style colour.
  `info`/`neutral` cards stay without border — a blue left border already marks
  highlighted projects and KPI cards (`ChronicleCard accent`).
- The header row shows the style icon in the style colour and the category name
  as a label next to the type („Warnung · Kommentar“). Colour is never the only
  signal (`DESIGN.md` §9).
- Internal texts carry a chip „Intern“ with a lock icon.
- Text, link and attachments render as before. The header row wraps at 360 px.

### Editing
- The text form gets a required select **„Kategorie“** below „Typ“, preset to
  the default category when creating a text.
- A „+“ button next to it opens „Neue Kategorie erstellen“: name + style picker
  (the four styles, each with icon and colour). Needs `projecttext.edit`, like
  creating a type.
- A switch **„Nur für Eingeloggte sichtbar“** (off by default).
- Category and visibility changes are recorded in the text changelog
  („Kategorie“, „Öffentlich“).

### MCP
- New tool `list_text_categories` (id, name, style).
- `upsert_project_text` takes optional `category_id` (omitted on create →
  default category) and `is_public`.
- `get_project_texts` returns `category` (name), `category_style` and `is_public`.
  MCP callers are always authenticated and see internal texts.

## Data model

### `project_text_category` (new)
| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `name` | varchar(100) | not null, unique |
| `style` | varchar(20) | not null, one of `neutral`/`info`/`warning`/`critical` (validated in the API) |

### `project_text` (changed)
| column | type | notes |
|---|---|---|
| `category_id` | int FK → `project_text_category.id` | **nullable in the DB** (expand/contract: code from before this change still inserts texts without it); the API always sets it |
| `is_public` | bool | not null, server default `true` (older code keeps working) |

Migration: create the table, seed „Info“ (`info`) and „Warnung“ (`warning`),
add both columns, backfill all existing texts with „Info“.

**Default category** = the category named „Info“; if it is missing, the one with
the lowest id. A text with `category_id = NULL` (written by older code after a
rollback) is shown with the default category in the UI and in MCP.

## API

| method | path | auth | notes |
|---|---|---|---|
| GET | `/api/v1/text_categories` | public | list, ordered by id |
| POST | `/api/v1/text_categories` | `projecttext.edit` | `{name, style}`; 409 on duplicate name, 422 on unknown style |
| GET | `/api/v1/projects/{id}/texts` | optional | anonymous → public texts only |
| GET | `/api/v1/projects/texts/{id}/attachments[/{aid}/download]` | optional | internal text + anonymous → 404 |

- `ProjectTextSchema` gains `category_id`, `category` (`{id, name, style}` or
  null, see default above) and `is_public`.
- `ProjectTextCreate`/`ProjectTextUpdate` gain optional `category_id` and
  `is_public`. Unknown `category_id` → 422.

## Decisions

| date | decision |
|---|---|
| 2026-10-20 | Category is its own dimension next to the type, with a fixed style set (W-check before planning). |
| 2026-10-20 | W1: new token `--warn` instead of `--led`; categories use semantic tokens `--text-cat-*` so colours can be switched centrally. |
| 2026-10-20 | W2: only `warning`/`critical` get a left border. |
| 2026-10-20 | W3: text visibility (roadmap item was ticked but never built) is implemented here. |
| 2026-10-20 | W4: the category belongs to the text and applies to all linked projects. |

## Acceptance criteria

- [ ] Existing texts show as „Info“ (icon + label, no border) after the migration.
- [ ] A text set to „Warnung“ shows the amber border, warning icon and label.
- [ ] A new category with style `critical` can be created from the form and is selectable right away.
- [ ] Creating a text without a category (API/MCP) assigns „Info“.
- [ ] An internal text is hidden for anonymous visitors (list and attachment download) and visible after login.
- [ ] Category and visibility changes appear in the text history.
- [ ] Changing `--text-cat-warning` in `tokens.css` recolours icon and border of all warnings.
- [ ] Layout works at 360 px.
- [ ] `make test` green.
