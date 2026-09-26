import type { ApiError } from "./client";

/**
 * Upload ceiling of the application, mirrored in three places that must stay in
 * step: the backend (`utils/file_storage.MAX_FILE_SIZE`), the container nginx
 * (`apps/frontend/nginx.conf`) and the TLS proxy on the server (see
 * docs/production_setup.md). Checking here too means the user learns about an
 * oversized file before waiting for the upload to travel.
 */
export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
export const MAX_UPLOAD_LABEL = "50 MB";

export function exceedsUploadLimit(file: File): boolean {
    return file.size > MAX_UPLOAD_BYTES;
}

export function tooLargeMessage(file: File): string {
    return `„${file.name}" überschreitet das Limit von ${MAX_UPLOAD_LABEL}.`;
}

/**
 * Message for a failed upload.
 *
 * A 413 needs its own text: it is usually the reverse proxy answering, not the
 * backend, and it answers with an HTML error page — so the status code is the
 * only thing left to go on. Everything else falls back to the API's `detail`,
 * then to the caller's generic text.
 */
export function uploadErrorMessage(error: unknown, fallback = "Upload fehlgeschlagen."): string {
    const status = (error as ApiError | undefined)?.status;
    const detail = (error as { details?: { detail?: string } } | undefined)?.details?.detail;

    if (status === 413) {
        return detail ?? `Datei zu groß — maximal ${MAX_UPLOAD_LABEL} pro Upload.`;
    }

    return detail ?? fallback;
}
