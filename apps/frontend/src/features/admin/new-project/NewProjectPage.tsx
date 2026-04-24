import { Alert, Button, Container, Group, Stack, Stepper, Title } from "@mantine/core";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../../lib/auth";
import type { Project } from "../../../shared/api/queries";
import Step1Stammdaten from "./Step1Stammdaten";
import Step2Geometrie from "./Step2Geometrie";
import Step3Properties from "./Step3Properties";
import Step4Finves from "./Step4Finves";
import Step5Vib from "./Step5Vib";

export default function NewProjectPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [active, setActive] = useState(0);
    const [project, setProject] = useState<Project | null>(null);

    const handleFinish = () => {
        if (project?.id != null) navigate(`/projects/${project.id}`);
        else navigate("/admin/unassigned");
    };

    if (user === null || (user.role !== "editor" && user.role !== "admin")) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Title order={2}>Neues Projekt anlegen</Title>
                <Stepper active={active} allowNextStepsSelect={false}>
                    <Stepper.Step label="Stammdaten" description="Pflicht">
                        <Step1Stammdaten
                            onCreated={(p) => {
                                setProject(p);
                                setActive(1);
                            }}
                        />
                    </Stepper.Step>
                    <Stepper.Step label="Geometrie" description="Optional">
                        {project?.id != null && (
                            <Step2Geometrie projectId={project.id} onDone={() => setActive(2)} />
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
                            <Step5Vib projectId={project.id} onDone={handleFinish} />
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
                                variant="subtle"
                                onClick={() => setActive((s) => s + 1)}
                                disabled={active >= 4}
                            >
                                Überspringen
                            </Button>
                            <Button onClick={handleFinish}>Fertig</Button>
                        </Group>
                    </Group>
                )}
            </Stack>
        </Container>
    );
}
