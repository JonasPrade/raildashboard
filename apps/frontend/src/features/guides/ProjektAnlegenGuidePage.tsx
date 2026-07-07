import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "projekt-anlegen",
    title: "Anleitung: Projekt anlegen",
    chip: "Grundlagen",
    intro: `Wie du über den Assistenten unter „Neues Projekt anlegen" ein Projekt Schritt für Schritt erfasst — von den Pflicht-Stammdaten über Geometrie und Planungsstand bis zur Verknüpfung mit FinVes und VIB-Einträgen.`,
    prerequisites: `- Du bist als **Editor** oder **Admin** eingeloggt (Recht „Projekte anlegen").
- Name (und idealerweise Projektnummer) des Vorhabens sind bekannt.
- Optional: Geometriedaten (Betriebsstellen oder GeoJSON) und bekannte Quellen (FinVe, VIB) zum direkten Verknüpfen.`,
    steps: [
        {
            key: "einstieg",
            title: "Der Assistent im Überblick",
            body: `Neue Projekte entstehen über den Assistenten unter [Neues Projekt anlegen](/admin/projects/new) (erreichbar über die Admin-Übersicht). Er führt durch sechs Stationen — nur die erste ist Pflicht:

1. **Stammdaten** (Pflicht) — legt das Projekt als Entwurf an.
2. **Geometrie** (optional) — Verlauf auf der Karte.
3. **Eigenschaften** (optional) — technische Projekteigenschaften.
4. **Planungsstand** (optional) — Phase, Beobachtungen, Verfahren.
5. **FinVes** (optional) — Finanzierungsvereinbarungen verknüpfen.
6. **VIB** (optional) — bestehende VIB-Einträge verknüpfen.

Sobald das Projekt angelegt ist, sind die Stationen frei anklickbar — du musst die Reihenfolge nicht einhalten. Unten stehen dauerhaft **„Zurück"**, **„Weiter"**, **„Als Entwurf speichern"** und **„Projekt fertigstellen"**.

> [!blue] Entwürfe aus Importen
> Auch die Import-Workflows (Fulda, Bauportal) legen über „Projekt fehlt?" Projekt-Entwürfe an. Diese tauchen wie eigene Entwürfe unter [Entwürfe](/admin/drafts) auf und werden dort mit demselben Assistenten fertiggestellt.`,
            exampleKey: "projekt-wizard",
        },
        {
            key: "stammdaten",
            title: "Schritt 1: Stammdaten (Pflicht)",
            body: `Nur der **„Projektname"** ist Pflicht; alles Weitere lässt sich nachtragen:

- **„Projektnummer"** (z. B. ABS 123) — hilft beim automatischen Zuordnen von Importen.
- **„Beschreibung"** und **„Begründung"** — Freitext.
- **„Übergeordnetes Projekt"** — hier machst du das neue Projekt zum **Unterprojekt** (z. B. einen Planfeststellungsabschnitt). Der Planungsstand hängt dann am Blatt, das übergeordnete Projekt aggregiert (siehe [Projektfortschritt](/admin/anleitungen/projektfortschritt), Abschnitt „Unterprojekte & Aggregation").
- **„Projektgruppen"** — z. B. Bedarfsplan Schiene; steuert u. a. die Voreinstellung „parlamentarische Befassung".

**„Projekt anlegen"** speichert das Projekt als **Entwurf** und springt zu Schritt 2. Ab jetzt geht nichts mehr verloren — du kannst jederzeit unterbrechen.`,
            exampleKey: "projekt-stammdaten",
        },
        {
            key: "geometrie",
            title: "Schritt 2: Geometrie (optional)",
            body: `Hier erfasst du den Verlauf auf der Karte — per Routing über das Schienennetz, mit Betriebsstellen, per GeoJSON-Upload oder von Hand gezeichnet. Nach **„Geometrie speichern"** bleibt der Editor offen, sodass du mehrere Geometrien nacheinander ergänzen kannst.

Die vier Erfassungswege und das Löschen bestehender Geometrie erklärt im Detail die [Anleitung: Geometrien erstellen](/admin/anleitungen/geometrie). Ohne Geometrie erscheint das Projekt nicht auf der Karte, ist aber in Listen und Detailseite voll nutzbar.`,
        },
        {
            key: "eigenschaften",
            title: "Schritt 3: Eigenschaften (optional)",
            body: `Hier setzt du die technischen Projekteigenschaften — dieselben Felder wie im Bearbeiten-Dialog der Projektdetailseite (u. a. Länge, neue Vmax, ETCS-Level, NBS/ABS, Wirkungen für Personenfern-, Nah- und Güterverkehr).

**„Speichern & Weiter"** übernimmt die Werte; **„Überspringen"** lässt sie leer.`,
        },
        {
            key: "planungsstand",
            title: "Schritt 4: Planungsstand (optional)",
            body: `Dieser Schritt zeigt dieselbe Planungsstand-Ansicht wie die Projektdetailseite. Über **„Bearbeiten"** öffnet sich der Drawer, in dem du Phase, Vertrauen, Beobachtungen sowie die Parallelspuren (Planfeststellung, parlamentarische Befassung) manuell einträgst.

Wie aus Beobachtungen der angezeigte Stand entsteht, erklärt die Anleitung [So funktioniert der Projektfortschritt](/admin/anleitungen/projektfortschritt). Alles hier Erfasste ist später jederzeit in der Projektansicht änderbar.`,
        },
        {
            key: "verknuepfen",
            title: "Schritt 5 & 6: FinVes und VIB verknüpfen (optional)",
            body: `Beide Schritte verknüpfen das neue Projekt mit bereits importierten Quelldaten:

- **FinVes**: bestehende Finanzierungsvereinbarungen im Suchfeld auswählen und mit **„Verknüpfen & Weiter"** zuordnen.
- **VIB**: bestehende VIB-Einträge (Format \`[Berichtsjahr] Vorhabenname\`) auswählen und mit **„Verknüpfen & Fertig"** zuordnen.

Aus beiden Verknüpfungen werden **automatisch Beobachtungen** (\`FinVe\`, \`VIB\`) für den Planungsstand abgeleitet. Fehlen die Quelldaten noch, kannst du sie später über die Import-Workflows nachziehen — die Zuordnung ist auch von dort aus möglich ([VIB-Import](/admin/anleitungen/vib), [Haushalts-Import](/admin/haushalt-import/guide)).`,
        },
        {
            key: "fertigstellen",
            title: "Entwurf speichern oder fertigstellen",
            body: `Zum Abschluss hast du zwei Möglichkeiten:

- **„Als Entwurf speichern"** — das Projekt bleibt ein Entwurf (nicht öffentlich sichtbar) und liegt unter [Entwürfe](/admin/drafts). Von dort führt „Weiter bearbeiten" zurück in den Assistenten.
- **„Projekt fertigstellen"** — das Projekt wird **veröffentlicht** („Das Projekt ist jetzt veröffentlicht.") und du landest direkt auf seiner Projektdetailseite.

> [!green] Tipp
> Lieber früh fertigstellen und danach normal weiterpflegen: Alle Assistenten-Inhalte (Eigenschaften, Geometrie, Planungsstand, Verknüpfungen) sind auf der Projektdetailseite genauso editierbar.`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-entwurf-finden",
            title: "Wo finde ich einen angefangenen Entwurf wieder?",
            body: `Unter [Entwürfe](/admin/drafts) — dort liegen alle noch nicht fertiggestellten Projekte, auch die aus Import-Workflows („Projekt fehlt?") entstandenen. „Weiter bearbeiten" öffnet den Assistenten mit dem gespeicherten Stand.`,
        },
        {
            key: "ts-unterprojekt",
            title: "Mehrere Abschnitte: ein Projekt oder viele?",
            body: `Projekte mit mehreren Planfeststellungsabschnitten werden als **ein übergeordnetes Projekt plus je ein Unterprojekt pro Abschnitt** modelliert: Zuerst das übergeordnete Projekt anlegen, dann pro Abschnitt ein weiteres Projekt mit gesetztem „Übergeordnetes Projekt". Der Planungsstand wird nur an den Abschnitten (Blättern) gepflegt; das übergeordnete Projekt zeigt automatisch die Spanne.`,
        },
    ],
};

export default function ProjektAnlegenGuidePage() {
    return <GuideRenderer def={DEF} />;
}
