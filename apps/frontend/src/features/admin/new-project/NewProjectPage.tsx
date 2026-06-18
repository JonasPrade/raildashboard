import { Alert, Button, Container, Group, Loader, Stack, Stepper, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../../lib/auth";
import { useFinalizeProject, useProject, type Project } from "../../../shared/api/queries";
import Step1Stammdaten from "./Step1Stammdaten";
import Step2Geometrie from "./Step2Geometrie";
import Step3Properties from "./Step3Properties";
import Step4Finves from "./Step4Finves";
import Step5Vib from "./Step5Vib";

export default function NewProjectPage() {
    const { can } = useAuth();
    const navigate = useNavigate();
    const params = useParams();
    const resumeId = params.projectId != null ? Number(params.projectId) : null;

    const [active, setActive] = useState(0);
    const [project, setProject] = useState<Project | null>(null);

    // Resume mode: load the existing draft and seed the wizard state once.
    const resumeQuery = useProject(resumeId ?? NaN);
    useEffect(() => {
        if (resumeId != null && resumeQuery.data && project == null) {
            setProject(resumeQuery.data);
        }
    }, [resumeId, resumeQuery.data, project]);

    const finalize = useFinalizeProject();

    const handleSaveDraft = () => {
        notifications.show({
            color: "blue",
            title: "Als Entwurf gespeichert",
            message: "Das Projekt bleibt ein Entwurf und kann später fertiggestellt werden.",
        });
        navigate("/admin/drafts");
    };

    const handleFinalize = async () => {
        if (project?.id == null) return;
        try {
            await finalize.mutateAsync(project.id);
            notifications.show({
                color: "green",
                title: "Projekt fertiggestellt",
                message: "Das Projekt ist jetzt veröffentlicht.",
            });
            navigate(`/projects/${project.id}`);
        } catch {
            notifications.show({
                color: "red",
                title: "Fehler",
                message: "Das Projekt konnte nicht fertiggestellt werden.",
            });
        }
    };

    if (!can("project.create")) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    if (resumeId != null && project == null) {
        if (resumeQuery.isError) {
            return (
                <Container size="sm" py="xl">
                    <Alert color="red" variant="light" title="Entwurf nicht gefunden">
                        Der gewünschte Entwurf konnte nicht geladen werden.
                    </Alert>
                </Container>
            );
        }
        return (
            <Container size="sm" py="xl">
                <Group justify="center"><Loader /></Group>
            </Container>
        );
    }

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Title order={2}>{resumeId != null ? "Entwurf weiter bearbeiten" : "Neues Projekt anlegen"}</Title>
                {/* Steps become clickable once the project exists (created in step 1),
                    so the user can jump freely between stages. */}
                <Stepper
                    active={active}
                    onStepClick={project != null ? setActive : undefined}
                    allowNextStepsSelect={project != null}
                >
                    <Stepper.Step label="Stammdaten" description="Pflicht">
                        <Step1Stammdaten
                            project={project}
                            onCreated={(p) => {
                                setProject(p);
                                setActive(1);
                            }}
                        />
                    </Stepper.Step>
                    <Stepper.Step label="Geometrie" description="Optional">
                        {project?.id != null && (
                            <Step2Geometrie project={project} onProjectChange={setProject} />
                        )}
                    </Stepper.Step>
                    <Stepper.Step label="Eigenschaften" description="Optional">
                        {project && (
                            <Step3Properties
                                project={project}
                                onDone={(updated) => {
                                    setProject(updated);
                                    setActive(3);
                                }}
                            />
                        )}
                    </Stepper.Step>
                    <Stepper.Step label="FinVes" description="Optional">
                        {project?.id != null && (
                            <Step4Finves projectId={project.id} onDone={() => setActive(4)} />
                        )}
                    </Stepper.Step>
                    <Stepper.Step label="VIB" description="Optional">
                        {project?.id != null && (
                            <Step5Vib projectId={project.id} onDone={handleFinalize} />
                        )}
                    </Stepper.Step>
                </Stepper>
                {project && (
                    <Group justify="space-between">
                        <Button
                            variant="subtle"
                            onClick={() => setActive((s) => Math.max(0, s - 1))}
                            disabled={active === 0}
                        >
                            Zurück
                        </Button>
                        <Group>
                            <Button
                                variant="default"
                                onClick={() => setActive((s) => s + 1)}
                                disabled={active >= 4}
                            >
                                Weiter
                            </Button>
                            <Button variant="subtle" onClick={handleSaveDraft} disabled={finalize.isPending}>
                                Als Entwurf speichern
                            </Button>
                            <Button onClick={handleFinalize} loading={finalize.isPending}>
                                Projekt fertigstellen
                            </Button>
                        </Group>
                    </Group>
                )}
            </Stack>
        </Container>
    );
}
