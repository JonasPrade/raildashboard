import { Group, Title } from "@mantine/core";

export function Header() {
    return (
        <Group justify="space-between" px="md" py="xs">
            <Title order={2}>Dashboard Schienenprojekte</Title>
        </Group>
    );
}