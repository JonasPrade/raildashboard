# Prompt: IDT-Design vollständig umsetzen

Du arbeitest im Repository `JonasPrade/raildashboard` (Schienendashboard, React 19 +
Mantine 8 Frontend unter `apps/frontend`, FastAPI-Backend unter `apps/backend`). Deine
Aufgabe ist die **vollständige** Umstellung des Dashboards auf das Design der Initiative
Deutschlandtakt, alle vier Stufen, bis die Akzeptanzkriterien des Epics erfüllt sind.
Nichts davon ist optional, keine Stufe wird übersprungen oder „für später“ gelassen.

## Vor dem ersten Schritt lesen, vollständig

1. `AGENT.md` und `CLAUDE.md` (Arbeitsregeln, Doku-Pflichten, `make test`, Migrationen,
   `Needs User Test`).
2. `docs/features/feature-idt-design.md` — der Plan. Er enthält alle Werte, Dateilisten,
   Mantine-Skalen, die CSS-Brücke, die Dunkel-Token-Tabelle, die Tabler-zu-Lucide-Zuordnung,
   die Chronicle-zu-DS-Zuordnung, die Komponentenregeln und je Stufe eine Test-Checkliste.
   Was dort steht, ist entschieden; es wird nicht neu diskutiert.
3. `docs/DESIGN.md` — die zwölf Regeln und die Verbote.
4. `docs/features/idt-design/` — Prototyp (`prototyp/liste.html`, `detail.html`,
   `dialog.html`, `proto.css`) und fünf Screenshots. Das ist die Sichtreferenz: Maße,
   Abstände, Rahmen, Schriftgrade. Öffne die HTML-Dateien mit Playwright und vergleiche
   dein Ergebnis dagegen; für den Prototyp kopierst du `InterVariable.woff2` nach
   `docs/features/idt-design/prototyp/fonts/`.
5. Das Design-System: Artefakt `https://claude.ai/artifact/14Xq8ZVdYasy3EUQ8bLhGh`
   (Version 9 oder neuer). Mit dem Artifact-Werkzeug (`action: read`, `path`) holst du
   `project/README.md`, `project/anwendungsebene.md`, `project/tokens.css` (generiert, mit
   Theme `dark`), `project/tokens.json`, `project/fonts/InterVariable.woff2`,
   `project/fonts/InterVariable-Italic.woff2`, `project/assets/favicons/*` und
   `project/assets/logo-idt-inverse.png`. Kannst du das Artefakt nicht lesen, liegen
   Tokens, Schrift und Logo auch im Repo
   `initiative-deutschlandtakt/wordpress-theme-initiative-deutschlandtakt-` unter
   `theme/idt-deutschlandtakt/` (`style.css` Abschnitt 2, `assets/fonts/`, `assets/`); die
   Dunkelwerte stehen dann in der Tabelle der Feature-Datei. Referenzumsetzung der
   Dunkelfassung: `JonasPrade/ini_strategy` → `stakeholder/static/stil.css` Abschnitt 4.
6. Die Issues #217 (Epic), #218, #219, #220, #221 (Stufen 1–4). #222 ist eine Human Task,
   die du nicht anfasst.

## Branch und Ablauf

- Prüfe, ob PR #223 (die Planung) gemerged ist. Wenn ja: Branch `feat/217-idt-design` von
  `master`. Wenn nein: Branch `feat/217-idt-design` von `claude/optimistic-darwin-wxwps7`
  und im PR-Text vermerken, dass er auf #223 aufsetzt.
- Reihenfolge: Stufe 1 (#218) → Stufe 2 (#219) und Stufe 3 (#220), die beide nur von
  Stufe 1 abhängen und parallel laufen dürfen → Stufe 4 (#221). Je Stufe ein
  zusammenhängender Commit-Block mit Conventional-Commit-Nachrichten auf Englisch; vor
  dem ersten Commit einer Stufe das Issue auf `In Progress` setzen (Board „raildashboard
  Roadmap“, Feld `Stage`, IDs in `docs/github-projects.md`), nach Abschluss auf
  `Needs User Test` mit der Test-Checkliste der Stufe als Issue-Kommentar. Issues nie
  selbst schließen.
- Ein Pull Request am Ende, `Closes #218`, `Closes #219`, `Closes #220`, `Closes #221`,
  `Part of #217`. CI (`make test`) muss grün sein; du beobachtest den PR und behebst
  Fehlschläge selbst.
- `make test` ist die Prüfung, lokal wie in der CI; `make test-local` die schnelle
  Schleife. Nach jeder Stufe zusätzlich `npm run lint`, `npm run build`, `tsc --noEmit`.

## Arbeiten mit Subagenten

Du bist Orchestrator. Zerlege jede Stufe in unabhängige Arbeitspakete und gib sie an
Subagenten; lass nichts Mechanisches im Hauptkontext laufen. Nutze für Orchestrierung,
Theme-Entwurf, Entscheidungen an Rändern des Plans und die Abnahme je Stufe das stärkste
verfügbare Modell (Opus oder höher); für mechanische Sweeps (Icon-Tausch in 35 Dateien,
65 Loader-Stellen, 57 Chronicle-Importe, `--mantine-color-*`-Stellen, Doku-Nachzüge) reicht
Sonnet. Haiku für nichts, was Design beurteilt.

Bewährte Schnitte:

- Stufe 1: (a) Tokens, Brücke, Theme, Dunkel-Mechanik; (b) Schrift, Favicons, `index.html`,
  `app.css`; (c) Icon-Tausch; (d) Kachel-URL dunkel in Env, Dockerfile, `release.yml`,
  Compose, Doku. Danach ein Prüf-Agent mit Playwright: Screenshots hell und dunkel aller
  Hauptrouten, Kontrastprüfung der Schrift gegen ihren Grund (Script in der Feature-Datei
  beschrieben: WCAG-Verhältnis, Grenzen 4,5:1 Schrift, 3:1 Icons und Rahmen).
- Stufe 2: (a) Backend-Felder, Migration, Schema, `make gen-api`; (b) Kopf und Fuß;
  (c) Impressum/Datenschutz-Routen und Admin-Maske; (d) Register; (e) Zustände-Bausteine
  und Loader-Sweep; (f) `VITE_APP_VERSION` in Build und Doku.
- Stufe 3: (a) `semanticColors.ts` und alle Konsumenten; (b) Diagramme inkl. Tests;
  (c) Zeitstrahl-Schraffur; (d) Karte, Geometrie-Vorschau, Gruppenfarben inkl.
  Backend-Default und MCP-Default.
- Stufe 4: (a) Mantine-Komponentenregeln in `theme.ts` und `components.css`;
  (b) `ResponsiveTable` Kartenmodus; (c) Chronicle-zu-DS-Umzug in Paketen von etwa zehn
  Dateien je Agent, danach Löschen von `components/chronicle` und `components/tafel`;
  (d) neue Tests für `Stat`, `EmptyState`, `LoadingState`, `ErrorState`, `ResponsiveTable`;
  (e) Doku-Sweep; (f) Prüf-Agent mit dem `grep`-Sweep aus der Feature-Datei und dem
  Bildvergleich gegen den Prototyp.

Jeder Subagent bekommt: Ziel, exakte Dateiliste, die betreffenden Abschnitte der
Feature-Datei als Pfadangabe (nicht als Zusammenfassung), was er nicht anfassen darf, und
die Prüfung, mit der er fertig ist. Du liest seine Diffs, bevor du committest.

## Qualitätsregeln, die über allem stehen

- Nur Tokens aus `tokens.css` und `semanticColors.ts`; kein Hex-Literal in einer
  Komponente (Ausnahme: MapLibre braucht Hex, deshalb `MAP_COLOR`).
- Nur semantische Aliasse (`--surface`, `--text-muted`, `--accent-primary`,
  `--border-frame`), nie `--idt-paper` oder `--idt-ink` direkt in Oberflächen.
- Kein Gelb als Status, kein Grün als Erfolgsfläche, Rot nur für Überfälliges und Löschen.
- Radius 0, 2px Ink-Rahmen, Hover ohne Anheben, kein Blockschatten, kein Kreisel.
- Zwei Breakpoints, 48em und 62em, kein dritter.
- Nichts aus Richtung F bleibt: der `grep`-Sweep der Feature-Datei liefert am Ende nichts.
- Bei jeder Stelle, an der der Plan eine Frage offen lässt, entscheidest du nicht still:
  eigenes Issue mit `area:design` anlegen, Regel aus `docs/github-projects.md`
  („Konzept-Lücken werden Issues“), und so umsetzen, dass beide Antworten später möglich
  bleiben.
- Dokumentation ist Teil jeder Stufe, nicht des Schlusses: `apps/frontend/README.md`,
  Root-`README.md`, `docs/environment.md`, `DEPLOY.md`, `docs/production_setup.md`,
  `CHANGELOG.md` (`[Unreleased]`), `documentationData.ts`, `docs/roadmap.md` (Stufen
  abhaken).

## Fertig heißt

Alle Punkte unter „Akzeptanzkriterien (gesamt)“ in `docs/features/feature-idt-design.md`
sind erfüllt, der PR ist grün, die vier Issues stehen auf `Needs User Test` mit
Checklisten, und du hast dem Nutzer eine Übersicht gegeben: was gebaut wurde, welche
Issues du für offene Fragen angelegt hast, und die Screenshots hell und dunkel der
Hauptrouten neben den Prototyp-Bildern.
