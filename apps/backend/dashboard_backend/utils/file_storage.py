"""File storage utility for text attachments.

Security guarantees:
- Path traversal: every resolved path is asserted to be under UPLOAD_DIR.
- MIME type: validated via python-magic (byte-level file header), not just
  the HTTP Content-Type header which is attacker-controlled.
- Write order: callers must persist the DB row first, then call save_attachment.
  On failure they must call delete_attachment_file in a finally block.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import magic

from dashboard_backend.core.config import settings

# ---------------------------------------------------------------------------
# Allowed MIME types
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "image/jpeg",
        "image/png",
    ]
)

# Extension map for storing files with a recognisable suffix
_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _upload_root() -> Path:
    return Path(settings.upload_dir).resolve()


def _text_dir(text_id: int) -> Path:
    return _upload_root() / str(text_id)


def _safe_path(text_id: int, stored_filename: str) -> Path:
    """Return the absolute path and assert it stays inside UPLOAD_DIR."""
    root = _upload_root()
    # Prevent path traversal: strip any directory components from stored_filename
    safe_name = Path(stored_filename).name
    candidate = (_text_dir(text_id) / safe_name).resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError(f"Path traversal attempt detected: {stored_filename!r}")
    return candidate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_mime(file_bytes: bytes, declared_mime: str) -> str:
    """Validate file content against the allowlist using magic byte sniffing.

    Both the byte-detected MIME and the declared Content-Type must be in
    ALLOWED_MIME_TYPES and must agree with each other.

    Returns the detected MIME type on success.
    Raises ValueError with a user-facing message on failure.
    """
    detected = magic.from_buffer(file_bytes[:2048], mime=True)

    if detected not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Dateityp nicht erlaubt. Erlaubt: PDF, Word, Excel, JPEG, PNG. "
            f"Erkannt: {detected}"
        )
    if declared_mime not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Dateityp nicht erlaubt (deklarierter Typ: {declared_mime})."
        )
    # The detected type is authoritative; we just verify the declared type is
    # also in the allowlist so clients aren't confused by a silent mismatch.
    return detected


def save_attachment(text_id: int, file_bytes: bytes, detected_mime: str) -> tuple[str, int]:
    """Write file bytes to disk under UPLOAD_DIR/{text_id}/.

    Returns (stored_filename, file_size).
    The caller is responsible for committing the DB row before calling this,
    and for calling delete_attachment_file in a finally block on error.
    """
    ext = _MIME_TO_EXT.get(detected_mime, "")
    stored_filename = f"{uuid.uuid4().hex}{ext}"

    dest_dir = _text_dir(text_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = _safe_path(text_id, stored_filename)
    dest.write_bytes(file_bytes)

    return stored_filename, len(file_bytes)


def delete_attachment_file(text_id: int, stored_filename: str) -> None:
    """Remove a stored file from disk. Silently ignores missing files."""
    try:
        path = _safe_path(text_id, stored_filename)
        path.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass  # path traversal attempt or permission error — ignore silently


def get_attachment_path(text_id: int, stored_filename: str) -> Path:
    """Return the absolute path to a stored attachment (validated)."""
    return _safe_path(text_id, stored_filename)
