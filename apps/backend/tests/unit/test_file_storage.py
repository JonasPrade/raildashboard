"""Unit tests for utils/file_storage.py.

Tests cover:
- Path traversal guard (_safe_path raises on ../escape)
- validate_mime allowlist logic (mocked magic detection)
- delete_attachment_file silently ignores missing files
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import dashboard_backend.utils.file_storage as fs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_upload_dir(tmp_path: Path, monkeypatch):
    """Override settings.upload_dir to use a tmp directory."""
    monkeypatch.setattr(fs, "_upload_root", lambda: tmp_path.resolve())


# ---------------------------------------------------------------------------
# _safe_path — path traversal guard
# ---------------------------------------------------------------------------


def test_safe_path_normal_filename(tmp_path, monkeypatch):
    _set_upload_dir(tmp_path, monkeypatch)
    result = fs._safe_path(1, "abc.pdf")
    assert result == (tmp_path / "1" / "abc.pdf").resolve()


def test_safe_path_strips_directory_components(tmp_path, monkeypatch):
    """../etc/passwd must not escape the upload root."""
    _set_upload_dir(tmp_path, monkeypatch)
    # Path("../etc/passwd").name == "passwd" — stored as {upload_root}/1/passwd
    result = fs._safe_path(1, "../etc/passwd")
    assert str(result).startswith(str(tmp_path))
    assert "etc" not in str(result)


def test_safe_path_traversal_raises(tmp_path, monkeypatch):
    """Explicitly crafted absolute path should raise ValueError."""
    _set_upload_dir(tmp_path, monkeypatch)

    # Simulate a stored_filename that after .name extraction still ends up outside root
    # by monkey-patching _text_dir to a different root to force the assertion to fail.
    evil_dir = tmp_path.parent  # parent of upload root

    with monkeypatch.context() as m:
        m.setattr(fs, "_text_dir", lambda tid: evil_dir)
        with pytest.raises(ValueError, match="Path traversal"):
            fs._safe_path(1, "innocent.pdf")


# ---------------------------------------------------------------------------
# validate_mime — allowlist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "detected,declared",
    [
        ("application/pdf", "application/pdf"),
        ("image/jpeg", "image/jpeg"),
        ("image/png", "image/png"),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ],
)
def test_validate_mime_allowed(detected, declared):
    with patch("dashboard_backend.utils.file_storage.magic.from_buffer", return_value=detected):
        result = fs.validate_mime(b"dummy", declared)
    assert result == detected


def test_validate_mime_disallowed_detected_type():
    with patch("dashboard_backend.utils.file_storage.magic.from_buffer", return_value="text/html"):
        with pytest.raises(ValueError, match="Dateityp nicht erlaubt"):
            fs.validate_mime(b"<html>", "text/html")


def test_validate_mime_disallowed_declared_type():
    # Detected is valid but declared is not — also rejected
    with patch("dashboard_backend.utils.file_storage.magic.from_buffer", return_value="application/pdf"):
        with pytest.raises(ValueError, match="Dateityp nicht erlaubt"):
            fs.validate_mime(b"dummy", "text/html")


def test_validate_mime_empty_bytes():
    with patch("dashboard_backend.utils.file_storage.magic.from_buffer", return_value="application/octet-stream"):
        with pytest.raises(ValueError):
            fs.validate_mime(b"", "application/octet-stream")


# ---------------------------------------------------------------------------
# delete_attachment_file — no exception on missing file
# ---------------------------------------------------------------------------


def test_delete_attachment_file_missing_is_silent(tmp_path, monkeypatch):
    _set_upload_dir(tmp_path, monkeypatch)
    # File does not exist — should not raise
    fs.delete_attachment_file(42, "nonexistent.pdf")


def test_delete_attachment_file_removes_file(tmp_path, monkeypatch):
    _set_upload_dir(tmp_path, monkeypatch)
    text_dir = tmp_path / "42"
    text_dir.mkdir(parents=True)
    target = text_dir / "file.pdf"
    target.write_bytes(b"content")

    fs.delete_attachment_file(42, "file.pdf")
    assert not target.exists()


# ---------------------------------------------------------------------------
# MAX_FILE_SIZE constant
# ---------------------------------------------------------------------------


def test_max_file_size_is_50mb():
    assert fs.MAX_FILE_SIZE == 50 * 1024 * 1024
