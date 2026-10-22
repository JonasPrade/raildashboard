import { useMemo, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ActionIcon, Anchor, Group, Modal, Stack, Text } from "@mantine/core";
import { useViewportSize } from "@mantine/hooks";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { LoadingState } from "../../shared/ui/LoadingState";

// Worker is bundled locally (no CDN dependency); this module is lazy-loaded,
// so pdfjs and its worker only load when a PDF preview is opened.
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

type PdfPreviewModalProps = {
    opened: boolean;
    onClose: () => void;
    /** Full URL including ?inline=true */
    attachmentUrl: string;
    filename: string;
};

export default function PdfPreviewModal({ opened, onClose, attachmentUrl, filename }: PdfPreviewModalProps) {
    const { width: viewportWidth } = useViewportSize();
    // A 720px page would need pinch-zoom on a phone — render it at screen width.
    const pageWidth = Math.min(720, Math.max(280, viewportWidth - 40));
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
    // Send the session cookie: attachments of internal texts need a signed-in user.
    // Memoised — a new object on every render would make react-pdf reload the file.
    const file = useMemo(() => ({ url: attachmentUrl, withCredentials: true }), [attachmentUrl]);

    return (
        <Modal
            opened={opened}
            onClose={handleClose}
            title={filename}
            size="xl"
            centered
        >
            {opened && (
                <Stack gap="sm" align="center">
                    <Document
                        file={file}
                        onLoadSuccess={handleLoadSuccess}
                        onLoadError={handleLoadError}
                        loading={<LoadingState height={480} label="PDF wird geladen …" />}
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
                        <Page pageNumber={pageNumber} width={pageWidth} />
                    </Document>
                    {numPages > 1 && (
                        <Group gap="xs" align="center">
                            <ActionIcon
                                variant="subtle"
                                disabled={pageNumber <= 1}
                                onClick={() => setPageNumber((p) => p - 1)}
                                aria-label="Vorherige Seite"
                            >
                                <ChevronLeft size={16} />
                            </ActionIcon>
                            <Text size="sm">{pageNumber} / {numPages}</Text>
                            <ActionIcon
                                variant="subtle"
                                disabled={pageNumber >= numPages}
                                onClick={() => setPageNumber((p) => p + 1)}
                                aria-label="Nächste Seite"
                            >
                                <ChevronRight size={16} />
                            </ActionIcon>
                        </Group>
                    )}
                </Stack>
            )}
        </Modal>
    );
}
