import { Accordion, Alert, Anchor, Box, Container, Group, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { ChronicleHeadline, ChronicleDataChip } from "../../components/chronicle";
import { useAuth } from "../../lib/auth";
import { useGuideOverrides, type GuideOverride } from "../../shared/api/queries";
import type { GuideDef, GuideSection } from "./guideContent";
import GuideSectionBody from "./GuideSectionBody";
import GuideExampleView from "./GuideExampleView";
import { GUIDE_EXAMPLES } from "./guideExamples";

/**
 * Standard guide-page skeleton (see guideContent.ts): back link, headline +
 * chip, editable intro, green prerequisites alert, numbered steps accordion
 * and an optional contained troubleshooting accordion. Every text body is a
 * markdown section that "guides.edit" users can override in-app; example views
 * are code and stay read-only.
 */
export default function GuideRenderer({ def }: { def: GuideDef }) {
    const { can } = useAuth();
    const canEdit = can("guides.edit");
    const { data: overrides } = useGuideOverrides(def.slug);

    const overrideFor = (key: string): GuideOverride | undefined =>
        overrides?.find((o) => o.section_key === key);

    const sectionBody = (section: GuideSection, dimmed?: boolean) => (
        <GuideSectionBody
            guideSlug={def.slug}
            sectionKey={section.key}
            defaultBody={section.body}
            override={overrideFor(section.key)}
            canEdit={canEdit}
            dimmed={dimmed}
        />
    );

    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Anchor component={Link} to="/admin/anleitungen" size="sm">
                        ← Alle Anleitungen
                    </Anchor>
                    <Group gap="xs" align="center">
                        <ChronicleHeadline as="h1">{def.title}</ChronicleHeadline>
                        <ChronicleDataChip>{def.chip}</ChronicleDataChip>
                    </Group>
                    <GuideSectionBody
                        guideSlug={def.slug}
                        sectionKey="intro"
                        defaultBody={def.intro}
                        override={overrideFor("intro")}
                        canEdit={canEdit}
                        dimmed
                    />
                </Stack>

                {def.prerequisites && (
                    <Alert color="green" variant="light" title="Voraussetzungen">
                        <Box mt="xs">
                            <GuideSectionBody
                                guideSlug={def.slug}
                                sectionKey="voraussetzungen"
                                defaultBody={def.prerequisites}
                                override={overrideFor("voraussetzungen")}
                                canEdit={canEdit}
                            />
                        </Box>
                    </Alert>
                )}

                <Accordion variant="separated" radius="md" defaultValue={def.steps[0]?.key}>
                    {def.steps.map((step, idx) => (
                        <Accordion.Item key={step.key} value={step.key}>
                            <Accordion.Control>
                                <Group gap="sm" align="center">
                                    <ChronicleDataChip>{idx + 1}</ChronicleDataChip>
                                    <Text fw={500}>{step.title}</Text>
                                </Group>
                            </Accordion.Control>
                            <Accordion.Panel>
                                <Box pl="md" pt="xs" pb="xs">
                                    {sectionBody(step)}
                                    {step.exampleKey && GUIDE_EXAMPLES[step.exampleKey] && (
                                        <GuideExampleView>
                                            {GUIDE_EXAMPLES[step.exampleKey]}
                                        </GuideExampleView>
                                    )}
                                </Box>
                            </Accordion.Panel>
                        </Accordion.Item>
                    ))}
                </Accordion>

                {def.troubleshooting && def.troubleshooting.length > 0 && (
                    <Accordion variant="contained" radius="md">
                        {def.troubleshooting.map((item) => (
                            <Accordion.Item key={item.key} value={item.key}>
                                <Accordion.Control>
                                    <Text size="sm" fw={500}>
                                        {item.title}
                                    </Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    {sectionBody(item)}
                                    {item.exampleKey && GUIDE_EXAMPLES[item.exampleKey] && (
                                        <GuideExampleView>
                                            {GUIDE_EXAMPLES[item.exampleKey]}
                                        </GuideExampleView>
                                    )}
                                </Accordion.Panel>
                            </Accordion.Item>
                        ))}
                    </Accordion>
                )}
            </Stack>
        </Container>
    );
}
