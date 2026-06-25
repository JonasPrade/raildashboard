import { isRouteErrorResponse, useRouteError, Link } from "react-router-dom";
import { Button, Container, Group, Stack, Text, Title } from "@mantine/core";

/**
 * Route-level error boundary used as `errorElement` on the root route.
 *
 * Replaces React Router's raw "Unexpected Application Error!" developer page
 * with a friendly, German, end-user-facing fallback. It distinguishes three
 * cases: a stale chunk (offer a reload), a 404-style route response, and any
 * other thrown error.
 */
function isChunkLoadError(error: unknown): boolean {
    const message =
        error instanceof Error
            ? error.message
            : typeof error === "string"
              ? error
              : "";
    return (
        /dynamically imported module/i.test(message) ||
        /Importing a module script failed/i.test(message) ||
        /ChunkLoadError/i.test(message)
    );
}

export default function RouteErrorBoundary() {
    const error = useRouteError();

    let title = "Etwas ist schiefgelaufen";
    let detail =
        "Beim Laden dieser Seite ist ein unerwarteter Fehler aufgetreten.";
    let showReload = false;

    if (isChunkLoadError(error)) {
        title = "Seite konnte nicht geladen werden";
        detail =
            "Vermutlich wurde im Hintergrund eine neue Version veröffentlicht. " +
            "Bitte lade die Seite neu.";
        showReload = true;
    } else if (isRouteErrorResponse(error)) {
        title = `${error.status} – ${error.statusText}`;
        detail =
            error.status === 404
                ? "Diese Seite wurde nicht gefunden."
                : "Die angeforderte Seite konnte nicht geladen werden.";
    }

    // Surface the technical message for developers without scaring end users.
    const technical =
        error instanceof Error
            ? error.message
            : isRouteErrorResponse(error)
              ? `${error.status} ${error.statusText}`
              : null;

    return (
        <Container size="sm" py="xl">
            <Stack gap="md" align="flex-start">
                <Title order={2}>{title}</Title>
                <Text c="dimmed">{detail}</Text>
                {technical && (
                    <Text size="xs" c="dimmed" ff="monospace">
                        {technical}
                    </Text>
                )}
                <Group mt="sm">
                    {showReload && (
                        <Button onClick={() => window.location.reload()}>
                            Seite neu laden
                        </Button>
                    )}
                    <Button
                        variant={showReload ? "default" : "filled"}
                        component={Link}
                        to="/"
                    >
                        Zur Startseite
                    </Button>
                </Group>
            </Stack>
        </Container>
    );
}
