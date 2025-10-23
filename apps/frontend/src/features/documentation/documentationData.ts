export type FeatureHighlight = {
    title: string;
    description: string;
    details?: string[];
};

export type WorkflowStep = {
    title: string;
    steps: string[];
};

export const featureHighlights: FeatureHighlight[] = [
    {
        title: "Interaktive Kartenansicht",
        description:
            "MapLibre-basierte Karte mit Mantine-Overlays für Steuerungselemente wie Filter." +
            " Der Kartenbereich ist bewusst modular aufgebaut, um spätere Layer oder Datenquellen zu integrieren.",
        details: [
            "Filterdrawer für Projektgruppen inkl. URL-Synchronisation",
            "Mantine-Komponenten für Buttons, Panels und Layout",
            "Vorbereitet für zusätzliche Steuerungs- und Overlay-Komponenten"
        ]
    },
    {
        title: "Projektgruppen-Filter",
        description:
            "Drawer-Komponente (`GroupFilterDrawer`) erlaubt die Auswahl mehrerer Projektgruppen." +
            " Auswahl wird als Query-Parameter (`group`) in der URL gespiegelt und holt ihre Daten direkt aus dem Backend.",
        details: [
            "Anbindung des Endpunkts `/api/v1/project_groups/` über React Query",
            "Custom-Rendering der Auswahlchips inkl. API-Farbkodierung",
            "Integrierte Lade- und Fehlermeldungen im Drawer"
        ]
    },
    {
        title: "Frontend-Dokumentation",
        description:
            "Diese Seite fasst Features, Workflows und Qualitätsanforderungen zusammen und ergänzt das README für Entwickler:innen.",
        details: [
            "Pflichtaktualisierung bei Feature-Änderungen",
            "Verlinkung auf relevante Skripte und Einstiegspunkte",
            "Strukturierte Aufbereitung für Projektbeteiligte"
        ]
    }
];

export const workflows: WorkflowStep[] = [
    {
        title: "Lokale Entwicklung",
        steps: [
            "Repository klonen und Abhängigkeiten installieren (`npm install`).",
            "Entwicklungsserver via `npm run dev` starten.",
            "Routen über den Browser (`/` für Karte, `/dokumentation` für Doku) prüfen.",
            "Vor einem Commit immer `npm run build` ausführen und Fehler beheben."
        ]
    },
    {
        title: "Dokumentation pflegen",
        steps: [
            "Feature- oder UI-Änderungen identifizieren.",
            "README.md und Dokumentationsseite parallel anpassen (Abschnitt 'Feature-Highlights' ergänzen/ändern).",
            "Bei neuen Skripten oder Prozessen den Bereich 'Workflows & Qualität' erweitern.",
            "Pull Request mit kurzer Zusammenfassung und Auflistung der Checks erstellen."
        ]
    }
];

export const qualityGates: string[] = [
    "`npm run build` muss ohne Fehler durchlaufen.",
    "Screenshots bereitstellen, wenn UI-Änderungen sichtbar sind.",
    "Query-Parameter und Routing-Szenarien testen (insbesondere `/` und `/dokumentation`)."
];

export const techStack: string[] = [
    "Vite 7 als Build- und Dev-Server",
    "React 19 mit React Router 7",
    "TypeScript 5 mit strict mode",
    "React Query für Server-State-Management",
    "Mantine 8 als UI-Bibliothek",
    "MapLibre GL für Kartendarstellung"
];
