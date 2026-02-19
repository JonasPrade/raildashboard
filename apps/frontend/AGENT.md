# Contributor Guide – Frontend

> The authoritative contributor guide is **`AGENT.md` at the repository root**. Read that first.

This file contains frontend-specific details that complement the root guide.

> **Default language:** English. Write code, comments, documentation, and commit messages in English. UI strings are in German.

## Project structure

```
src/
├── features/          # Feature modules (auth, dashboard, documentation, ...)
├── components/        # Shared UI components (buttons, layouts, navigation)
├── api/               # Backend integration & API clients (React Query services, REST wrapper)
├── hooks/             # Custom React hooks (e.g. useProjects)
├── types/             # Global TypeScript types used across features
├── shared/            # Utilities, constants, helper functions (no UI components)
├── assets/            # Images, fonts, icons
└── router.tsx         # Central routing configuration with layout
```

## Core principles

1. **TypeScript first:** Avoid `any`. Use `unknown` for temporarily untyped values and add type guards to refine them. Place global types in `src/types/` and utilities in `src/shared/`. Keep feature-specific types local to the respective feature (`types.ts`).
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
2. **Feature-oriented structure:** Create new functionality under `src/features/<feature-name>` (e.g. `src/features/auth/`, `src/features/dashboard/`). Only place shared UI in `src/components/`.
3. **Use Mantine intentionally:** Rely on Mantine's standard components. Extract recurring patterns into custom components under `src/components/` and manage theme overrides centrally (e.g. `theme.ts`).
4. **Keep routing tidy:** Register new pages in `src/router.tsx`. For larger bundles use lazy loading (`React.lazy()` and `Suspense`).
   ```tsx
   const DocumentationPage = React.lazy(() => import("./features/documentation/DocumentationPage"));

   <Route
     path="/documentation"
     element={(
       <Suspense fallback={<Loader />}>
         <DocumentationPage />
       </Suspense>
     )}
   />
   ```
5. **Protect quality:** Before committing, run `npm run build && npm run lint && npm run test` locally and document the results.

## Git workflow
- **Branches:** `feature/<summary>`, `fix/<bug-id>`, `docs/<topic>`, `refactor/<area>`.
- **Strategy:** `main` stays stable and deployable. `develop` collects completed features. Branch from `develop` when starting work.
- **Merges:** Use squash merges from feature branches into `develop`. Rebase critical bug fixes onto `main` and sync `develop` afterwards.
- **Rebasing:** Rebase your branch onto the latest target branch before submitting a PR.

## Code quality & tooling
- **ESLint:** Follow the project-wide rules (`npm run lint`). Do not ignore warnings without documenting why.
- **Prettier:** Keep formatting consistent via `npm run format` or your editor integration.
- **Type checks:** Run `npm run type-check` regularly.
- **Pre-commit hooks:** Husky and lint-staged are configured; update `.husky/pre-commit` when adding new files.
- **EditorConfig:** Respect `.editorconfig`; inform the team about significant changes.

## State management & APIs
- **State:** Use React state/hooks for local state. Prefer Zustand or Redux Toolkit for shared client state; use React Query for server state.
- **API structure:** Wrap API calls in `src/api/<resource>.ts`. Keep return values strictly typed and handle errors consistently.
- **Error handling:** Produce uniform error objects (`{ message, code }`). Centralise toasts/dialogues and remove `console.error` statements before releasing (or guard them behind feature flags).

## Documentation & communication
- **Stay in sync:** Update the following whenever you change features or scripts: `README.md` (setup, workflows) and `src/features/documentation/DocumentationPage.tsx` (user-facing overview).
- **Feature documentation:** Follow this structure for new entries:
  1. **Purpose** – context and problem statement.
  2. **Components** – main components, props, responsibilities.
  3. **APIs & data** – endpoints, query keys, schemas.
  4. **Scripts & commands** – relevant npm scripts, migration hints.
- **Code comments:** Document public APIs (hooks, components) with JSDoc. Use inline comments sparingly for complex logic and keep them up to date.
- **Communication:** Maintain changelogs and release notes; highlight breaking changes prominently.

## Testing requirements
- **Test types:** Unit tests with Vitest, integration tests (e.g. React Testing Library), end-to-end tests (Playwright/Cypress).
- **Coverage:** Minimum 80 % statements/branches. Review coverage reports before merging.
- **Commands:**
  - `npm run test` – unit/integration
  - `npm run test:coverage` – coverage report
  - `npm run lint` – ESLint
  - `npm run type-check` – TypeScript validation
  - `npm run build` – production build
- **CI:** PRs can only be merged when all checks succeed.

## Performance & best practices
- **Code splitting:** Use `React.lazy()` or dynamic imports for heavy components.
- **Bundle sizes:** Aim for chunks below 300 kB; optimise (tree shaking, splitting) when exceeding.
- **Memoisation:** Apply `useMemo`/`useCallback` for expensive computations or heavy prop drilling.
- **Networking:** Batch API requests, leverage React Query caching, and define retry strategies.

## Accessibility standards
- **WCAG 2.1 AA:** All UI components must meet this level.
- **Semantics:** Use semantic HTML; add ARIA attributes only when necessary.
- **Keyboard:** Validate focus order and provide visible focus styles.
- **Screen readers:** Ensure labels, descriptions, and `aria-live` regions for dynamic content.
- **Testing:** Perform manual checks with screen readers (NVDA/VoiceOver) before significant releases.

## Pull requests
- **Commit messages:** Follow Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Examples:
  - `feat(projects): add project group analytics`
  - `fix(map): correct bounding box parsing`
- **PR description:**
  ```markdown
  ## Summary
  - ...

  ## Testing
  - `npm run build`
  - `npm run lint`
  ```
- **Checklist:**
  - [ ] Tests & linting executed locally
  - [ ] Documentation updated (README + app)
  - [ ] Screenshots/demos attached (for UI changes)
  - [ ] Breaking changes documented
- **Review process:** Require at least two approvals; address reviewer feedback promptly.

## Screenshots & demos
- **Formats:** PNG or WebP, 1440 px width, retina scale 2× recommended.
- **Storage:** Place under `docs/screenshots/<feature>/`. Include date or commit hash in filenames.
- **Accessibility proof:** For UI changes, document keyboard navigation and screen-reader output (e.g. brief GIF/WebM or extra screenshots).
- **Demos:** Link a short Loom/MP4 (≤ 2 min) for interactive changes when relevant.
