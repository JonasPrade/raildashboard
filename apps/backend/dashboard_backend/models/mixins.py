"""Reusable column groups shared by several models."""

from __future__ import annotations

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import declarative_mixin


@declarative_mixin
class OcrSourceMixin:
    """Persisted outcome of stage 1 (``services.document_ocr``) for a PDF import.

    Every PDF importer keeps the machine-readable text it worked from: it makes
    a failed run inspectable, and lets post-processing be retried without
    paying for the extraction again.  The three columns mirror
    :class:`~dashboard_backend.services.document_ocr.OcrResult`.
    """

    # Full document text as it went into the parser (markdown for Mistral OCR,
    # plain text for the pymupdf/pdfplumber fallbacks)
    ocr_raw_text = Column(Text, nullable=True)
    # "done" | "fallback" | "failed" — see OcrResult.status
    ocr_status = Column(String(20), nullable=True)
    # e.g. "mistral-ocr-2512", "pymupdf", "pdfplumber"
    ocr_model = Column(String(100), nullable=True)
