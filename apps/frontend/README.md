# Schienendashboard Frontend

Dieses Projekt implementiert das React-Frontend für das Schienendashboard. Es basiert auf [Vite](https://vitejs.dev/), [TypeScript](https://www.typescriptlang.org/) und [Mantine](https://mantine.dev/) und liefert eine modulare Oberfläche für die Visualisierung von Bahnprojekten.

## Schnellstart

```bash
npm install
npm run dev
```

* `npm run dev` startet die Entwicklungsumgebung (Vite Dev-Server).
* `npm run build` führt den TypeScript-Check (`tsc`) aus und erzeugt anschließend den Produktions-Build.
* `npm run preview` startet einen lokalen Server, um den Build zu überprüfen.

> **Hinweis:** Die Skripte `npm run gen:api` und `npm run gen:zod` generieren Client-Code aus einem OpenAPI-Schema. Sie setzen einen laufenden Backend-Endpunkt unter `http://127.0.0.1:8000/openapi.json` voraus.

## Projektstruktur

```
├── public/                # Statische Assets (Fonts, Favicons, …)
├── src/
│   ├── components/        # Wiederverwendbare UI-Bausteine (z. B. Header)
│   ├── features/          # Fachliche Feature-Module (Map, Projekte, Dokumentation …)
│   ├── lib/               # Hilfsfunktionen & Infrastruktur
│   ├── shared/            # Module, die von mehreren Features genutzt werden
│   ├── theme.ts           # Mantine-Theme-Konfiguration
│   └── router.tsx         # Routen-Definitionen
├── README.md              # Dieses Dokument
├── AGENT.MD               # Entwicklungsrichtlinien für Beitragende
└── package.json           # npm-Skripte und Abhängigkeiten
```

## Entwicklungskonventionen

* **TypeScript strikt halten:** Neue Module sollen Typsicherheit konsequent nutzen (keine `any`-Typen).
* **Feature-Folder-Struktur:** Funktionsbereiche (z. B. Karte, Projekte, Dokumentation) liegen in eigenen Ordnern unter `src/features`.
* **Getrennte Zuständigkeiten:** UI-Komponenten in `components/`, technische Hilfen in `lib/`, globale Typen in `types.ts` bzw. `shared/`.
* **Mantine-Komponenten:** Für Layout- und UI-Aufgaben bevorzugt Mantine verwenden und auf konsistente Theme-Farben achten (`theme.ts`).
* **Routing:** Neue Seiten als untergeordnete Routen des `Layout` in `router.tsx` anlegen.
* **Dokumentation aktuell halten:** Inhaltliche oder visuelle Änderungen an Features müssen in der Entwickler- und Nutzerdokumentation (README, Dokumentationsseite im Frontend) nachvollzogen werden.

## Dokumentation im Frontend

Über `/dokumentation` steht eine eingebettete Dokumentationsseite zur Verfügung. Sie beschreibt zentrale Features, Workflows und Qualitätsanforderungen. Jede Änderung am Funktionsumfang muss hier nachvollzogen werden.

## Qualitätschecks

Vor einem Commit sollten mindestens folgende Prüfungen laufen:

```bash
npm run build
```

Optional ergänzt ihr projektspezifische Tests oder Linter, sobald verfügbar. Bitte die Ergebnisse im Pull Request dokumentieren.

## Lizenz

Dieses Projekt ist derzeit intern. Ergänzt eine Lizenzdatei, sobald das Projekt veröffentlicht wird.
