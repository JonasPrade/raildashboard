# Leitfaden für Beitragende

## Projektstruktur
```
src/
├── features/          # Feature-Module (auth, dashboard, dokumentation, ...)
├── components/        # Geteilte UI-Komponenten (Buttons, Layouts, Navigation)
├── api/               # Backend-Integration & API-Clients (React Query Services, REST-Wrapper)
├── hooks/             # Custom React Hooks (z. B. useProjects)
├── types/             # Globale TypeScript-Typen, die feature-übergreifend genutzt werden
├── shared/            # Utilities, Konstanten, Helper-Funktionen (keine UI)
├── assets/            # Bilder, Fonts, Icons
└── router.tsx         # Zentrale Routing-Konfiguration mit Layout
```

## Allgemeine Prinzipien
1. **TypeScript first:** Kein `any`. Nutzt `unknown`, wenn ein Wert zunächst untypisiert bleibt, und erstellt Type Guards, um ihn zu verfeinern. Globale Typen gehören in `src/types/`. `src/shared/` beherbergt Hilfsfunktionen und Konstanten. Feature-spezifische Typen verbleiben lokal im jeweiligen Feature (`types.ts`).
   ```ts
   type RawProject = { id: number; payload: unknown };

   function isProjectPayload(value: unknown): value is { title: string } {
     return typeof value === "object" && value !== null && "title" in value;
   }

   export function mapProject(raw: RawProject) {
     if (!isProjectPayload(raw.payload)) throw new Error("Invalid payload");
     return { id: raw.id, title: raw.payload.title };
   }
   ```
2. **Feature-orientierte Struktur:** Neue Funktionalitäten als Module unter `src/features/<feature-name>` anlegen, z. B. `src/features/auth/`, `src/features/dashboard/`. Nur gemeinsam nutzbare UI in `src/components/` ablegen.
3. **Mantine gezielt nutzen:** Standardkomponenten aus Mantine verwenden. Wiederkehrende Muster als Custom-Komponenten in `src/components/` extrahieren und Theme-Overrides zentral im Theme (z. B. `theme.ts`) pflegen.
4. **Routing pflegen:** Neue Seiten in `src/router.tsx` registrieren. Bei größeren Bundles Lazy Loading via `React.lazy()` und `Suspense` einsetzen.
   ```tsx
   const DocumentationPage = React.lazy(() => import("./features/documentation/DocumentationPage"));

   <Route
     path="/dokumentation"
     element={(
       <Suspense fallback={<Loader />}>
         <DocumentationPage />
       </Suspense>
     )}
   />
   ```
5. **Qualität sichern:** Vor jedem Commit lokal `npm run build && npm run lint && npm run test` ausführen und Ergebnisse dokumentieren.

## Git-Workflow
- **Branches:** `feature/<kurzbeschreibung>`, `fix/<bug-id>`, `docs/<thema>`, `refactor/<bereich>`.
- **Strategie:** `main` ist stabil und deploy-fähig. `develop` bündelt abgeschlossene Features. Feature-Branches von `develop` abzweigen.
- **Merges:** Features per Squash-Merge in `develop`. Kritische Bugfixes per Rebase-Merge direkt nach `main` (anschließend `develop` aktualisieren).
- **Rebasing:** Vor PR-Abgabe lokalen Branch auf den aktuellen Ziel-Branch rebasen.

## Code-Qualität & Tooling
- **ESLint:** Projektweite Regeln (`npm run lint`). Keine Warnungen ignorieren, ohne den Grund zu dokumentieren.
- **Prettier:** Einheitliche Formatierung via `npm run format` oder Editor-Integration.
- **Type-Checks:** `npm run type-check` regelmäßig ausführen.
- **Pre-Commit-Hooks:** Husky & lint-staged konfigurieren; neue Dateien in `.husky/pre-commit` berücksichtigen.
- **EditorConfig:** `.editorconfig` respektieren; bei Änderungen Team informieren.

## State Management & APIs
- **State:** Lokaler Zustand mit React State/Hooks. Geteilter Zustand bevorzugt via Zustand oder Redux Toolkit; für Server State React Query einsetzen.
- **API-Struktur:** API-Calls in `src/api/<resource>.ts` kapseln. Rückgaben strikt typisieren und Fehler behandeln.
- **Error-Handling:** Einheitliche Fehlerobjekte erzeugen (`{ message, code }`). Toasts/Dialoge zentralisieren, Logging via `console.error` nur für Debugging (vor Deploys entfernen oder Feature Flags nutzen).

## Dokumentation & Kommunikation
- **Synchron halten:** Jede Feature- oder Skriptänderung sofort in folgenden Quellen pflegen: `README.md` (Setup, Workflows) und `src/features/documentation/DocumentationPage.tsx` (User-facing Überblick).
- **Feature-Dokumentation:** Neue Einträge mit folgender Struktur ergänzen:
  1. **Zweck** – kurzer Kontext, Problemstellung.
  2. **Komponenten** – Hauptkomponenten, Props, Zuständigkeiten.
  3. **APIs & Daten** – genutzte Endpunkte, Query Keys, Schemas.
  4. **Skripte & Befehle** – relevante npm-Skripte, Migrationshinweise.
- **Code-Kommentare:** Öffentliche APIs (Hooks, Komponenten) mit JSDoc dokumentieren. Inline-Kommentare nur bei komplexer Logik einsetzen und bei Refactorings aktualisieren.
- **Kommunikation:** Changelogs & Release Notes im Repo pflegen; Breaking Changes prominent kennzeichnen.

## Testing-Anforderungen
- **Test-Typen:** Unit-Tests mit Vitest, Integrations-Tests (z. B. React Testing Library), End-to-End-Tests (Playwright/Cypress).
- **Coverage:** Mindest-Testabdeckung 80 % (Statements/Branches). Coverage-Reports vor Merge überprüfen.
- **Befehle:**
  - `npm run test` – Unit/Integration
  - `npm run test:coverage` – Coverage-Report
  - `npm run lint` – ESLint
  - `npm run type-check` – TS-Validierung
  - `npm run build` – Produktions-Build
- **CI:** PRs dürfen nur gemerged werden, wenn alle Checks grün sind.

## Performance & Best Practices
- **Code-Splitting:** Route-basiert per `React.lazy()` oder dynamische Imports für schwere Komponenten.
- **Bundle-Größen:** Warnung ab 300 kB pro Chunk; Optimierung (Tree-Shaking, Splitting) bei Überschreitung.
- **Memoization:** `useMemo`/`useCallback` bei teuren Berechnungen oder Prop-Drilling einsetzen.
- **Netzwerk:** API-Requests zusammenfassen, Caching via React Query nutzen, Retry-Strategien definieren.

## Accessibility-Standards
- **WCAG 2.1 AA:** Alle UI-Komponenten müssen diesem Level entsprechen.
- **Semantik:** Semantisches HTML, ARIA-Attribute nur ergänzend.
- **Keyboard:** Fokus-Reihenfolge testen, sichtbare Fokus-Stile sicherstellen.
- **Screen-Reader:** Labels, Beschreibungen und `aria-live`-Regionen für dynamische Inhalte bereitstellen.
- **Tests:** Manuelle Checks mit Screen Readern (NVDA/VoiceOver) vor wichtigen Releases.

## Pull-Requests
- **Commit-Messages:** Conventional Commits verwenden (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Beispiele:
  - `feat(projects): add project group analytics`
  - `fix(map): correct bounding box parsing`
- **PR-Beschreibung:**
  ```markdown
  ## Summary
  - ...

  ## Testing
  - `npm run build`
  - `npm run lint`
  ```
- **Checkliste:**
  - [ ] Tests & Linting lokal ausgeführt
  - [ ] Dokumentation aktualisiert (README + App)
  - [ ] Screenshots/Demos beigefügt (falls UI)
  - [ ] Breaking Changes dokumentiert
- **Review-Prozess:** Mindestens 2 Approvals, alle automatischen Checks müssen erfolgreich sein. Reviewer-Kommentare zeitnah adressieren.

## Screenshots & Demos
- **Formate:** PNG oder WebP, 1440px Breite, Retina-Skalierung 2× empfohlen.
- **Ablage:** Unter `docs/screenshots/<feature>/`. Dateinamen mit Datum oder Commit-Hash versehen.
- **Accessibility-Nachweis:** Für UI-Änderungen zusätzlich Tastatur-Navigation und Screen-Reader-Ausgabe dokumentieren (z. B. kurze GIF/WebM oder separate Screenshots).
- **Demos:** Falls interaktive Änderungen, kurzes Loom/MP4 (max. 2 min) verlinken.

