import { useState } from "react";
import { Document, Page } from "react-pdf";
import { ActionIcon, Anchor, Group, Loader, Modal, Stack, Text } from "@mantine/core";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";

type PdfPreviewModalProps = {
    opened: boolean;
    onClose: () => void;
    /** Full URL including ?inline=true */
    attachmentUrl: string;
    filename: string;
};

export default function PdfPreviewModal({ opened, onClose, attachmentUrl, filename }: PdfPreviewModalProps) {
    const [numPages, setNumPages] = useState(0);
    const [pageNumber, setPageNumber] = useState(1);
    const [loadError, setLoadError] = useState(false);

    function handleLoadSuccess({ numPages: n }: { numPages: number }) {
        setNumPages(n);
        setPageNumber(1);
        setLoadError(false);
    }

    function handleLoadError() {
        setLoadError(true);
    }

    // Reset state when modal closes
    function handleClose() {
        setNumPages(0);
        setPageNumber(1);
        setLoadError(false);
        onClose();
    }

    const downloadUrl = attachmentUrl.replace("?inline=true", "");

    return (
        <Modal opened={opened} onClose={handleClose} title={filename} size="xl" centered>
            {opened && (
                <Stack gap="sm" align="center">
                    <Document
                        file={attachmentUrl}
                        onLoadSuccess={handleLoadSuccess}
                        onLoadError={handleLoadError}
                        loading={<Loader size="md" />}
                        error={
                            loadError ? (
                                <Stack align="center" gap="xs">
                                    <Text c="red" size="sm">PDF konnte nicht geladen werden.</Text>
                                    <Anchor href={downloadUrl} size="sm">
                                        Herunterladen
                                    </Anchor>
                                </Stack>
                            ) : null
                        }
                    >
                        <Page pageNumber={pageNumber} width={720} />
                    </Document>
                    {numPages > 1 && (
                        <Group gap="xs" align="center">
                            <ActionIcon
                                variant="subtle"
                                disabled={pageNumber <= 1}
                                onClick={() => setPageNumber((p) => p - 1)}
                                aria-label="Vorherige Seite"
                            >
                                <IconChevronLeft size={16} />
                            </ActionIcon>
                            <Text size="sm">{pageNumber} / {numPages}</Text>
                            <ActionIcon
                                variant="subtle"
                                disabled={pageNumber >= numPages}
                                onClick={() => setPageNumber((p) => p + 1)}
                                aria-label="Nächste Seite"
                            >
                                <IconChevronRight size={16} />
                            </ActionIcon>
                        </Group>
                    )}
                </Stack>
            )}
        </Modal>
    );
}
