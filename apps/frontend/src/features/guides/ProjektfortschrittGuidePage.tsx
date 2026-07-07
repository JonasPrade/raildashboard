import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "projektfortschritt",
    title: "So funktioniert der Projektfortschritt",
    chip: "Grundlagen",
    intro: `Das mentale Modell hinter dem Planungsstand: Wie aus mehreren, teils widersprüchlichen Quellen ein nachvollziehbarer, angezeigter Stand entsteht — und wo du eingreifen kannst.`,
    steps: [
        {
            key: "grundprinzip",
            title: "Grundprinzip: abgeleitet, nicht eingetragen",
            body: `Ein Projekt hat **kein** einzelnes „Status"-Feld, das man von Hand setzt. Stattdessen sammelt das Dashboard **Beobachtungen** aus mehreren Quellen und leitet daraus einen angezeigten Planungsstand ab. So bleiben widersprüchliche Quellen sichtbar, statt sich gegenseitig zu überschreiben.

Jede Beobachtung ist ein Tupel aus *Quelle, Spur, behauptetem Zustand, Beobachtungsdatum und Konfidenz*. Der angezeigte Stand („Headline") ist immer das Ergebnis einer Ableitung über alle Beobachtungen — nie ein direkt gespeicherter Wert.`,
        },
        {
            key: "leistungsphasen",
            title: "Die Leistungsphasen (Hauptspur)",
            body: `Die Hauptspur ist eine lineare, immer vorhandene Kette von fünf Phasen:

- \`Nicht gestartet\`
- \`Vorplanung\` (Lph 1–2)
- \`Genehmigungsplanung\` (Lph 3–4)
- \`Bau\`
- \`In Betrieb\` (faktisch abgeschlossen, grün)

Dargestellt als horizontaler Verlauf mit Kreisen und Pfeilen. Manuelle Beobachtungen erfassen **ausschließlich** diese Leistungsphasen.`,
        },
        {
            key: "verfahren",
            title: "Begleitende Verfahren: Planfeststellung & Parl. Befassung",
            body: `Zwei Verfahren laufen parallel zur Hauptspur und werden als **Meilenstein-Rauten** auf der Zeitleiste angezeigt (grün = abgeschlossen + Datum, blau = läuft, Umriss = offen):

- **Planfeststellung (PFB)** — Raute zwischen Genehmigungsplanung und Bau (das rechtliche Tor zum Bau). Nur sichtbar, wenn „hat PF" gesetzt ist; das Flag setzt sich *automatisch*, sobald PF-Daten (Zustand/Datum/Link) erfasst werden.
- **Parlamentarische Befassung** — Raute zwischen Vorplanung und Genehmigungsplanung. Voreinstellung kommt aus der Projektgruppe (Bedarfsplan Schiene / BSWAG → an), manuell übersteuerbar.

> [!blue] Wo erfassen?
> Beide Verfahren pflegst du im Bearbeiten-Drawer über das Schaltmenü „Verfahren" (Switch je Verfahren, mit Zustand, Datum, Anmerkung und Links) — **nicht** über eine manuelle Beobachtung.`,
            exampleKey: "projektfortschritt-stepper",
        },
        {
            key: "quellen",
            title: "Woher die Beobachtungen kommen (Quellen)",
            body: `Es gibt sechs Quellentypen:

- \`VIB\` und \`FinVe\` — importiert und m:n mit Projekten verknüpft; Beobachtungen werden daraus *automatisch abgeleitet* ([VIB-Import-Anleitung](/admin/anleitungen/vib)).
- \`Fulda-Runde\`, \`Bauportal\` und \`Medien\` — werden über die jeweiligen Import-Workflows gepflegt ([Fulda](/admin/anleitungen/fulda), [Bauportal](/admin/anleitungen/bauportal), [Medien](/admin/anleitungen/medien)).
- \`Manuell\` — redaktionelle Beobachtung, die du direkt am Projekt erfasst (Phase + Datum, optional als „erwartet").`,
        },
        {
            key: "ableitung",
            title: "Wie der angezeigte Stand entsteht (Hybrid-Ableitung)",
            body: `Maßgeblich ist die **glaubwürdigste** Beobachtung: Unter allen Hauptspur-Beobachtungen über der Glaubwürdigkeitsschwelle gewinnt die mit der **höchsten effektiven Konfidenz** — ihre Phase wird zur Headline. Entscheidend ist die Konfidenz, *nicht* die Phasen-Reihenfolge.

Die effektive Konfidenz = Default-Vertrauen je Quellentyp × Aktualitätsverfall (*recency decay*). Deshalb verliert der „immer veraltete" VIB mit der Zeit an Gewicht, und eine frische redaktionelle Korrektur schlägt ein schwaches Automatik-Signal.

> [!yellow] Bewusster Trade-off
> Ein frisches, schwach gewichtetes Signal kann ein älteres, höheres überstimmen — der abgeleitete Stand kann für Automatik-Quellen also auch „zurückgehen". Das ist gewollt, damit aktuelle und menschliche Eingaben maßgeblich bleiben. Konflikte werden nie weggerechnet, sondern im Aufklappbereich transparent gezeigt.`,
        },
        {
            key: "lebenszyklus",
            title: "Lebenszyklus-Overlay: aktiv / pausiert / abgebrochen",
            body: `Orthogonal zur Phasenkette liegt ein Lebenszyklus-Zustand (\`Aktiv\` / \`Pausiert\` / \`Abgebrochen\`). Er wird nicht in die Phasen gemischt. Bei „Pausiert"/„Abgebrochen" wird die gesamte Darstellung überblendet (Banner + abgeblendeter Stepper); die zuletzt bekannte Phase bleibt erhalten.`,
        },
        {
            key: "aggregation",
            title: "Unterprojekte & Aggregation",
            body: `Projekte mit mehreren Planfeststellungsabschnitten sind als **Unterprojekte** modelliert. Der Fortschritt hängt immer am **Blatt-Projekt** (genau ein Stand). Ein übergeordnetes Projekt **aggregiert** seine Kinder und zeigt die Headline als **Spanne** (min..max über alle erreichbaren Blätter).

- Die Aggregation ist **rekursiv** über den ganzen Teilbaum (beliebige Tiefe), nicht nur eine Ebene.
- Nur echte Blätter tragen einen Zustand; Zwischenknoten spannen die Blätter unter sich.
- Ein **manueller Override an einem Zwischenknoten** fixiert den gesamten Teilbaum auf diese eine Phase.
- Ein direktes Kind, das selbst Superior ist, zeigt seine eigene Sub-Spanne (Badge „Gruppe").`,
        },
        {
            key: "prognose",
            title: "Prognose & erwartete Termine",
            body: `Neben dem aktuellen Stand zeigt der Aufklappbereich eine **Prognose** (Restdauer der aktuellen Phase + nächste Schritte). Konkrete Termine aus VIB-PFA und Fulda speisen die Prognose.

Eine manuelle Beobachtung kannst du als **„erwartet"** markieren (Phase + Datum). Erwartete Einträge fließen **nicht** in die Headline ein (sie verändern den heutigen Stand nicht), sondern übersteuern nur die Prognose.`,
        },
        {
            key: "eingreifen",
            title: "Wie du selbst eingreifst",
            body: `- **Manuelle Beobachtung** (Phase + Datum, optional „erwartet") am Projekt erfassen — hohe Konfidenz, schlägt bei Bedarf Automatik-Signale.
- **Phasen-Override** setzen, wenn der abgeleitete Vorschlag falsch ist — an einem Zwischenknoten fixiert er den ganzen Teilbaum.
- **Verfahren-Drawer** für Planfeststellung / Parl. Befassung pflegen.
- Neue Quelldaten über die Import-Workflows einspielen: [Haushalt](/admin/haushalt-import/guide), [Fulda-Runde](/admin/anleitungen/fulda), [Bauportal](/admin/anleitungen/bauportal), [VIB-Bericht](/admin/anleitungen/vib), [Medien/Presse](/admin/anleitungen/medien).`,
        },
    ],
};

export default function ProjektfortschrittGuidePage() {
    return <GuideRenderer def={DEF} />;
}
