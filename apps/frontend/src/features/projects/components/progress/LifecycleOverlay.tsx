import { Alert, Anchor, Stack, Text } from "@mantine/core";
import { Ban, Pause, Replace } from "lucide-react";
import { Link } from "react-router-dom";

import { formatDateShort } from "../../../../shared/format";
import { LIFECYCLE_LABEL, type LifecycleStatus } from "./phaseMeta";

export type LifecycleProjectRef = { id: number; name: string; project_number?: string | null };

type Props = {
    status: LifecycleStatus;
    note?: string | null;
    date?: string | null;
    /** ERSETZT: the successor (null when it was deleted). */
    replacedBy?: LifecycleProjectRef | null;
    /** Projects that name this one as their successor. */
    replaces?: LifecycleProjectRef[];
};

const TEXT: Record<Exclude<LifecycleStatus, "AKTIV">, string> = {
    PAUSIERT: "Dieses Projekt ist derzeit pausiert. Der zuletzt bekannte Planungsstand bleibt erhalten.",
    ABGEBROCHEN:
        "Dieses Projekt wurde abgebrochen. Der zuletzt bekannte Planungsstand bleibt zur Information erhalten.",
    ERSETZT:
        "Dieses Projekt wird nicht mehr in dieser Form verfolgt. Der zuletzt bekannte Planungsstand bleibt zur Information erhalten; maßgeblich sind die Angaben beim Nachfolger.",
};

function ProjectLink({ project }: { project: LifecycleProjectRef }) {
    return (
        <Anchor component={Link} to={`/projects/${project.id}`} fw={600}>
            {project.name}
            {project.project_number ? ` (${project.project_number})` : ""}
        </Anchor>
    );
}

/** Banner of the lifecycle overlay (PAUSIERT/ABGEBROCHEN/ERSETZT) with reason,
 * date and — for a replaced project — the link to its successor; on the
 * successor a hint links back to the projects it replaces
 * (docs/features/feature-project-replacement.md). Renders nothing for an active
 * project that replaces nothing. The phase stepper is dimmed separately. */
export default function LifecycleOverlay({ status, note, date, replacedBy, replaces = [] }: Props) {
    const backReference =
        replaces.length > 0 ? (
            <Alert color="teal" variant="light" icon={<Replace size={16} />} title="Nachfolgeprojekt">
                <Text size="sm">
                    Ersetzt{" "}
                    {replaces.map((project, index) => (
                        <span key={project.id}>
                            {index > 0 && ", "}
                            <ProjectLink project={project} />
                        </span>
                    ))}
                    .
                </Text>
            </Alert>
        ) : null;
    if (status === "AKTIV") return backReference;

    const icon = status === "PAUSIERT" ? <Pause size={16} /> : status === "ERSETZT" ? <Replace size={16} /> : <Ban size={16} />;
    return (
        <Stack gap="sm">
            <Alert
                // Lifecycle is no "Versäumnis": neutral alert, the icon tells the states apart.
                color="teal"
                variant="light"
                icon={icon}
                title={`Projekt ${LIFECYCLE_LABEL[status]}`}
            >
                <Stack gap={4}>
                    {status === "ERSETZT" && (
                        <Text size="sm">
                            Ersetzt durch{" "}
                            {replacedBy ? <ProjectLink project={replacedBy} /> : "ein nicht mehr vorhandenes Projekt"}
                            {date ? ` (seit ${formatDateShort(date)})` : ""}.
                        </Text>
                    )}
                    <Text size="sm">{TEXT[status]}</Text>
                    {status !== "ERSETZT" && date && <Text size="sm">Seit {formatDateShort(date)}.</Text>}
                    {note && (
                        <Text size="sm" c="dimmed">
                            Begründung: {note}
                        </Text>
                    )}
                </Stack>
            </Alert>
            {backReference}
        </Stack>
    );
}
