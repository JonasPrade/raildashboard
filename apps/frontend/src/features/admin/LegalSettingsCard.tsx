import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import {
    Button,
    Group,
    Paper,
    SimpleGrid,
    Stack,
    Text,
    Textarea,
    TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import {
    useAppSettings,
    useUpdateAppSettings,
    type AppSettings,
    type AppSettingsUpdatePayload,
} from "../../shared/api/queries";
import { LEGAL_SETTINGS_ANCHOR } from "../legal/legal";

type LegalFields = {
    impressum_url: string;
    impressum_markdown: string;
    datenschutz_url: string;
    datenschutz_markdown: string;
};

const FIELD_KEYS = ["impressum_url", "impressum_markdown", "datenschutz_url", "datenschutz_markdown"] as const;

const URL_HINT = "URL gesetzt → Weiterleitung, sonst eigene Seite";

function fromSettings(settings: AppSettings | undefined): LegalFields {
    return {
        impressum_url: settings?.impressum_url ?? "",
        impressum_markdown: settings?.impressum_markdown ?? "",
        datenschutz_url: settings?.datenschutz_url ?? "",
        datenschutz_markdown: settings?.datenschutz_markdown ?? "",
    };
}

function urlError(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    try {
        const parsed = new URL(trimmed);
        if (parsed.protocol === "http:" || parsed.protocol === "https:") return null;
    } catch {
        // fall through
    }
    return "Adresse muss mit http:// oder https:// beginnen";
}

/**
 * Admin card for Impressum and Datenschutz (docs/features/feature-idt-design.md → W8).
 * Shown on /admin for users with settings.manage; the empty state of /impressum
 * and /datenschutz links here via #impressum-datenschutz.
 */
export function LegalSettingsCard() {
    const { data: settings } = useAppSettings();
    const updateSettings = useUpdateAppSettings();
    const [values, setValues] = useState<LegalFields>(() => fromSettings(settings));
    const [seeded, setSeeded] = useState(settings !== undefined);
    const ref = useRef<HTMLDivElement>(null);
    const location = useLocation();

    // Seed the form once the settings arrive (the card may mount before they load).
    useEffect(() => {
        if (!seeded && settings) {
            setValues(fromSettings(settings));
            setSeeded(true);
        }
    }, [seeded, settings]);

    useEffect(() => {
        if (location.hash === `#${LEGAL_SETTINGS_ANCHOR}`) {
            ref.current?.scrollIntoView?.({ block: "start" });
        }
    }, [location.hash]);

    const saved = fromSettings(settings);
    const dirty = FIELD_KEYS.some((key) => values[key] !== saved[key]);
    const impressumUrlError = urlError(values.impressum_url);
    const datenschutzUrlError = urlError(values.datenschutz_url);
    const invalid = impressumUrlError !== null || datenschutzUrlError !== null;

    const set = (key: keyof LegalFields) => (event: { currentTarget: { value: string } }) => {
        const value = event.currentTarget.value;
        setValues((prev) => ({ ...prev, [key]: value }));
    };

    const handleSave = () => {
        // Empty strings clear a field on the server.
        const payload: AppSettingsUpdatePayload = {};
        for (const key of FIELD_KEYS) {
            if (values[key] !== saved[key]) payload[key] = values[key].trim();
        }
        updateSettings.mutate(payload, {
            onSuccess: (result) => {
                setValues(fromSettings(result));
                notifications.show({
                    color: "green",
                    title: "Gespeichert",
                    message: "Impressum und Datenschutz wurden gespeichert.",
                });
            },
            onError: () =>
                notifications.show({
                    color: "red",
                    title: "Fehler",
                    message: "Impressum und Datenschutz konnten nicht gespeichert werden.",
                }),
        });
    };

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md" id={LEGAL_SETTINGS_ANCHOR} ref={ref} style={{ scrollMarginTop: 80 }}>
                <Stack gap={4}>
                    <Text component="h2" fw={700} m={0} size="lg">
                        Impressum und Datenschutz
                    </Text>
                    <Text size="sm" c="dimmed">
                        Inhalt der Seiten „Impressum“ und „Datenschutz“, die in der Fußzeile verlinkt sind.
                    </Text>
                </Stack>
                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
                    <Stack gap="sm">
                        <TextInput
                            label="Impressum – URL"
                            description={URL_HINT}
                            placeholder="https://…"
                            value={values.impressum_url}
                            onChange={set("impressum_url")}
                            error={impressumUrlError}
                            maxLength={500}
                        />
                        <Textarea
                            label="Impressum – Text (Markdown)"
                            value={values.impressum_markdown}
                            onChange={set("impressum_markdown")}
                            autosize
                            minRows={6}
                            maxRows={20}
                        />
                    </Stack>
                    <Stack gap="sm">
                        <TextInput
                            label="Datenschutz – URL"
                            description={URL_HINT}
                            placeholder="https://…"
                            value={values.datenschutz_url}
                            onChange={set("datenschutz_url")}
                            error={datenschutzUrlError}
                            maxLength={500}
                        />
                        <Textarea
                            label="Datenschutz – Text (Markdown)"
                            value={values.datenschutz_markdown}
                            onChange={set("datenschutz_markdown")}
                            autosize
                            minRows={6}
                            maxRows={20}
                        />
                    </Stack>
                </SimpleGrid>
                <Group justify="flex-end">
                    <Button
                        onClick={handleSave}
                        loading={updateSettings.isPending}
                        disabled={!dirty || invalid}
                    >
                        Speichern
                    </Button>
                </Group>
            </Stack>
        </Paper>
    );
}
