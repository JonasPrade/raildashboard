# Feature: Design der Initiative Deutschlandtakt (IDT-Design)

Stand: 2026-10-21. Status: **umgesetzt (Stufen 1–4), Abnahme offen**. Ersetzt „Richtung F ·
Bahnhofshalle Tag“ (`feature-rebrand-direction-f.md`, abgelöst) vollständig.

Dieses Dokument ist für die Umsetzung durch ein Sprachmodell geschrieben: Es
enthält alle Werte, Dateilisten und Zuordnungen, damit nichts geraten werden
muss. Wo etwas offen bleibt, steht es unter „Offen“ und wird als Issue
geklärt, nicht still entschieden (`docs/architecture.md` → Grundsätze).

## Ziel

Das Schienendashboard trägt das Corporate Design der Initiative Deutschlandtakt:
Papier `#FFF6F0`, Ink `#00373C`, Violett als Aktionsfarbe, Cyan sekundär, nur
die Schrift Inter, Radius 0, 2px-Ink-Rahmen, Lucide-Icons. Die Werkzeug-
Bausteine (Tabellen, Felder, Dialoge, Zustände, Status, Register) folgen der
**Anwendungsebene** des Studios. Es gibt eine optionale **Dunkelfassung** wie im
Strategie-Tool. Keine Vermischung mit Richtung F: Gold, Preußischblau, Archivo
Narrow, IBM Plex, Fallblatt und das Platzhalter-Quadrat verschwinden.

Sichtreferenz: `docs/features/idt-design/01-projektliste.png` bis
`05-mobil-projektdetail.png`, erzeugt aus dem statischen Prototyp
`docs/features/idt-design/prototyp/` (`liste.html`, `detail.html`,
`dialog.html`, `proto.css`; die Schrift `InterVariable.woff2` liegt nach
Stufe 1 unter `apps/frontend/src/shared/theme/fonts/` und wird für den Prototyp nach
`prototyp/fonts/` kopiert). Der Prototyp ist Vorgabe für Maße und Bild, nicht
für Code.

## Quellen (verbindlich, in dieser Reihenfolge)

| Quelle | Was | Wo |
|---|---|---|
| Design System (DS) | Tokens, Komponenten, Datenviz, Markenregeln | Artefakt `https://claude.ai/artifact/14Xq8ZVdYasy3EUQ8bLhGh`, Dateien unter `project/` (`README.md`, `tokens.json`, `tokens.css`, `components/*`, `guidelines/cards/*`, `assets/favicons/*`, `fonts/*`) |
| Anwendungsebene | Tabellen, Felder, Dialoge, Datum, Status, Zustände, Navigation, Icons, Dunkelfassung | DS-Abschnitt `project/anwendungsebene.md` (seit DS-Version 9, 2026-10-21); Ursprung `JonasPrade/ini_strategy` → `docs/design/anwendungsebene/README.md` mit den Entwurfsdateien |
| Strategie-Tool | Referenzumsetzung, besonders die Dunkelfassung | `JonasPrade/ini_strategy` → `stakeholder/static/stil.css` (Abschnitte 2–4), `app.js` („Hell- und Dunkelfassung“) |
| WordPress-Theme | zweiter Konsument derselben Tokens, kein Vorbild für Werkzeuge | `initiative-deutschlandtakt/wordpress-theme-initiative-deutschlandtakt-` |
| Dieses Dokument | Entscheidungen, Zuordnungen, Stufen | – |

Weichen DS und Anwendungsebene voneinander ab, gilt für Werkzeug-Bausteine die
Anwendungsebene. Weicht dieses Dokument von beiden ab, steht die Abweichung in
der Entscheidungstabelle mit Begründung.

## Umfang

- Frontend vollständig: Theme, Tokens, Schrift, Icons, Shell (Kopf, Fuß),
  Komponenten, Diagramme, Karte, Zustände, Dunkelfassung.
- Backend klein: Default-Farbe der Projektgruppe, vier Felder in `AppSettings`
  für Impressum und Datenschutz, Auslieferung über den bestehenden
  Settings-Endpunkt.
- Dokumentation: `docs/DESIGN.md` (neu geschrieben), READMEs, In-App-Doku.

Nicht im Umfang: Layout-Neugestaltung einzelner Seiten (wird nach der
Umstellung geprüft, eigenes Issue), Inhalte von Impressum und Datenschutz
(Human Task), Änderungen am DS-Artefakt (eigene Pflege), das WordPress-Theme.

## Entscheidungen

Alle am 2026-10-20/21 mit dem Nutzer getroffen (Grill-Runden Q1–Q33,
Widerspruchs-Check W1–W8 und fünf vorab aufgelöste Widersprüche).

| Nr. | Entscheidung |
|---|---|
| Q1 | Tiefe: Tokens **und** Komponenten-Angleichung. Seitenlayouts später. |
| Q2/Q20 | Markenauftritt: Bildmarke aus dem DS-Favicon-Set (Ink-Quadrat mit Gleisbalken) 40px plus „Schienendashboard“ in Inter 700 im Kopf; kein zusätzlicher IDT-Schriftzug im Kopf. DS-Favicon-Set ersetzt `favicon.svg`. |
| Q3 | Tokens: `tokens.css` aus dem DS verbatim vendoren, Mantine darauf abbilden. Theme-Repo bleibt unberührt. |
| Q4/Q15 | Schriftgrade nach Anwendungsebene: Grundschrift 16px, Stufen 13 / 13,5 / 14,5 / 16 / 19 / 21; DS-Display-Stufen nur für Kennzahlen. |
| Q5 | Hover nur Farbwechsel, kein Anheben; kein Blockschatten im Dashboard; Fokusring 2px Violett, 2px Abstand. |
| Q6/Q16 | Icons: `@tabler/icons-react` entfernen, `lucide-react` einführen (Tausch, keine Ergänzung). |
| Q7/Q27/Q28 | Vorgehen: diese Feature-Datei, dann vier Arbeitspakete als Issues (ein Epic, vier Teil-Issues), Umsetzung durch ein schwächeres Modell. |
| Q8/Q22/Q33 | Richtung F vollständig ablösen; `components/chronicle/*` und `components/tafel/*` werden gelöscht und durch DS-Bausteine ersetzt (Zuordnung unten). Fallblatt entfällt ersatzlos. |
| Q9 | Kein Alias-Block: alle `--bg/--ink/--led/--signal/--go/--info/--board`-Stellen werden auf DS-Namen umgeschrieben. |
| Q10 | Nur InterVariable, selbst gehostet (woff2). Google Fonts, Archivo Narrow, IBM Plex, Inter-TTF entfallen. Mono-Rolle entfällt: Versal-Etiketten in Inter mit `--ls-label`, Zahlen mit `tabular-nums`. |
| Q11/W6 | Farbzuordnungen in **einem** Modul `src/shared/theme/semanticColors.ts`; `phaseMeta.ts` re-exportiert `MAIN_PHASE_COLOR` von dort. Phasen auf der Teal-Rampe, „In Betrieb“ grün. |
| Q12 | Gruppenfarbe bleibt frei; Farbwähler bietet `chart-1…6` als Swatches; Defaults (Backend, Frontend, Projektdetail) auf `#6E50FA`; Bestandsdaten unverändert. |
| Q13 | Mantine-Standardpaletten durch DS-Skalen ersetzen; `dimmed` → `--text-muted`. Zuordnungstabellen und `--mantine-color-*`-Stellen werden auf Namen umgeschrieben, der Rest zieht über die Skalen mit. |
| Q14 | Anwendungsebene ist verbindlich; Strategie-Tool ist Referenzumsetzung. |
| Q17/Q29 | Dunkelfassung: Token des Strategie-Tools plus aufgehellte Diagrammfarben (Tabelle unten); dieselben Werte stehen seit 2026-10-21 als Theme `dark` im DS (Version 9). |
| Q18 | Dunkelfassung: Vorgabe System, Knopf im Kopf (Mond/Sonne, Wort als `aria-label`, im Mobilmenü mit Wort), Speicher-Schlüssel `schienendashboard.thema`, über Mantines `defaultColorScheme="auto"` und `useMantineColorScheme`. |
| Q19 | Karte dunkel: optionale zweite Kachel-URL `REACT_APP_TILE_LAYER_URL_DARK`, Rückfall auf die helle. |
| Q21/Q31/W8 | Schmale Fußzeile (Ink, 3px Violett-Kante, Inverse-Logo, Fassung, Links). Impressum und Datenschutz als Felder in `AppSettings` (URL oder Markdown), gepflegt in der Admin-Einstellungsmaske; URL gesetzt → Link nach außen, sonst eigene Route. Inhalte: Human Task. |
| Q23/W7 | Statusregel der Anwendungsebene: Rot nur für Überfälliges und Löschen, kein Gelb; Todo-Priorität ohne Farbe; Erfolgsmeldungen Haken statt Grün; Zähler im Kopf Ink-Rahmen auf Violett-Soft, rot nur mit Überfälligem. |
| Q24/W1 | Infraplan-Diagramm **wie heute**: Ist als Balken `chart-1`, Ziel des gewählten Jahrgangs als durchgezogene Linie `chart-2`, Ziel des Vorjahrgangs gestrichelt `chart-2`. Keine Änderung an `infraplanFormat.ts`-Logik und Test, nur Farben. |
| Q25 | Tabellenzeilen 48px über Token `--row-h`; Fünf-Spalten-Regel nicht erzwungen, aber Prüfpunkt je Tabelle. |
| Q26 | Register an der linken Kante für die Projektdetailseite ersetzt `ProjectTableOfContents`. |
| Q32 | Umbruchpunkte der Anwendungsebene (720/900px) werden auf die bestehenden 48em/62em abgebildet; kein dritter Breakpoint. |
| W2 | **Alle** Datentabellen werden unter 48em zu Karten (`ResponsiveTable`), auch breite. Oberhalb scrollen sie wie heute in ihrer Karte. |
| W3 | Mantine `Alert` wird global nach Anwendungsebene gestaltet (Rahmen, rote Innenkante, kein roter Grund); Code bleibt `<Alert color="red">`. |
| W4 | Zeitstrahl: geplanter Teil **schraffiert** in der Phasenfarbe statt heller. |
| W5 | Textkategorien: Kante in Statusfarbe (Info Cyan, Warnung Bernstein, Kritisch Rot), Icon in Ink, nur Kritisch mit rotem Icon; Kante 8px wie DS-Callout. |
| vorab | „Kein globaler Dark Mode“ (DESIGN.md §8, Feature F) → aufgehoben. „Markenteilung außerhalb Scope“ (Feature F Z. 199) → aufgehoben. „Nie eine Abhängigkeit hinzufügen“ → Tausch Tabler→Lucide. „Chronicle-Props bleiben“ → aufgehoben. |

## Stufen (vier Arbeitspakete)

Jede Stufe ist ein Issue, ein Commit-Block und ein Test-Durchlauf. Die
Reihenfolge ist fest. Zwischen den Stufen darf das Dashboard uneinheitlich
aussehen, aber `make test` bleibt grün und jede Seite bleibt bedienbar.

| Stufe | Inhalt | Ergebnis |
|---|---|---|
| 1 Fundament | Tokens, Schrift, Mantine-Theme mit DS-Skalen, CSS-Brücke, Dunkelfassung, Favicons, Icons | Alles ist umgefärbt und in Inter, Lucide statt Tabler, Dunkel-Knopf funktioniert; Chronicle-Bausteine laufen noch (auf neuen Tokens) |
| 2 Shell und Marke | Kopfzeile, Fußzeile, Impressum/Datenschutz (Backend-Felder, Routen), Register der Projektseite, Zustände (Leer/Lädt/Fehler), Loader → Skeleton | Shell fertig; alle 65 Kreisel ersetzt |
| 3 Farbzuordnungen, Diagramme, Karte | `semanticColors.ts`, Phasen/Verkehrsarten/Quellen/Todos/Textkategorien, Diagrammfarben, Karte und Gruppenfarben inkl. Backend-Default | Keine Mantine-Farbnamen mehr in Zuordnungstabellen; Diagramme in DS-Palette |
| 4 Bausteine | Mantine-Komponenten nach Anwendungsebene (Button, Felder, Tabelle, Dialog, Badge, Alert, Notifications, Tabs), Chronicle/Tafel löschen, 57 Importstellen umziehen, Tabellen-Karten, Doku-Sweep | Richtung F ist restlos weg; `grep -ri "chronicle\|tafel\|preussen\|gold\|archivo\|plex\|tabler" src` liefert nichts |

## Stufe 1 — Fundament

### Dateien

```
apps/frontend/
├── index.html                         # Google-Fonts-Links raus, theme-color #00373C, Favicon-Set
├── public/
│   ├── fonts/InterVariable.woff2      # NEU, aus DS project/fonts/ (oder Theme-Repo assets/fonts/)
│   ├── fonts/InterVariable-Italic.woff2
│   ├── fonts/inter/                   # LÖSCHEN (TTF)
│   ├── favicon.ico, favicon-16x16.png, favicon-32x32.png, apple-touch-icon.png,
│   │   android-chrome-192x192.png, android-chrome-512x512.png, site.webmanifest   # NEU aus DS project/assets/favicons/
│   ├── bildmarke.png                  # NEU = android-chrome-192x192.png (Kopfzeile)
│   ├── logo-idt-inverse.png           # NEU aus DS project/assets/ (Fußzeile)
│   └── favicon.svg                    # LÖSCHEN
└── src/
    ├── main.tsx                       # Import-Reihenfolge: @mantine/core → shared/theme/tokens.css → shared/theme/mantine-bridge.css → notifications → app.css; MantineProvider defaultColorScheme="auto", colorSchemeManager mit Schlüssel schienendashboard.thema
    ├── app.css                        # Mobil-Ebene bleibt, @font-face Inter raus (liegt in tokens.css), Header-Regeln 30em/80em raus
    ├── theme.ts                       # LÖSCHEN, ersetzt durch shared/theme/theme.ts
    ├── components/chronicle/tokens.css # LÖSCHEN in Stufe 4; in Stufe 1 nur noch Layout-Tokens (--page-pad, --card-pad, --map-height, --map-height-detail, --header-height, --row-h), alle Farben entfernt
    └── shared/theme/
        ├── tokens.css                 # DS tokens.css verbatim (Kopfkommentar: Quelle, Artefakt-Version, Datum)
        ├── mantine-bridge.css         # Mantine-CSS-Variablen auf DS-Tokens (unten)
        ├── theme.ts                   # createTheme (unten)
        └── index.ts                   # export { theme }
```

`tokens.css` enthält seit DS-Version 9 (2026-10-21) die Blöcke `:root, [data-theme="light"]`
und `[data-theme="dark"]`; die Dunkelwerte stehen zur Kontrolle auch in der Tabelle unten. Mantine setzt `data-mantine-color-scheme`, nicht
`data-theme`; `mantine-bridge.css` übersetzt:

```css
/* mantine-bridge.css */
:root[data-mantine-color-scheme="dark"] { color-scheme: dark; }
/* Die DS-Dunkelwerte gelten unter [data-theme="dark"]. Der Provider setzt
   zusätzlich data-theme am <html>, siehe main.tsx (useEffect auf colorScheme). */
:root {
  --mantine-color-body: var(--surface);
  --mantine-color-text: var(--text-body);
  --mantine-color-dimmed: var(--text-muted);
  --mantine-color-default-border: var(--border);
  --mantine-color-default: var(--surface);
  --mantine-color-default-hover: var(--surface-alt);
  --mantine-color-anchor: var(--text-link);
  --mantine-color-placeholder: var(--text-muted);
  --mantine-color-error: var(--idt-danger);
  --mantine-primary-color-filled: var(--accent-primary);
  --mantine-primary-color-filled-hover: var(--accent-primary-hover);
  --mantine-primary-color-light: var(--idt-violet-soft);
  --mantine-primary-color-light-color: var(--accent-primary-hover);
  --mantine-radius-default: 0;
  --mantine-shadow-xs: var(--shadow-sm); --mantine-shadow-sm: var(--shadow-sm);
  --mantine-shadow-md: var(--shadow-md); --mantine-shadow-lg: var(--shadow-lg); --mantine-shadow-xl: var(--shadow-lg);
  --mantine-font-family: var(--font-sans);
  --mantine-font-family-headings: var(--font-display);
  --mantine-font-family-monospace: var(--font-sans);
}
```

Weicht die vendorte `tokens.css` von der Tabelle „Dunkelfassung“ ab, gilt das DS;
die Tabelle wird dann nachgezogen, nicht umgekehrt.

### Mantine-Theme (`shared/theme/theme.ts`)

Skalen: Index 0 hellste, 9 dunkelste; `primaryShade: 6`. Werte sind aus den
DS-Farben gemischt (Papier nach oben, `#001A1D` nach unten) und so belegt, dass
die DS-Token an den Stellen liegen, die Mantine benutzt (6 = filled, 0 = light,
7/8 = hover/active).

```ts
import { createTheme, Container, rem } from "@mantine/core";

const violet = ["#e8e3ff","#d8caf3","#c3b1f4","#ae99f6","#9981f7","#8368f9","#6e50fa","#5a3de6","#4a2fcc","#1c2854"];
const cyan   = ["#d6f8ff","#bbe1e3","#96d5db","#70c9d4","#00dcfa","#25b2c5","#00a6be","#008396","#00606e","#003d45"];
const teal   = ["#efeae5","#cacecc","#aeb8b8","#91a2a4","#748c90","#57767c","#3a6068","#2c4e55","#00373c","#002326"];
const gray   = ["#fbede6","#f3e2da","#e2d3cb","#c9b6ac","#a89a92","#7d7470","#585857","#3a6068","#00373c","#002326"];
const red    = ["#fce8e2","#f4c7c2","#eeada9","#e89390","#e27977","#dc5f5e","#d64545","#a03a3b","#6b3031","#362527"];
const green  = ["#edede4","#c3d9c8","#a2c9b2","#82ba9d","#61aa87","#409a71","#1f8a5b","#176e4c","#10523c","#08362c"];
const amber  = ["#f7ebdd","#e4d1b0","#d5bd8d","#c6a86a","#e8a100","#a97f23","#9a6b00","#745707","#4d420e","#262e16"];

export const theme = createTheme({
  primaryColor: "violet",
  primaryShade: 6,
  autoContrast: true,          // Papier- oder Ink-Schrift je Fläche (Cyan bekommt Ink)
  luminanceThreshold: 0.35,
  defaultRadius: 0,
  radius: { xs: "0", sm: "0", md: "0", lg: "0", xl: "0" },
  colors: {
    violet, cyan, teal, gray, red, green,
    // Mantine-Standardnamen, die im Code vorkommen, auf DS-Skalen legen:
    blue: teal, indigo: violet, grape: violet, pink: red, orange: amber, yellow: amber,
    lime: green, dark: teal,
  },
  black: "#00373c",
  white: "#fff6f0",
  fontFamily: "'InterVariable', 'Inter', system-ui, sans-serif",
  fontFamilyMonospace: "'InterVariable', 'Inter', system-ui, sans-serif",
  fontSizes: { xs: rem(13), sm: rem(13.5), md: rem(16), lg: rem(19), xl: rem(21) },
  lineHeights: { xs: "1.4", sm: "1.45", md: "1.5", lg: "1.3", xl: "1.2" },
  headings: {
    fontFamily: "'InterVariable', 'Inter', system-ui, sans-serif",
    fontWeight: "700",
    sizes: {
      h1: { fontSize: rem(21), lineHeight: "1.2" },   // Ansichtstitel
      h2: { fontSize: rem(19), lineHeight: "1.25" },  // Abschnitt (mit 2px-Ink-Linie, s. Stufe 4)
      h3: { fontSize: rem(17), lineHeight: "1.3" },
      h4: { fontSize: rem(16), lineHeight: "1.4" },
    },
  },
  spacing: { xs: rem(4), sm: rem(8), md: rem(16), lg: rem(24), xl: rem(32) },
  components: {
    Container: Container.extend({ defaultProps: { px: "var(--page-pad)", size: 1400 } }),
    // Komponenten-Regeln kommen in Stufe 4 (Tabelle dort).
  },
});
```

Der „Nebentext“ 14,5px hat keine Mantine-Stufe: Tabellen und Karten-Paare setzen
`fz={rem(14.5)}` bzw. die Klasse `.idt-neben` aus `app.css`.

### Dunkelfassung

**Umgesetzt (Stufe 1):** Das veröffentlichte `tokens.css` des DS (Version 9) enthält keinen
`[data-theme="dark"]`-Block, obwohl `tokens.json` das Theme `dark` führt (#224). Der Block am
Ende der vendorten `tokens.css` ist deshalb aus `tokens.json` erzeugt und entfällt, sobald das
DS ihn ausliefert. Ein Inline-Skript in `index.html` setzt `data-theme` vor dem ersten Paint
(liest `localStorage` `schienendashboard.thema`, sonst `prefers-color-scheme`), damit es kein
Aufblitzen gibt; `ThemeAttributeSync` hält das Attribut danach mit Mantine synchron.

Mechanik: `MantineProvider defaultColorScheme="auto"` mit
`localStorageColorSchemeManager({ key: "schienendashboard.thema" })`. Ein
`useEffect` in `main.tsx` spiegelt das berechnete Schema
(`useComputedColorScheme`) nach `document.documentElement.dataset.theme`
(`"light"`/`"dark"`), damit die DS-Tokens greifen. Knopf im Kopf: Lucide `moon`
wenn hell, `sun` wenn dunkel; `aria-label` und `title` „Dunkelfassung
einschalten“ / „Hellfassung einschalten“; im Mobilmenü mit sichtbarem Wort.

Werte (Theme `dark`; alles, was hier nicht steht, bleibt wie hell):

| Token | hell | dunkel |
|---|---|---|
| `--surface` | `#fff6f0` | `#00373c` |
| `--surface-alt` | `#fbede6` | `#002a2e` |
| `--surface-sunken` | `#f3e2da` | `#002326` |
| `--surface-inverse` | `#00373c` | `#fff6f0` |
| `--surface-card` | `#fff6f0` | `#00373c` |
| `--text-strong`, `--text-body` | `#00373c` | `#fff6f0` |
| `--text-muted` | `#585857` | `#8fb4bc` |
| `--text-faint` | `#6e9097` | `#6e9097` |
| `--text-on-inverse` | `#fff6f0` | `#00373c` |
| `--text-on-inverse-muted` | `#8fb4bc` | `#585857` |
| `--text-on-accent` | `#fff6f0` | `#00373c` |
| `--text-link` | `#6e50fa` | `#ad9bff` |
| `--border` | `#e2d3cb` | `#295659` |
| `--border-strong` | `#c9b6ac` | `#4c7072` |
| `--border-frame` | `#00373c` | `#8ca09f` |
| `--accent-primary` / `-hover` / `-active` | `#6e50fa` / `#5a3de6` / `#4a2fcc` | `#ad9bff` / `#c7bcff` / `#9684f5` |
| `--focus-ring` | `#6e50fa` | `#ad9bff` |
| `--idt-violet-soft` / `--idt-cyan-soft` / `--idt-yellow-soft` | `#e8e3ff` / `#d6f8ff` / `#fffddb` | `#1d485d` / `#00535c` / `#2b594b` |
| `--idt-success` / `--idt-danger` | `#1f8a5b` / `#d64545` | `#4fbf8b` / `#f08585` |
| `--idt-chart-1…6` | `#6e50fa` `#00dcfa` `#00373c` `#3a6068` `#b3a6ff` `#7fe9fb` | `#ad9bff` `#00dcfa` `#fff6f0` `#8fb4bc` `#d8d0ff` `#c4f5fd` |
| `--idt-seq-1…5` | `#d3e7e8` `#a8c7c9` `#6e9097` `#3a6068` `#00373c` | `#2e6670` `#4c7f88` `#6e9097` `#a8c7c9` `#d3e7e8` |
| `--idt-diverge-neg` / `-mid` / `-pos` | `#d64545` / `#e2d3cb` / `#1f8a5b` | `#f08585` / `#4c7072` / `#4fbf8b` |
| `--idt-highlight-line` | `#00373c` | `#fff6f0` |
| `--idt-chart-grid` / `-axis` / `-track` | `#e2d3cb` / `#6e9097` / `#fbede6` | `#215053` / `#8fb4bc` / `#0b4650` |
| `--shadow-sm` / `-md` / `-lg` | wie DS | `0 1px 2px rgba(0,0,0,.40)` / `0 4px 16px rgba(0,0,0,.45)` / `0 12px 40px rgba(0,0,0,.55)` |
| `--shadow-block` / `-sm` | `… #00373c` | `6px 6px 0 #001a1d` / `4px 4px 0 #001a1d` |

Mantine-Skalen in der Dunkelfassung: Mantine liest für `dark` die Skala
`dark` (hier `teal`) für Flächen; Flächen und Text kommen aber über die Brücke
aus den DS-Aliassen, deshalb genügt die Brücke. Prüfen: `Button variant="filled"`
in Violett muss in dunkel `#ad9bff` mit Ink-Schrift sein — dafür
`--mantine-primary-color-filled` in der Brücke, nicht die Skala.

Logo in der Fußzeile ist auf beiden Fassungen die Inverse-Variante (Ink-Grund).
Bildmarke im Kopf (Ink-Quadrat) wirkt auf beiden Fassungen.

Karte: `REACT_APP_TILE_LAYER_URL_DARK` (optional, `.env.example`,
`.env.prod.example`, `docs/environment.md`, Dockerfile-ARG, `release.yml`
build_args, `compose.override.yaml`). Gesetzt → MapLibre tauscht die
Rasterquelle beim Schemawechsel; sonst bleibt die helle Karte, im 2px-Rahmen.

### Schrift

`tokens.css` des DS bringt die `@font-face`-Regeln mit `url('fonts/InterVariable.woff2')`
mit; der Pfad ist relativ zur CSS-Datei. Zwei Wege, einer wird gewählt und im
Kopfkommentar von `tokens.css` notiert: (a) die beiden woff2 nach
`src/shared/theme/fonts/` legen (Vite bündelt sie), (b) die `@font-face`-Zeilen in
`app.css` mit `/fonts/…` schreiben und in `tokens.css` entfernen. Empfohlen (a).
`index.html`: alle `fonts.googleapis.com`/`gstatic`-Links und Preloads
entfernen; `<link rel="preload" as="font" href="…InterVariable.woff2" crossorigin>`.

### Icons (Tabler → Lucide)

`npm remove @tabler/icons-react && npm install lucide-react@<aktuelle Version, mindestens zwei Wochen alt>`.
Lucide-Komponenten heißen `PascalCase` ohne Präfix; Größe über `size`, Strich
immer 2 (`strokeWidth` nicht setzen), Farbe `currentColor`.

| Tabler (Fundstellen) | Lucide |
|---|---|
| `IconTrash` (18) | `Trash2` |
| `IconPlus` (17) | `Plus` |
| `IconSearch` (10) | `Search` |
| `IconPencil` (10) | `Pencil` |
| `IconChevronRight` / `Left` / `Down` (10/10/2) | `ChevronRight` / `ChevronLeft` / `ChevronDown` |
| `IconRefresh` (8) | `RefreshCw` |
| `IconExternalLink` (6) | `ExternalLink` |
| `IconInfoCircle` (5) | `Info` |
| `IconDotsVertical` (4) | `EllipsisVertical` |
| `IconChecks` (4) | `CheckCheck` |
| `IconTaskAdd` (2) | `ListPlus` |
| `IconRoute` (2) | `Route` |
| `IconPlayerPause` (2) | `Pause` |
| `IconMenu` (2) | `Menu` |
| `IconMap` (2) | `Map` |
| `IconLock` (2) | `Lock` |
| `IconHelp` (2) | `CircleHelp` |
| `IconFlag` (2) | `Flag` |
| `IconEye` (2) | `Eye` |
| `IconClose` (2) | `X` |
| `IconClockHour4` (2) | `Clock` |
| `IconCheck` (2) | `Check` |
| `IconCalendarEvent` (2) | `Calendar` |
| `IconBan` (2) | `Ban` |
| `IconArrowLeft` (2) | `ArrowLeft` |
| `IconAdjustments` (2) | `SlidersHorizontal` |
| neu | `Moon`, `Sun` (Dunkel-Knopf), `Filter` (Filterleiste), `ArrowUp`/`ArrowDown` (Sortierpfeil), `Download` (CSV), `TriangleAlert`, `OctagonAlert`, `FileText` (Textkategorien) |

Größen: 16px in Zeilen und Feldern, 20px in Leisten, 22–26px als Merkzeichen.

### Test-Checkliste Stufe 1 (Issue-Kommentar, `Needs User Test`)

- [ ] `/` öffnen: Grund ist Papier `#FFF6F0`, Schrift Inter, keine Google-Fonts-Anfrage im Netzwerk-Tab.
- [ ] Browser-Tab zeigt das IDT-Favicon (Gleisbalken auf Ink).
- [ ] Knopf im Kopf: Mond anklicken → Grund wird Ink `#00373C`, Schrift Papier, Knopf zeigt Sonne; Seite neu laden → bleibt dunkel; Sonne anklicken → wieder hell.
- [ ] Systemeinstellung „Dunkel“ ohne gespeicherte Wahl (`localStorage` leeren) → Dashboard startet dunkel.
- [ ] Ein beliebiger Primär-Knopf (z. B. „Speichern“ in `/admin/projects/new`): Violett mit Papier-Schrift; im Dunkeln `#ad9bff` mit Ink-Schrift.
- [ ] Alle Icons sind Linienzeichen in Ink; keine Konsolenfehler „Icon… is not exported“.
- [ ] `npm run lint`, `npm test`, `npm run build` grün; `make test` grün.

## Stufe 2 — Shell, Marke, Zustände

### Kopfzeile (`components/Header.tsx`)

- `AppShell header={{ height: 72 }}`, Token `--header-height: 72px` (mobil 64px).
- Grund `--surface`, `border-bottom: 2px solid var(--border-frame)`; kein Blur,
  keine Transparenz.
- Links `<a href="/">` mit `<img src="/bildmarke.png" width=40 height=40 alt="">`
  und „Schienendashboard“ (19px/700, `letter-spacing: -0.015em`). Unter 48em
  36px und 17px.
- Navigation: Textlinks 15px/600 in `--text-strong`, `padding 0 12px`, aktiver
  Punkt `border-bottom: 3px solid var(--accent-primary)` (über die ganze
  Kopfhöhe, Linie bündig mit der Kopfunterkante). Zähler (W7): `<span>` mit
  `border: 1px solid var(--border-frame)`, Grund `--idt-violet-soft`, 13px,
  `tabular-nums`; enthält die Liste Überfälliges → `border-color`/Farbe
  `--idt-danger`, Gewicht 700, Grund bleibt. Bisheriger roter Zähler entfällt.
- Rechts: Dunkel-Knopf (`ActionIcon variant="default"`, 40px), unter 62em
  zusätzlich Burger (Lucide `Menu`) → Drawer wie heute. Die CSS-Regeln in
  `app.css` zu 30em/80em (Wordmark-Ausblendung) entfallen.
- `Signet.tsx`, `Wordmark.tsx` werden gelöscht (Stufe 2, nicht erst 4).

### Fußzeile (neu `components/Footer.tsx`, `AppShell.Footer` oder nach dem `Outlet`)

- Grund `--idt-ink`, `border-top: 3px solid var(--idt-violet)`, Höhe mind.
  56px, `padding 0 var(--page-pad)`, Schrift 13,5px `--text-on-inverse-muted`.
- Links: `<img src="/logo-idt-inverse.png" height=26 alt="Initiative Deutschlandtakt">`,
  „Schienendashboard · Fassung `<version>`“. Version: Vite `define`
  `__APP_VERSION__` aus `VITE_APP_VERSION`; `release.yml` übergibt den kurzen
  Commit-SHA als build_arg, lokal „dev“. Deploy-relevante Doku nachziehen
  (`CHANGELOG.md`, `DEPLOY.md`, `docs/production_setup.md`).
- Rechts: Links „Impressum“, „Datenschutz“, „Dokumentation“ in `--idt-paper`
  600. Unter 48em umbrechend.
- Fußzeile ist Teil des `Layout`, erscheint auf jeder Route; `RouteErrorBoundary`
  bekommt sie ebenfalls (heute ohne Kopf und Fuß).

### Impressum und Datenschutz (W8)

Backend (Expand-Migration über `make migrate-create MSG="legal pages in app settings"`):

```python
# models/app_settings.py — vier Null-Spalten
impressum_url = Column(String(500), nullable=True)
impressum_markdown = Column(Text, nullable=True)
datenschutz_url = Column(String(500), nullable=True)
datenschutz_markdown = Column(Text, nullable=True)
```

Schema `AppSettingsRead`/`AppSettingsUpdate` um die vier Felder erweitern;
`GET /api/v1/settings/` liefert sie öffentlich, `PATCH` wie heute hinter
`settings.manage`. `make gen-api`.

Frontend: Admin-Maske (dort, wo `map_group_mode` gepflegt wird,
`ProjectGroupsAdminPage.tsx` → Abschnitt „Einstellungen“ oder eigene Karte auf
`/admin`) mit vier Feldern (URL, Markdown je Seite; Hinweis „URL gesetzt →
Weiterleitung, sonst eigene Seite“). Routen `/impressum` und `/datenschutz`:
rendern den Markdown (`react-markdown` ist vorhanden) als Seite mit
Ansichtstitel; ist nur die URL gesetzt, zeigt die Fußzeile einen externen Link
und die Route leitet per `window.location.replace` weiter. Sind beide leer,
zeigt die Seite den Leer-Zustand „Noch kein Impressum hinterlegt“ mit Link auf
die Admin-Maske (nur für `settings.manage`). Inhalt: **Human Task**.

### Register der Projektseite (Q26, ersetzt `ProjectTableOfContents.tsx`)

- Ab 62em: Spalte 240px links des Inhalts, `position: sticky; top: calc(var(--header-height) + 24px)`,
  2px-Ink-Rahmen; Kopfzeile „ABSCHNITTE“ (Versal-Etikett) mit Klappsymbol;
  Einträge 14,5px/500, Haarlinie dazwischen, aktiver Eintrag
  `border-left: 3px solid var(--accent-primary)`, 700. Geschlossen: 26px
  schmale Lasche in Ink mit senkrechter Beschriftung „Abschnitte“; Zustand in
  `localStorage` (`schienendashboard.register`).
- Unter 62em: Knopf am unteren Rand (`position: fixed`, Ink, 44px, Lucide
  `Menu` + „Abschnitte“), öffnet dasselbe Register als Drawer von unten.
- Aktiver Abschnitt per `IntersectionObserver` wie heute.

### Zustände (Anwendungsebene) — `src/shared/ui/`

| Baustein | Datei | Regel |
|---|---|---|
| `Leer` | `EmptyState.tsx` | 2px-Rahmen, Überschrift 17/700, ein Satz, eine Aktion (Button outline) |
| `Lädt` | `LoadingState.tsx` | Mantine `Skeleton` mit `radius=0`, Balken 13px in `--surface-sunken`, `animate={false}`; Varianten `rows` (n Zeilen) und `block` (Höhe) |
| `Fehler` | `ErrorState.tsx` | 2px-Rahmen, `box-shadow: inset 4px 0 0 var(--idt-danger)`, Überschrift, Satz, Knopf „Erneut versuchen“ (`onRetry` → React-Query `refetch`) |
| Rückmeldung im Kopf | `SaveStatus.tsx` | 2px-Rahmen, 15px, Haken + „gespeichert HH:MM“ / „schreibt …“ / rote Innenkante „nicht gespeichert“ + „erneut“ |

Alle 65 `<Loader>`-Stellen werden durch `LoadingState` (im Inhalt) ersetzt; der
Suspense-Fallback in `router.tsx` wird `LoadingState rows={6}`. Mantine
`Loader` bleibt nur in Buttons (`loading` Prop), dort als kleiner Kreisel
zulässig.

### Test-Checkliste Stufe 2

- [ ] Kopf 72px hoch, Papier, 2px Ink-Linie unten, Bildmarke links, „Schienendashboard“ daneben, aktiver Menüpunkt mit violetter Unterkante.
- [ ] „Aufgaben“ zeigt den Zähler im Ink-Rahmen auf Violett-Soft; eine Aufgabe überfällig stellen → Zähler rot gerahmt, fett.
- [ ] Fußzeile auf jeder Seite (auch `/nicht-vorhanden`): Ink mit violetter Kante, Inverse-Logo, Fassung, drei Links.
- [ ] Admin → Einstellungen: Impressum-URL eintragen → Fußzeilen-Link führt nach außen; URL leeren, Markdown eintragen → `/impressum` zeigt den Text; beides leer → Leer-Zustand mit Hinweis.
- [ ] `/projects/:id` ab 992px: Register links, aktiver Abschnitt beim Scrollen mit violetter Kante; Lasche schließen/öffnen, Zustand nach Neuladen erhalten.
- [ ] `/projects/:id` auf 390px: Knopf „Abschnitte“ unten, öffnet Register als Blatt.
- [ ] Netzwerk drosseln, `/` laden: Platzhalterbalken statt Kreisel; Backend stoppen → Fehlerzustand mit roter Innenkante und „Erneut versuchen“.

## Stufe 3 — Farbzuordnungen, Diagramme, Karte

### `src/shared/theme/semanticColors.ts` (W6)

```ts
// Jede Zuordnung von Fachbegriff zu Farbe steht hier. Werte sind CSS-Variablen
// aus tokens.css, damit die Dunkelfassung greift. Keine Mantine-Farbnamen.
export const PHASE_COLOR = {
  NICHT_GESTARTET: "var(--idt-seq-1)",
  VORPLANUNG: "var(--idt-seq-2)",
  GENEHMIGUNGSPLANUNG: "var(--idt-seq-3)",
  BAU: "var(--idt-seq-4)",
  IN_BETRIEB: "var(--idt-success)",
  UNBEKANNT: "var(--idt-line-strong)",
} as const;
export const TRAFFIC_COLOR = { FERNVERKEHR: "var(--idt-chart-1)", NAHVERKEHR: "var(--idt-chart-2)", GUETERVERKEHR: "var(--idt-chart-3)" } as const;
export const FORECAST_SOURCE_COLOR = { "VIB-PFA": "var(--idt-chart-1)", "Fulda-Runde": "var(--idt-chart-2)", BVWP: "var(--idt-chart-3)", "Schätzung": "var(--idt-chart-4)" } as const;
export const LANE_STATE_COLOR = { idle: "var(--idt-line-strong)", active: "var(--accent-primary)", done: "var(--idt-success)" } as const;
export const TODO_STATUS_STYLE = {  // Anwendungsebene: nur Rot trägt Farbe
  OPEN: { color: "var(--text-muted)", weight: 400 },
  IN_PROGRESS: { color: "var(--text-strong)", weight: 400 },
  DONE: { color: "var(--text-muted)", weight: 400, check: true },
  OVERDUE: { color: "var(--text-strong)", weight: 700, underline: "var(--idt-danger)" },
} as const;
export const TEXT_CATEGORY_STYLE = {  // W5
  neutral: { edge: null, icon: "FileText", iconColor: "var(--text-muted)" },
  info: { edge: "var(--idt-cyan)", icon: "Info", iconColor: "var(--text-strong)" },
  warning: { edge: "var(--idt-warning)", icon: "TriangleAlert", iconColor: "var(--text-strong)" },
  critical: { edge: "var(--idt-danger)", icon: "OctagonAlert", iconColor: "var(--idt-danger)" },
} as const;
export const CHART_SERIES = ["var(--idt-chart-1)", "var(--idt-chart-2)", "var(--idt-chart-3)", "var(--idt-chart-4)", "var(--idt-chart-5)", "var(--idt-chart-6)"] as const;
export const CHART_FURNITURE = { grid: "var(--idt-chart-grid)", axis: "var(--idt-chart-axis)", track: "var(--idt-chart-track)" } as const;
export const MAP_COLOR = { default: "#6E50FA", selected: "#6E50FA", alternative: "#00DCFA", constituency: "#00373C", stroke: "#FFF6F0" } as const; // Karte braucht Hex (MapLibre kennt keine CSS-Variablen)
export const GROUP_COLOR_SWATCHES = ["#6E50FA", "#00DCFA", "#00373C", "#3A6068", "#B3A6FF", "#7FE9FB"] as const;
```

Konsumenten (alle umstellen, Mantine-Farbnamen dort entfernen):
`phaseMeta.ts` (re-export `MAIN_PHASE_COLOR = PHASE_COLOR`), `PhaseBadge.tsx`,
`SubprojectsTable.tsx`, `BauportalImportPage.tsx`, `TimelineView.tsx`,
`PhaseStepper.tsx`, `ProgressMini.tsx` (`--ledOk`-Bug verschwindet damit),
`ParallelLanes.tsx`, `ForecastPanel.tsx`, `textCategoryStyles.ts` (Tokens
`--text-cat-*` entfallen, Test anpassen), `projectFeatureConfig.ts`,
`todoConstants.ts`, `ChronicleDataChip.tsx` (bis Stufe 4), `MapView.tsx`,
`MapPage.tsx`, `ProjectDetail.tsx` (`MAP_COLOR`), `GeometryPreviewMap.tsx`,
`LazyMapView.tsx`, `ProjectGroupFormModal.tsx`.

`@mantine/charts` nimmt `color` als CSS-Wert; `var(--idt-chart-1)` funktioniert
direkt. Recharts-SVG-Attribute (`stroke`, `fill`) ebenfalls.

### Diagramme

| Stelle | Regel |
|---|---|
| `FinveBudgetDetails.tsx` `SERIE_COLORS` | `CHART_SERIES` (6 statt 10; mehr als 6 Reihen → Rest in `--idt-seq-3`, Legende nennt „weitere“) |
| `FinveBudgetDetails.tsx` `LineChart color="green.6"` | `var(--idt-chart-1)` |
| `GvfgSection.tsx` `teal.6`/`blue.6` | `chart-1`/`chart-2` |
| `infraplanFormat.ts` `IST_COLORS`/`ZIEL_COLORS` | Ist `chart-1` (Balken), Ziel aktueller Jahrgang `chart-2` durchgezogen, Vorjahrgang `chart-2` gestrichelt (W1: Logik und Test bleiben) |
| Gitter, Achsen | `CHART_FURNITURE`; Achsenschrift 12,5px `--idt-chart-axis`, `tabular-nums` |
| `ChartLegend` | quadratische Swatches 12px (kein `ColorSwatch`-Kreis), 13,5px |
| Tooltip | Papier, 2px Ink-Rahmen, kein Schatten, Radius 0 |
| Zeitstrahl `TimelineView.tsx` (W4) | Segmente `PHASE_COLOR`; geplanter Teil (nach heute) als Schraffur `repeating-linear-gradient(135deg, <farbe> 0 4px, transparent 4px 8px)`; Etappenpause gestrichelt in `seq-4`; Inbetriebnahme-Punkt `--idt-success` (kantig, 10px); Rauten und hohle Punkte in Ink. Datumsqualifikation (2026-10-22): Jahr = weiche Kante (`mask-image`-Verlauf), Untergrenze = offener Bereich als blasse Schraffur (`color-mix` 45 %) mit Pfeil, Annahme = gestrichelter Rahmen in Ink (`timelineStyles.ts`) — bewusst verschieden von der dünnen Etappenpause (W3) |
| Gelb | nie als Datenreihe; die eine Hervorhebungszahl je Ansicht darf `--idt-highlight` mit Ink-Kontur tragen |

### Karte

- Basiskacheln unverändert (hell), dunkle Variante nur über `REACT_APP_TILE_LAYER_URL_DARK`.
- Linien/Punkte: `["coalesce", ["get","groupColor"], MAP_COLOR.default]`;
  Punktkontur `MAP_COLOR.stroke`; Hover: Linienbreite 4 → 8 wie heute.
- Wahlkreise: Fläche `#00373C` bei 8 % Deckkraft, Kontur `#00373C` 1px.
- Geometrie-Vorschau: gewählt `MAP_COLOR.selected` 5px, Alternativen
  `MAP_COLOR.alternative` gestrichelt, Fehler/Löschen `#D64545`.
- Platzhalter ohne Kachel-URL: `--surface-sunken`.
- Kartenrahmen: 2px Ink (Karte „im Rahmen“), Radius 0; Bedienelemente der
  Karte (`MapControls`) als gerahmte Knöpfe 40px.

### Gruppenfarben (Q12)

- Backend `project_group.py`: `default="#6E50FA"`; Schema-Defaults
  `project_group_schema.py` ebenso; MCP `create_project_group` Default ebenso.
  Kein DDL nötig (nur ORM-Default), Bestand bleibt; Hinweis in `CHANGELOG.md`.
- Frontend `ProjectGroupFormModal.tsx`: `ColorInput` mit `swatches={GROUP_COLOR_SWATCHES}`,
  `swatchesPerRow=6`, Default `#6E50FA`; freie Eingabe bleibt.
- `MapPage.tsx` `DEFAULT_GROUP_COLOR`, `ProjectDetail.tsx` `MAP_COLOR` → `MAP_COLOR.default`.

### Test-Checkliste Stufe 3

- [ ] Projektliste: Phasen-Tags zeigen das Teal-Quadrat (hell → dunkel von „Nicht gestartet“ bis „Bau“), „In Betrieb“ grün.
- [ ] Zeitstrahl: vergangener Teil voll, geplanter Teil schraffiert; im Dunkeln lesbar.
- [ ] `/infraplan`: Ist-Balken violett, Ziel-Linie cyan durchgezogen, Vorjahres-Ziel cyan gestrichelt; Legende quadratisch.
- [ ] FinVe-Donut: höchstens sechs Farben aus der DS-Palette.
- [ ] Karte: Projekte ohne Gruppenfarbe violett, Wahlkreise Ink-Schraffur, Auswahl in der Geometrie-Vorschau violett, Alternativen cyan gestrichelt.
- [ ] Admin → Projektgruppen → Neu: Farbwähler zeigt sechs Swatches, Vorgabe violett; eine Gruppe mit alter Farbe `#FF0000` behält sie.
- [ ] Aufgaben: überfällige Aufgabe fett mit roter Unterkante, erledigte gedämpft mit Haken, Priorität ohne Farbe.
- [ ] Projekttexte: Hinweis mit Cyan-Kante und Ink-Icon, Warnung Bernstein, Kritisch rot mit rotem Icon, Neutral ohne Kante.

## Stufe 4 — Bausteine, Tabellen, Dialoge, Sweep

### Mantine-Komponenten (`theme.ts` → `components`)

Alle Werte aus der Anwendungsebene. Umsetzung über `Component.extend({ defaultProps, classNames, vars })`
und eine Datei `src/shared/theme/components.css` mit den Klassen (keine CSS-Module,
eine Datei). Radius überall 0.

| Komponente | Regel |
|---|---|
| `Button` | Höhe 40px (`--h-bedien`, mobil 44), 14,5px/600, `padding 0 16px`, Rahmen 2px. `filled` (bestätigend): Fläche `--accent-primary`, Schrift `--text-on-accent`, Hover `--accent-primary-hover`; `default`/`outline` (abbrechend, sekundär): transparent, Rahmen `--border-frame`, Schrift `--text-strong`, Hover Grund `--surface-alt`; `subtle`: ohne Rahmen; `color="red" variant="outline"` (Entfernen in Leisten): Rahmen und Schrift `--idt-danger`; `color="red" variant="filled"` (nur im Lösch-Dialog): Fläche `--idt-danger`. Kein `transform` bei Hover. `size="compact-sm"` → 34px (Auswahlleiste). Deaktiviert: Deckkraft .45. |
| `ActionIcon` | wie `Button` `default`, 40px quadratisch, Icon 20px |
| `TextInput`, `Textarea`, `NumberInput`, `Select`, `MultiSelect`, `DateInput`, `PasswordInput` | Rahmen 2px `--border-frame`, Grund `--surface`, `padding 8px 11px`, 16px; Fokus: Rahmen `--focus-ring` + `outline: 2px solid var(--focus-ring); outline-offset: 2px`; Fehler: Rahmen `--idt-danger`; gesperrt: Rahmen `--border-strong`, Grund `--surface-sunken`, Schrift `--text-muted`; Label 13,5px/600; Beschreibung/Hinweis 13px `--text-muted`. Dropdown: 2px `--focus-ring` ohne Oberkante, Einträge mit Haarlinie, gewählter Eintrag `--idt-violet-soft` mit Haken rechts, kein Schatten. Marken in `MultiSelect`: kantig, 1px Ink, 14,5px/600. |
| `Checkbox` | 18px, 2px `--border-frame` auf `--surface`; an: Fläche `--accent-primary`, weißer Haken; Fokus wie Felder |
| `Switch`, `Radio`, `SegmentedControl` | Radius 0, aktive Fläche `--accent-primary`; `SegmentedControl` als 2px-Rahmen mit Ink-Trennern (Karte/Liste/Zeitstrahl) |
| `Table` | Kopf 13,5px/600 `--text-muted`, `border-bottom: 2px solid var(--border-frame)`; sortierte Spalte 700 `--text-strong`, Pfeil inline (`display:inline-block; vertical-align:-2px; margin-left:6px`), `white-space: nowrap`; Zeilen `--row-h` (48px) mit `border-bottom: 1px solid var(--border)`, kein Zebra, keine Zellrahmen, Hover Grund `--surface-alt`; Zahlen `.num` rechts `tabular-nums`; Kästchenspalte `width:1px; padding:15px 0 15px 16px`, angekreuzte Zeile Grund `--surface-alt` + `box-shadow: inset 3px 0 0 var(--border-frame)` auf der Kästchenzelle; äußerer Rahmen 2px Ink |
| `ResponsiveTable` (W2) | ab 48em wie heute (`ScrollContainer`); unter 48em **Karten**: jede Zeile ein 2px-Rahmen, die erste Zelle als Überschrift 17/700 (Kästchen davor), übrige Zellen als Paare Etikett (aus `<th>`-Text, 13,5/600 muted) links / Wert rechts, Status-Zelle allein in der Fußzeile über einer Haarlinie, Sortierung als Zeile über der Liste. Umsetzung generisch: `ResponsiveTable` liest die Kopfzeile aus `Table.Thead` und schreibt `data-label` in die `Td`; CSS `display:block`-Regeln in `components.css`. Bei Tabellen mit mehr als fünf Inhaltsspalten gilt das genauso (Entscheidung W2). |
| `Modal` (Dialog) | Abdunklung `rgba(0,55,60,.32)`; Fläche `--surface`, 2px `--border-frame`, `box-shadow: 8px 8px 0 rgba(0,55,60,.18)`, Radius 0; Kopf: Titel 19/700, Kreuz rechts, 2px Ink-Linie darunter; Fuß: 2px Ink-Linie darüber, Aktionen rechts, höchstens zwei (bestätigend `filled`, abbrechend `default`, löschend `color="red" filled` **statt** der bestätigenden); unter 48em Vollbild mit festem Kopf und Fuß, Rumpf scrollt, Aktionen volle Breite 46px |
| `Drawer` | wie Modal ohne Schatten; mobil 100 % |
| `Alert` (W3) | 2px `--border-frame`, Grund `--surface`, `box-shadow: inset 4px 0 0 var(--idt-danger)` für `color="red"`, Bernstein-Kante für `yellow`/`orange`, Cyan-Kante für `blue`/`cyan`, keine Kante sonst; Titel 17/700, Text 14,5; Icon in Ink (rot nur bei `red`) |
| `Badge` (Tag) | 22px hoch, 11,5px/600 Versalien `letter-spacing .06em`, Radius 0, 1px Rahmen; `variant="outline"` = Rahmen Ink, Schrift Ink; `variant="light"` = Tint-Grund (`--idt-violet-soft`/`--idt-cyan-soft`) mit farbigem Rahmen; `variant="filled"` = Fläche in der Farbe mit Papier- oder Ink-Schrift (`autoContrast`); optionales Quadrat 9px links (Phasen) |
| `Notifications` | Papier, 2px Ink-Rahmen, Radius 0, kein Schatten, `color="green"` → Haken-Icon in Ink **ohne** grüne Fläche; `color="red"` → rote Innenkante 4px |
| `Tabs` | Reiter 15px/600, aktiver Reiter `border-bottom: 3px solid var(--accent-primary)`, Liste mit 2px Ink-Linie unten |
| `Paper`/`Card` | `withBorder` → 1px `--border` + `--shadow-sm` (DS `soft`); Klasse `.karte--frame` → 2px Ink ohne Schatten; `.karte--inverse` → Ink-Grund, Papier-Text (Ersatz für `tone="board"`); farbige Oberkante 6px per `--card-accent` (Ersatz für `accent`) |
| `Title`/Abschnitt | `h2` als Abschnittstitel mit `padding-bottom: 8px; border-bottom: 2px solid var(--border-frame)`; Fragezeichen-Link zur Doku als `title` (keine Erklärtexte in der Oberfläche) |
| `Menu`, `Popover`, `Tooltip` | 2px Ink-Rahmen, Papier, kein Schatten, Radius 0; Tooltip Ink-Grund mit Papier-Schrift |
| `Pagination`, `Stepper`, `Progress` | Radius 0; Progress-Track `--idt-chart-track`, Füllung `--accent-primary` |
| Skeleton | `radius=0`, Farbe `--surface-sunken`, ohne Animation |

Eyebrow/Versal-Etikett: Klasse `.idt-eyebrow` (13px, `letter-spacing: .12em`,
Versalien, `--text-muted`, optional „→ “ in `--idt-cyan-active`).
Kennzahl (`Stat`): neuer Baustein `src/shared/ui/Stat.tsx` — Zahl 36px/700
`tabular-nums` (`size="lg"` 56px), Titel 16/600, Etikett Versal 13px;
Kennzahlenband: Grid mit 2px-Rahmen und 2px-Trennern (siehe Prototyp).

### Chronicle und Tafel → DS (Q33)

| Alt (`components/chronicle`, `components/tafel`) | Neu |
|---|---|
| `ChronicleCard` (Standard) | Mantine `Paper withBorder p="lg"` (DS `soft`) |
| `ChronicleCard accent / accentColor` | `Paper` mit `style={{ "--card-accent": farbe }}` (6px Oberkante) bzw. Textkategorie-Karte mit 8px Linkskante aus `TEXT_CATEGORY_STYLE` |
| `ChronicleCard tone="board"` | `Paper className="karte--inverse"` |
| `ChronicleButton variant` | Mantine `Button` (`primary`→`filled`, `outline`→`default`, `ghost`→`subtle`) |
| `ChronicleDataChip` (mit Punkt) | `Badge variant="outline"` mit Quadrat 9px in der Zuordnungsfarbe |
| `ChronicleHeadline` (+ Eyebrow) | `Title order={1|2}` + `.idt-eyebrow` |
| `Eyebrow` | `.idt-eyebrow` |
| `SectionHead` | `Title order={2}` (Abschnittstitel mit Ink-Linie) |
| `Signet`, `Wordmark` | Bildmarke + Produktname (Stufe 2) |
| `FlapDigit`, `FlapNumber` | entfällt; Zahlen als `Stat` oder Text |

Vorgehen: pro Importdatei (57) ersetzen, Tests der vier Chronicle-Komponenten
löschen, neue Tests für `Stat`, `EmptyState`, `LoadingState`, `ErrorState`,
`ResponsiveTable` (Kartenmodus) anlegen. Danach `components/chronicle/` und
`components/tafel/` löschen; die Layout-Tokens (`--page-pad`, `--card-pad`,
`--map-height`, `--map-height-detail`, `--header-height`, `--row-h`) wandern
nach `src/shared/theme/layout.css`.

### Sweep

- `grep -rniE "chronicle|tafel|preussen|gold|archivo|plex|tabler|#2563eb|#ff0000|#0f2347|#c98a00|--led|--signal|--go\b|--board|--bg[234]?\b|--ink[23]?\b|--rule" apps/frontend/src` liefert nichts.
- `grep -rn 'c="dimmed"' apps/frontend/src` darf bleiben (läuft über die Brücke).
- Mantine-Farbnamen in `c=`/`color=` außerhalb der Zuordnungstabellen dürfen
  bleiben (Skalen); die 30 `--mantine-color-*`-Stellen werden auf DS-Aliasse
  umgeschrieben.
- Doku: `docs/DESIGN.md` (steht), `apps/frontend/README.md` (Abschnitte
  „Key dependencies“ → `lucide-react`, „Responsive layout“ → Karten unter
  48em, Register; neuer Abschnitt „Design“ mit Verweis auf `docs/DESIGN.md`),
  Root-`README.md` → Frontend-Absatz, `docs/architecture.md` (Technologietabelle,
  UI-Komponenten, Fehlerbehandlung; steht), `documentationData.ts` (Dunkelfassung,
  Impressum, Register), `docs/environment.md` (`REACT_APP_TILE_LAYER_URL_DARK`,
  `VITE_APP_VERSION`), `CHANGELOG.md`, `DEPLOY.md`/`docs/production_setup.md`
  (Build-Args), `docs/roadmap.md` (Stufen abhaken).

### Test-Checkliste Stufe 4

- [ ] `/?view=list`: Filterleiste (Suchfeld 2px, Filtermarken Violett-Soft, Trefferzahl rechts), zwei Zeilen ankreuzen → Auswahlleiste mit violetter Innenkante, „Entfernen“ rot gerahmt, angekreuzte Zeilen auf Papier-2 mit Ink-Strich.
- [ ] Spaltenkopf anklicken: sortierte Spalte fett mit Pfeil hinter dem Wort; Zeilen 48px, keine Zebra-Streifen.
- [ ] Projektliste auf 390px: jede Zeile eine Karte mit Name als Überschrift, Paare Etikett/Wert, Phase in der Fußzeile; Review-Tabelle (`/admin/vib-import/review/:id`) ebenfalls Karten, kein seitliches Scrollen der Seite.
- [ ] „Projekt anlegen“: Dialog mit 2px-Rahmen und hartem Schatten, Fokusfeld violett mit Ring, zwei Aktionen im Fuß; auf 390px Vollbild, Fuß bleibt sichtbar beim Scrollen.
- [ ] Löschen-Dialog: nur „Abbrechen“ und roter „Löschen“-Knopf, kein violetter.
- [ ] Erfolgsmeldung nach Speichern: Papier mit Ink-Rahmen und Haken, nicht grün; Fehlermeldung mit roter Innenkante.
- [ ] Projektseite: Abschnittstitel mit Ink-Linie, Kennzahlenband mit 2px-Rahmen, Tags kantig in Versalien.
- [ ] Dunkelfassung einmal durch alle Hauptrouten: keine weiße Fläche, keine violette Schrift auf Ink, Diagramme lesbar.
- [ ] `grep`-Sweep (oben) leer; `make test` grün.

## Mobil (Abbildung der Anwendungsebene auf die zwei Breakpoints)

| Anwendungsebene | Dashboard |
|---|---|
| Tabelle → Karten unter 720px | unter 48em (768px) |
| Register ab 900px, sonst Knopf unten | ab 62em (992px), sonst Knopf unten |
| Bedienhöhe 44px mobil | unter 48em (bestehende Mobil-Ebene) |
| Dialog Vollbild mobil | unter 48em (bestehende Mobil-Ebene) |

Die Regel „kein dritter Breakpoint“ aus `feature-mobile-usability.md` bleibt.

## Akzeptanzkriterien (gesamt)

- [ ] Kein Element trägt eine Farbe außerhalb der DS-Tokens oder der daraus
  gemischten Mantine-Skalen; `tokens.css` ist byte-gleich mit dem DS (bis auf
  den Kopfkommentar).
- [ ] Inter ist die einzige Schrift; keine externe Schrift- oder Script-Quelle.
- [ ] Lucide ist die einzige Icon-Bibliothek.
- [ ] Hell- und Dunkelfassung sind auf allen Routen vollständig; jede Schrift
  erreicht 4,5:1, Icons und Rahmen 3:1 auf ihrem Grund.
- [ ] Alle Bausteine der Anwendungsebene (Tabelle, Felder, Dialog, Zustände,
  Status, Register, Rückmeldung) sind vorhanden und sehen aus wie im Prototyp.
- [ ] `components/chronicle` und `components/tafel` existieren nicht mehr.
- [ ] Impressum und Datenschutz sind erreichbar (Seite oder Weiterleitung) und
  in der Admin-Maske pflegbar.
- [ ] `make test` grün; alle vier Issues durch `Needs User Test`.

## Offen (werden Issues, keine stillen Entscheidungen)

- Layout einzelner Seiten nach der Umstellung (Startseite, Projektseite,
  Infraplan) — Prüfung nach Stufe 4.
- Dunkle Kacheln: gibt es beim BKG eine dunkle Variante? Bis dahin bleibt die
  Karte hell.
- Vektor-Logo und Schutzraum liegen dem DS nicht vor; die Bildmarke bleibt PNG.
- Inhalte Impressum und Datenschutz (Human Task, #222).
- #224 — Das veröffentlichte DS-`tokens.css` enthält keinen Dunkel-Block; bis zur Auslieferung
  durch das DS steht ein aus `tokens.json` erzeugter Block in der vendorten Datei.
- #225 — Roter Kleintext erreicht auf Papier nur 4,1:1 und verfehlt damit die
  Anwendungsebene (4,5:1); Farbe oder Größe klären.
- #226 — Inline-Bearbeitung: wo `SaveStatus` eingesetzt wird und wie Speichern/Fehler dort
  angezeigt werden.
- #227 — Erklärtexte auf Seiten (Regel 10 in `docs/DESIGN.md`) in die Dokumentation
  verschieben.

## Issues (angelegt am 2026-10-21)

Epic #217; Stufe 1 #218; Stufe 2 #219 (depends on #218); Stufe 3 #220 (depends on
#218); Stufe 4 #221 (depends on #219, #220); Human Task Impressum/Datenschutz #222
(depends on #219). Während der Umsetzung kamen hinzu: #224 (DS-`tokens.css` ohne Dunkel-Block),
#225 (roter Kleintext 4,1:1), #226 (Inline-Bearbeitung / `SaveStatus`), #227 (Erklärtexte → Doku). Alle `area:design`, `bot:claude-code`. Die Texte unten sind der Stand beim Anlegen.

**Epic — IDT-Design: Dashboard auf das Design der Initiative Deutschlandtakt umstellen** (`type:ui`)
- Aufgabe: Richtung F vollständig durch das IDT-Design ersetzen (DS + Anwendungsebene + Dunkelfassung), in vier Stufen.
- Akzeptanzkriterien: die Gesamtliste oben.
- Abhängigkeiten: Teil-Issues 1–4.

**Teil 1 — IDT-Design Stufe 1: Tokens, Schrift, Theme, Dunkelfassung, Icons** (`type:ui`)
- Aufgabe: `tokens.css` vendoren, Mantine-Theme mit DS-Skalen, CSS-Brücke, Inter selbst gehostet, Google Fonts raus, Favicon-Set, Dunkel-Knopf, Tabler → Lucide.
- Akzeptanzkriterien: Test-Checkliste Stufe 1.
- Abhängigkeiten: keine.

**Teil 2 — IDT-Design Stufe 2: Kopf, Fuß, Impressum/Datenschutz, Register, Zustände** (`type:ui`, berührt Backend: `AppSettings`-Felder)
- Aufgabe: Kopfzeile mit Bildmarke, Fußzeile, vier Settings-Felder + Routen, Register der Projektseite, Leer/Lädt/Fehler, Loader → Skeleton.
- Akzeptanzkriterien: Test-Checkliste Stufe 2.
- Abhängigkeiten: Depends on Teil 1.

**Teil 3 — IDT-Design Stufe 3: Farbzuordnungen, Diagramme, Karte** (`type:ui`)
- Aufgabe: `semanticColors.ts`, alle Zuordnungen, Diagrammfarben, Zeitstrahl-Schraffur, Karte, Gruppenfarben inkl. Backend-Default.
- Akzeptanzkriterien: Test-Checkliste Stufe 3.
- Abhängigkeiten: Depends on Teil 1.

**Teil 4 — IDT-Design Stufe 4: Bausteine nach Anwendungsebene, Chronicle löschen, Sweep** (`type:ui`)
- Aufgabe: Mantine-Komponenten gestalten, Tabellen-Karten, Dialoge, Chronicle/Tafel entfernen, 57 Importstellen umziehen, Doku-Sweep.
- Akzeptanzkriterien: Test-Checkliste Stufe 4 und grep-Sweep.
- Abhängigkeiten: Depends on Teil 2, Teil 3.

**Human Task — Impressum und Datenschutz einpflegen** (`human-task`, `area:docs`)
- Aufgabe: Texte oder Weiterleitungs-URLs in Admin → Einstellungen eintragen; Betreiber klären.

## Referenzen

- `docs/DESIGN.md` — die verbindliche Gestaltungsvorgabe (Kurzfassung mit Verweisen).
- `docs/features/feature-rebrand-direction-f.md` — abgelöst.
- `docs/features/feature-mobile-usability.md` — Breakpoints, Mobil-Ebene (am 2026-10-21 um Karten und Register ergänzt).
- `docs/features/feature-text-categories.md`, `feature-project-timeline.md`, `feature-unassigned-assignments.md`, `feature-code-optimization.md` — am 2026-10-21 an W4–W7 angepasst.
