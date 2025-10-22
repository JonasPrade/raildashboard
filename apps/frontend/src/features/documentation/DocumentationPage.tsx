import { Anchor, Badge, Card, Divider, Group, List, Stack, Text, Title } from "@mantine/core";
import { featureHighlights, qualityGates, techStack, workflows } from "./documentationData";

export default function DocumentationPage() {
    return (
        <Stack gap="xl" p="xl" maw={960} mx="auto">
            <Stack gap="xs">
                <Title order={1}>Schienendashboard – Funktions- & Entwicklerdokumentation</Title>
                <Text c="dimmed">
                    Diese Seite ergänzt das <Anchor component="a" href="/README.md" target="_blank">README</Anchor> und
                    beschreibt die derzeit verfügbaren Features, Workflows und Qualitätsanforderungen des Frontends.
                    Aktualisiert die Inhalte, sobald sich Funktionen, Skripte oder Integrationspunkte ändern.
                </Text>
            </Stack>

            <Card withBorder shadow="sm" radius="md" padding="xl">
                <Stack gap="sm">
                    <Group justify="space-between" align="flex-start">
                        <Title order={2}>Technologie-Stack</Title>
                        <Badge color="petrol" variant="light">Stand: {new Date().getFullYear()}</Badge>
                    </Group>
                    <List spacing="xs">
                        {techStack.map((entry) => (
                            <List.Item key={entry}>{entry}</List.Item>
                        ))}
                    </List>
                </Stack>
            </Card>

            <Stack gap="md">
                <Title order={2}>Feature-Highlights</Title>
                {featureHighlights.map((feature) => (
                    <Card key={feature.title} withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="xs">
                            <Group gap="xs">
                                <Title order={3}>{feature.title}</Title>
                            </Group>
                            <Text>{feature.description}</Text>
                            {feature.details && (
                                <List spacing="xs">
                                    {feature.details.map((detail) => (
                                        <List.Item key={detail}>{detail}</List.Item>
                                    ))}
                                </List>
                            )}
                        </Stack>
                    </Card>
                ))}
            </Stack>

            <Divider label="Workflows & Qualität" labelPosition="center" my="lg" />

            <Stack gap="lg">
                {workflows.map((workflow) => (
                    <Card key={workflow.title} withBorder radius="md" padding="lg">
                        <Stack gap="xs">
                            <Title order={3}>{workflow.title}</Title>
                            <List spacing="xs" type="ordered">
                                {workflow.steps.map((step) => (
                                    <List.Item key={step}>{step}</List.Item>
                                ))}
                            </List>
                        </Stack>
                    </Card>
                ))}

                <Card withBorder radius="md" padding="lg" shadow="xs">
                    <Stack gap="xs">
                        <Group gap="xs">
                            <Title order={3}>Qualitätsanforderungen</Title>
                            <Badge color="green" variant="light">
                                verpflichtend
                            </Badge>
                        </Group>
                        <List spacing="xs">
                            {qualityGates.map((gate) => (
                                <List.Item key={gate}>{gate}</List.Item>
                            ))}
                        </List>
                    </Stack>
                </Card>
            </Stack>

            <Card withBorder radius="md" padding="lg">
                <Stack gap="xs">
                    <Title order={3}>Weiterführende Ressourcen</Title>
                    <List spacing="xs">
                        <List.Item>
                            <Anchor component="a" href="/README.md" target="_blank" rel="noopener noreferrer">
                                Projekt-README öffnen
                            </Anchor>
                        </List.Item>
                        <List.Item>
                            <Text span fw={500}>
                                Routenübersicht:
                            </Text>{" "}
                            <Text span>/ (Kartenansicht), /dokumentation (diese Seite)</Text>
                        </List.Item>
                        <List.Item>
                            <Text span fw={500}>
                                Skripte:
                            </Text>{" "}
                            <Text span>`npm run dev`, `npm run build`, `npm run preview`, `npm run gen:api`, `npm run gen:zod`</Text>
                        </List.Item>
                    </List>
                </Stack>
            </Card>
        </Stack>
    );
}
