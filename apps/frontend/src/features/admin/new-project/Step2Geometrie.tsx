import { Stack, Text } from "@mantine/core";

import type { Project } from "../../../shared/api/queries";
import GeometryEditor from "../../routing/GeometryEditor";

type Props = {
    project: Project;
    /** Called whenever the geometry was saved, with the updated project. */
    onProjectChange: (updatedProject: Project) => void;
};

export default function Step2Geometrie({ project, onProjectChange }: Props) {
    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">
                Lege eine Geometrie für dieses Projekt an (optional): Route zwischen Betriebsstellen
                berechnen, einzelne Betriebsstellen hinzufügen, eine GeoJSON-Datei hochladen oder
                Linien und Punkte direkt auf der Karte zeichnen. Du kannst nacheinander mehrere
                Geometrien ergänzen — nach dem Speichern bleibt der Editor offen. Mit „Zurück",
                „Überspringen" oder „Fertig" unten geht es weiter.
            </Text>
            <GeometryEditor
                project={project}
                onSaved={onProjectChange}
                onCancel={() => {}}
                showCancel={false}
                saveLabel="Geometrie speichern"
                height={560}
            />
        </Stack>
    );
}
