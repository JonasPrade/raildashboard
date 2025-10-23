import { Anchor, Badge, Card, Divider, Group, List, Stack, Text, Title } from "@mantine/core";
import { featureHighlights, qualityGates, techStack, workflows } from "./documentationData";

export default function DocumentationPage() {
    return (
        <Stack gap="xl" p="xl" maw={960} mx="auto">
            <Stack gap="xs">
                <Title order={1}>Railway dashboard – feature & developer documentation</Title>
                <Text c="dimmed">
                    This page complements the <Anchor component="a" href="/README.md" target="_blank">README</Anchor> and
                    outlines the currently available features, workflows, and quality requirements of the frontend.
                    Refresh the content whenever functionality, scripts, or integration points change.
                </Text>
            </Stack>

            <Card withBorder shadow="sm" radius="md" padding="xl">
                <Stack gap="sm">
                    <Group justify="space-between" align="flex-start">
                        <Title order={2}>Technology stack</Title>
                        <Badge color="petrol" variant="light">Updated: {new Date().getFullYear()}</Badge>
                    </Group>
                    <List spacing="xs">
                        {techStack.map((entry) => (
                            <List.Item key={entry}>{entry}</List.Item>
                        ))}
                    </List>
                </Stack>
            </Card>

            <Stack gap="md">
                <Title order={2}>Feature highlights</Title>
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

            <Divider label="Workflows & quality" labelPosition="center" my="lg" />

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
                            <Title order={3}>Quality requirements</Title>
                            <Badge color="green" variant="light">
                                mandatory
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
                    <Title order={3}>Further resources</Title>
                    <List spacing="xs">
                        <List.Item>
                            <Anchor component="a" href="/README.md" target="_blank" rel="noopener noreferrer">
                                Open the project README
                            </Anchor>
                        </List.Item>
                        <List.Item>
                            <Text span fw={500}>
                                Routes:
                            </Text>{" "}
                            <Text span>/ (map view), /documentation (this page)</Text>
                        </List.Item>
                        <List.Item>
                            <Text span fw={500}>
                                Scripts:
                            </Text>{" "}
                            <Text span>`npm run dev`, `npm run build`, `npm run preview`, `npm run gen:api`, `npm run gen:zod`</Text>
                        </List.Item>
                    </List>
                </Stack>
            </Card>
        </Stack>
    );
}
