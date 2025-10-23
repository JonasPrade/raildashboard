# Railway Dashboard Frontend

This project implements the React frontend for the railway dashboard. It is built with [Vite](https://vitejs.dev/), [TypeScript](https://www.typescriptlang.org/), and [Mantine](https://mantine.dev/) to provide a modular interface for visualising rail infrastructure projects.

## Quick start

```bash
npm install
npm run dev
```

* `npm run dev` starts the development environment (Vite dev server).
* `npm run build` runs the TypeScript check (`tsc`) and creates the production build.
* `npm run preview` starts a local server to inspect the build output.

> **Note:** The scripts `npm run gen:api` and `npm run gen:zod` generate client code from an OpenAPI schema. They require a backend endpoint to be available at `http://127.0.0.1:8000/openapi.json`.

## Project structure
## Konfiguration

Standardmäßig kommuniziert das Frontend mit einem Backend unter `http://localhost:8000`. Über die Umgebungsvariable `VITE_API_BASE_URL` (z. B. in einer `.env`-Datei im Projektwurzelverzeichnis) kann eine alternative Basis-URL hinterlegt werden.

## Projektstruktur

```
├── public/                # Static assets (fonts, favicons, …)
├── src/
│   ├── components/        # Reusable UI building blocks (e.g. header)
│   ├── features/          # Domain-specific feature modules (map, projects, documentation …)
│   ├── lib/               # Utilities and infrastructure
│   ├── shared/            # Modules shared across features
│   ├── theme.ts           # Mantine theme configuration
│   └── router.tsx         # Route definitions
├── README.md              # This document
├── AGENT.MD               # Contribution guidelines
└── package.json           # npm scripts and dependencies
```

## Development conventions

* **Stay strict with TypeScript:** New modules should embrace type safety (avoid `any`).
* **Feature folder structure:** Functional areas (e.g. map, projects, documentation) live in dedicated folders under `src/features`.
* **Separation of concerns:** Put UI components in `components/`, technical helpers in `lib/`, and global types in `types.ts` or `shared/`.
* **Mantine components:** Prefer Mantine for layout and UI work, and keep theme colours consistent (`theme.ts`).
* **Routing:** Register new pages as children of the shared `Layout` component in `router.tsx`.
* **Keep documentation current:** Any functional or visual change must be reflected in both developer- and user-facing docs (README, in-app documentation page).

## Documentation inside the app

Navigate to `/documentation` to access the embedded documentation page. It outlines the key features, workflows, and quality requirements. Update this page whenever the functional scope changes.

## Quality checks

Run at least the following check before committing:

```bash
npm run build
```

Feel free to add project-specific tests or linters as they become available. Document the executed checks in the pull request.

## Licence

The project is currently internal. Add a licence file once the project is ready for public release.
