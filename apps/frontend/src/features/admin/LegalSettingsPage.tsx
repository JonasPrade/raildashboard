import { Link } from "react-router-dom";
import { Anchor, Container, Group, Stack, Title } from "@mantine/core";
import { ChevronLeft } from "lucide-react";

import RequirePermission from "../../components/RequirePermission";
import { LegalSettingsCard } from "./LegalSettingsCard";

/** /admin/rechtliches: Impressum and Datenschutz (feature-idt-design.md → W8). */
export default function LegalSettingsPage() {
    return (
        <RequirePermission perm="settings.manage" message="Impressum und Datenschutz pflegen nur Administratoren.">
            <Container size="lg" py="xl">
                <Stack gap="lg">
                    <Anchor component={Link} to="/admin" size="sm" c="dimmed">
                        <Group gap={4} align="center">
                            <ChevronLeft size={16} />
                            Zurück zu den Einstellungen
                        </Group>
                    </Anchor>
                    <Title order={1}>Impressum & Datenschutz</Title>
                    <LegalSettingsCard />
                </Stack>
            </Container>
        </RequirePermission>
    );
}
