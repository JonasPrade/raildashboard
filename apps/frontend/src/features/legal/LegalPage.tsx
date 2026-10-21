import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Anchor, Button, Container, Stack, Text, Title, Typography } from "@mantine/core";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { useAuth } from "../../lib/auth";
import { useAppSettings } from "../../shared/api/queries";
import { EmptyState } from "../../shared/ui/EmptyState";
import { ErrorState } from "../../shared/ui/ErrorState";
import { LoadingState } from "../../shared/ui/LoadingState";
import { LEGAL_SETTINGS_ANCHOR } from "./legal";

export type LegalPageKind = "impressum" | "datenschutz";

const COPY: Record<LegalPageKind, { title: string; emptyTitle: string; emptyText: string }> = {
    impressum: {
        title: "Impressum",
        emptyTitle: "Noch kein Impressum hinterlegt",
        emptyText: "Sobald in der Administration ein Text oder eine Adresse eingetragen ist, erscheint das Impressum hier.",
    },
    datenschutz: {
        title: "Datenschutzerklärung",
        emptyTitle: "Noch keine Datenschutzerklärung hinterlegt",
        emptyText: "Sobald in der Administration ein Text oder eine Adresse eingetragen ist, erscheint die Datenschutzerklärung hier.",
    },
};

/**
 * /impressum and /datenschutz (docs/features/feature-idt-design.md → W8).
 * The content comes from AppSettings: a URL wins and redirects outside,
 * otherwise the Markdown is rendered; both empty → empty state.
 */
export default function LegalPage({ kind }: { kind: LegalPageKind }) {
    const { data, isLoading, isError, refetch } = useAppSettings();
    const { can } = useAuth();
    const copy = COPY[kind];

    const url = (kind === "impressum" ? data?.impressum_url : data?.datenschutz_url)?.trim() || null;
    const markdown =
        (kind === "impressum" ? data?.impressum_markdown : data?.datenschutz_markdown)?.trim() || null;

    useEffect(() => {
        if (url) window.location.replace(url);
    }, [url]);

    let body;
    if (isLoading) {
        body = <LoadingState rows={6} />;
    } else if (isError) {
        body = (
            <ErrorState onRetry={() => void refetch()}>
                Die Seite konnte nicht geladen werden.
            </ErrorState>
        );
    } else if (url) {
        body = (
            <Text>
                Weiterleitung zu <Anchor href={url}>{url}</Anchor> …
            </Text>
        );
    } else if (markdown) {
        body = (
            <Typography>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
            </Typography>
        );
    } else {
        body = (
            <EmptyState
                title={copy.emptyTitle}
                action={
                    can("settings.manage") ? (
                        <Button
                            component={Link}
                            to={`/admin#${LEGAL_SETTINGS_ANCHOR}`}
                            variant="outline"
                        >
                            In der Administration eintragen
                        </Button>
                    ) : undefined
                }
            >
                {copy.emptyText}
            </EmptyState>
        );
    }

    return (
        <Container size="md" py="xl">
            <Stack gap="lg">
                <Title order={1}>{copy.title}</Title>
                {body}
            </Stack>
        </Container>
    );
}
