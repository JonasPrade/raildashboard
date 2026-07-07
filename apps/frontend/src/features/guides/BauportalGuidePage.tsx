import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "bauportal",
    title: "Anleitung: DB-Bauportal abrufen",
    chip: "Schritt für Schritt",
    intro: `Wie du den aktuellen Bau- und Planungsstand aus der offenen Bauportal-API der Deutschen Bahn abrufst, prüfst und den Projekten zuordnest.`,
    prerequisites: `- Du bist als **Editor** oder **Admin** eingeloggt (Recht „Planungsstand bearbeiten").
- Die Bauportal-API ist vom Server aus erreichbar.`,
    steps: [
        {
            key: "abrufen",
            title: "Aktuellen Stand abrufen",
            body: `Gehe zu [DB-Bauportal](/admin/bauportal-import) und klicke auf **„Bauportal abrufen"**. Das Dashboard holt die aktuellen Einträge aus der offenen Bauportal-API der Deutschen Bahn.

Die Meldung nach dem Abruf zeigt, wie viele Einträge insgesamt geholt, neu angelegt und aktualisiert wurden. Ein erneuter Abruf ist jederzeit möglich und aktualisiert bestehende Einträge (Status/Zeitangaben), ohne deine bestätigten Zuordnungen zu verlieren.`,
        },
        {
            key: "pruefen",
            title: "Vorschläge prüfen und Projekte zuordnen",
            body: `Die Tabelle zeigt pro Bauportal-Eintrag: den Kurztitel (mit Link zum Bauportal), die abgeleitete **Phase**, den Bauzeitraum und ein Feld zur Projektzuordnung.

- Die Phase wird aus dem Bauportal-Status gemappt (z. B. \`Bau\`, \`In Betrieb\`). Steht dort **„kein Beitrag"**, liefert der Status keine verwertbare Phase — solche Einträge müssen nicht übernommen werden.
- Ein \`✦\`-Vorschlag ist bereits vorbelegt. Prüfe ihn, passe ihn im Auswahlfeld an oder entferne ihn.
- Gibt es das Projekt noch nicht, kannst du über **„Projekt fehlt?"** direkt einen **Projekt-Entwurf** anlegen; er wird dem Eintrag zugeordnet und bleibt zunächst unbestätigt (fertigstellen: [Anleitung: Projekt anlegen](/admin/anleitungen/projekt-anlegen)).
- Mit dem Schalter **„Nur offene (unbestätigt)"** blendest du bereits übernommene Einträge aus, um den Rest abzuarbeiten.`,
            exampleKey: "bauportal-table",
        },
        {
            key: "uebernehmen",
            title: "Übernehmen",
            body: `Mit **„Alle übernehmen (N)"** bestätigst du auf einen Schlag alle zugeordneten, noch offenen Einträge. N zeigt an, wie viele bereit sind (zugeordnet und unbestätigt). Zuordnungen lassen sich auch nach dem Übernehmen weiter anpassen.

> [!blue] Was dabei entsteht
> Jede bestätigte Zuordnung erzeugt eine abgeleitete **Beobachtung** mit der Quelle \`Bauportal\`. Wie stark sie den angezeigten Stand beeinflusst, entscheidet die [glaubwürdigkeitsbasierte Ableitung](/admin/anleitungen/projektfortschritt) (Vertrauen je Quelle × Aktualität).`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-api-down",
            title: '„Abruf fehlgeschlagen — API nicht erreichbar"',
            body: `Die Bauportal-API antwortet nicht (temporär offline oder vom Server aus nicht erreichbar). Später erneut versuchen; besteht das Problem fort, einen Administrator hinzuziehen.`,
        },
        {
            key: "ts-kein-beitrag",
            title: 'Ein Eintrag zeigt „kein Beitrag"',
            body: `Der Bauportal-Status lässt sich nicht auf eine Leistungsphase abbilden (z. B. rein informative Einträge). Solche Zeilen liefern keine sinnvolle Beobachtung und können offen bleiben.`,
        },
    ],
};

export default function BauportalGuidePage() {
    return <GuideRenderer def={DEF} />;
}
