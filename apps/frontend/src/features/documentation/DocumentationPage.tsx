import { Anchor, Badge, Group, List, Paper, Stack, Text, Title } from "@mantine/core";
import { featureHighlights, qualityGates, techStack, workflows } from "./documentationData";

export default function DocumentationPage() {
    return (
        <Stack gap="xl" p={{ base: "xs", sm: "xl" }} maw={960} mx="auto">
            <Stack gap="xs">
                <Title order={1}>Railway dashboard – feature & developer documentation</Title>
                <Text c="dimmed">
                    This page complements the <Anchor component="a" href="/README.md" target="_blank">README</Anchor> and
                    outlines the currently available features, workflows, and quality requirements of the frontend.
                    Refresh the content whenever functionality, scripts, or integration points change.
                </Text>
            </Stack>

            <Paper withBorder p="var(--card-pad)">
                <Stack gap="sm">
                    <Group justify="space-between" align="flex-start">
                        <Title order={2}>Technology stack</Title>
                        <Badge variant="outline">Updated: {new Date().getFullYear()}</Badge>
                    </Group>
                    <List spacing="xs">
                        {techStack.map((entry) => (
                            <List.Item key={entry}>{entry}</List.Item>
                        ))}
                    </List>
                </Stack>
            </Paper>

            <Stack gap="md">
                <Title order={2}>Feature highlights</Title>
                {featureHighlights.map((feature) => (
                    <Paper withBorder p="var(--card-pad)" key={feature.title}>
                        <Stack gap="xs">
                            <Group gap="xs">
                                <Text fw={600} size="lg">{feature.title}</Text>
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
                    </Paper>
                ))}
            </Stack>

            <Stack gap="lg">
                {workflows.map((workflow) => (
                    <Paper withBorder p="var(--card-pad)" key={workflow.title}>
                        <Stack gap="xs">
                            <Text fw={600} size="lg">{workflow.title}</Text>
                            <List spacing="xs" type="ordered">
                                {workflow.steps.map((step) => (
                                    <List.Item key={step}>{step}</List.Item>
                                ))}
                            </List>
                        </Stack>
                    </Paper>
                ))}

                <Paper withBorder p="var(--card-pad)">
                    <Stack gap="xs">
                        <Group gap="xs">
                            <Text fw={600} size="lg">Quality requirements</Text>
                            <Badge variant="outline">mandatory</Badge>
                        </Group>
                        <List spacing="xs">
                            {qualityGates.map((gate) => (
                                <List.Item key={gate}>{gate}</List.Item>
                            ))}
                        </List>
                    </Stack>
                </Paper>
            </Stack>

            <Paper withBorder p="var(--card-pad)">
                <Stack gap="xs">
                    <Text fw={600} size="lg">Further resources</Text>
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
            </Paper>
        </Stack>
    );
}
