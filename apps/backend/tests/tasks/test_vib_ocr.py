"""Tests for vib_ocr — Mistral OCR + pymupdf fallback."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from dashboard_backend.tasks.vib_ocr import (
    _find_rail_section_pages,
    _inline_tables,
    _pages_to_text,
    extract_full_pdf_text,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _page(index: int, markdown: str) -> SimpleNamespace:
    return SimpleNamespace(index=index, markdown=markdown)


def _make_ocr_response(pages: list, model: str = "mistral-ocr-2512") -> SimpleNamespace:
    return SimpleNamespace(pages=pages, model=model)


# ---------------------------------------------------------------------------
# _find_rail_section_pages (utility — not in main flow, useful for debugging)
# ---------------------------------------------------------------------------

class TestFindRailSectionPages:
    def test_returns_pages_between_b_and_c(self):
        pages = [
            _page(0, "Inhaltsverzeichnis"),
            _page(1, "A Wasserstraßen"),
            _page(2, "B Schienenwege\nB.4.1 Projekte"),
            _page(3, "Fortsetzung Schienenwege"),
            _page(4, "C Bundesfernstraßen"),
            _page(5, "D Sonstiges"),
        ]
        result = _find_rail_section_pages(pages)
        assert [p.index for p in result] == [2, 3]

    def test_includes_all_remaining_when_c_not_found(self):
        pages = [
            _page(0, "B Schienenwege\ninhalt"),
            _page(1, "Fortsetzung"),
            _page(2, "Ende"),
        ]
        result = _find_rail_section_pages(pages)
        assert [p.index for p in result] == [0, 1, 2]

    def test_falls_back_to_all_pages_when_b_not_found(self):
        pages = [_page(0, "kein Schienenwege"), _page(1, "auch nicht")]
        result = _find_rail_section_pages(pages)
        assert [p.index for p in result] == [0, 1]

    def test_case_insensitive_match(self):
        pages = [
            _page(0, "b schienenwege\ninhalt"),
            _page(1, "c bundesfernstraßen"),
        ]
        result = _find_rail_section_pages(pages)
        assert [p.index for p in result] == [0]


# ---------------------------------------------------------------------------
# _pages_to_text
# ---------------------------------------------------------------------------

class TestInlineTables:
    def _tbl(self, tbl_id: str, content: str):
        return SimpleNamespace(id=tbl_id, content=content)

    def test_replaces_tbl_reference_with_content(self):
        md = "some text\n[tbl-3.md](tbl-3.md)\nmore text"
        tables = [self._tbl("tbl-3", "| A | B |\n|---|---|\n| 1 | 2 |")]
        result = _inline_tables(md, tables)
        assert "| A | B |" in result
        assert "[tbl-3.md](tbl-3.md)" not in result

    def test_replaces_without_md_suffix(self):
        md = "text [tbl-1](tbl-1) end"
        tables = [self._tbl("tbl-1", "| X |")]
        result = _inline_tables(md, tables)
        assert "| X |" in result

    def test_multiple_tables(self):
        md = "[tbl-0.md](tbl-0.md)\n[tbl-1.md](tbl-1.md)"
        tables = [self._tbl("tbl-0", "table0"), self._tbl("tbl-1", "table1")]
        result = _inline_tables(md, tables)
        assert "table0" in result
        assert "table1" in result

    def test_unknown_reference_left_intact(self):
        md = "text [other.md](other.md) end"
        tables = [self._tbl("tbl-0", "data")]
        result = _inline_tables(md, tables)
        assert "[other.md](other.md)" in result


class TestPagesToText:
    def test_joins_markdowns(self):
        pages = [_page(0, "Seite 1"), _page(1, "Seite 2")]
        assert _pages_to_text(pages) == "Seite 1\nSeite 2"

    def test_empty_list_returns_empty_string(self):
        assert _pages_to_text([]) == ""

    def test_header_footer_excluded_when_strip_true(self):
        page = SimpleNamespace(index=0, markdown="body text", header="PAGE HEADER", footer="42")
        result = _pages_to_text([page], strip_headers_footers=True)
        assert "PAGE HEADER" not in result
        assert "42" not in result
        assert "body text" in result

    def test_header_footer_included_when_strip_false(self):
        page = SimpleNamespace(index=0, markdown="body", header="HEADER", footer="FOOTER")
        result = _pages_to_text([page], strip_headers_footers=False)
        assert "HEADER" in result
        assert "FOOTER" in result

    def test_table_inlined(self):
        tbl = SimpleNamespace(id="tbl-0", content="| Col |\n| --- |\n| val |")
        page = SimpleNamespace(index=0, markdown="intro\n[tbl-0.md](tbl-0.md)\noutro", tables=[tbl])
        result = _pages_to_text([page])
        assert "| Col |" in result
        assert "[tbl-0.md](tbl-0.md)" not in result

    def test_image_refs_stripped(self):
        page = SimpleNamespace(index=0, markdown="text ![img-0.jpeg](img-0.jpeg) end")
        result = _pages_to_text([page], strip_images=True)
        assert "![" not in result
        assert "text" in result


# ---------------------------------------------------------------------------
# extract_full_pdf_text
# ---------------------------------------------------------------------------

def _page_with_image(index: int, markdown: str, img_id: str, img_b64: str) -> SimpleNamespace:
    img = SimpleNamespace(id=img_id, image_base64=img_b64)
    return SimpleNamespace(index=index, markdown=markdown, images=[img])


# ---------------------------------------------------------------------------
# _collect_images
# ---------------------------------------------------------------------------

class TestCollectImages:
    def test_extracts_images_from_pages(self):
        from dashboard_backend.tasks.vib_ocr import _collect_images
        pages = [
            _page_with_image(0, "text", "img-0.jpeg", "abc123"),
            _page_with_image(1, "more", "img-1.png", "def456"),
        ]
        result = _collect_images(pages)
        assert len(result) == 2
        assert result[0] == {"page_index": 0, "id": "img-0.jpeg", "image_base64": "abc123"}
        assert result[1] == {"page_index": 1, "id": "img-1.png", "image_base64": "def456"}

    def test_skips_images_without_base64(self):
        from dashboard_backend.tasks.vib_ocr import _collect_images
        img = SimpleNamespace(id="img-0.jpeg", image_base64=None)
        page = SimpleNamespace(index=0, markdown="text", images=[img])
        result = _collect_images([page])
        assert result == []

    def test_returns_empty_for_pages_without_images(self):
        from dashboard_backend.tasks.vib_ocr import _collect_images
        result = _collect_images([_page(0, "text"), _page(1, "more")])
        assert result == []

    def test_multiple_images_per_page(self):
        from dashboard_backend.tasks.vib_ocr import _collect_images
        imgs = [
            SimpleNamespace(id="img-0.jpeg", image_base64="aaa"),
            SimpleNamespace(id="img-1.jpeg", image_base64="bbb"),
        ]
        page = SimpleNamespace(index=2, markdown="text", images=imgs)
        result = _collect_images([page])
        assert len(result) == 2
        assert all(r["page_index"] == 2 for r in result)


# ---------------------------------------------------------------------------
# extract_full_pdf_text (images)
# ---------------------------------------------------------------------------

class TestExtractFullPdfText:
    def _fake_mistral_response(self):
        pages = [
            _page(0, "Inhaltsverzeichnis\nB 4.1.1 Projekt Alpha . . . 42"),
            _page(1, "B Schienenwege\n## B.4.1.1 Projekt Alpha"),
            _page(2, "Fortsetzung Alpha\nC Bundesfernstraßen"),
        ]
        return _make_ocr_response(pages)

    def test_calls_mistral_when_api_key_given(self):
        mock_client = MagicMock()
        mock_client.ocr.process.return_value = self._fake_mistral_response()

        with patch("dashboard_backend.tasks.vib_ocr.Mistral", return_value=mock_client):
            text, model, status, images = extract_full_pdf_text(
                pdf_bytes=b"fakepdf",
                api_key="sk-test",
                base_url="https://api.mistral.ai",
                model="mistral-ocr-latest",
            )

        mock_client.ocr.process.assert_called_once()
        call_kwargs = mock_client.ocr.process.call_args.kwargs
        assert call_kwargs["model"] == "mistral-ocr-latest"
        assert call_kwargs["table_format"] == "markdown"
        assert "data:application/pdf;base64," in call_kwargs["document"]["document_url"]

    def test_returns_all_pages_text(self):
        pages = [
            _page(0, "Inhaltsverzeichnis"),
            _page(1, "B Schienenwege\nProjekttext"),
            _page(2, "C Bundesfernstraßen"),
        ]
        mock_client = MagicMock()
        mock_client.ocr.process.return_value = _make_ocr_response(pages)

        with patch("dashboard_backend.tasks.vib_ocr.Mistral", return_value=mock_client):
            text, model, status, images = extract_full_pdf_text(
                pdf_bytes=b"fakepdf",
                api_key="sk-test",
                base_url="https://api.mistral.ai",
                model="mistral-ocr-latest",
            )

        # All pages present — filtering is _parse_vib_pdf's job
        assert "Inhaltsverzeichnis" in text
        assert "Projekttext" in text
        assert "Bundesfernstraßen" in text

    def test_returns_done_status_on_success(self):
        mock_client = MagicMock()
        mock_client.ocr.process.return_value = self._fake_mistral_response()

        with patch("dashboard_backend.tasks.vib_ocr.Mistral", return_value=mock_client):
            _, model, status, _images = extract_full_pdf_text(
                pdf_bytes=b"fakepdf",
                api_key="sk-test",
                base_url="https://api.mistral.ai",
                model="mistral-ocr-latest",
            )

        assert status == "done"
        assert model == "mistral-ocr-2512"

    def test_falls_back_to_pymupdf_when_no_api_key(self):
        fake_page = MagicMock()
        fake_page.get_text.return_value = "B Schienenwege\nB.4.1.1 Projekt"
        fake_doc = MagicMock()
        fake_doc.__iter__ = lambda self: iter([fake_page])
        fake_doc.__enter__ = lambda self: fake_doc
        fake_doc.__exit__ = MagicMock(return_value=False)

        with patch("dashboard_backend.tasks.vib_ocr.fitz") as mock_fitz:
            mock_fitz.open.return_value = fake_doc
            text, model, status, images = extract_full_pdf_text(
                pdf_bytes=b"fakepdf",
                api_key="",
                base_url="https://api.mistral.ai",
                model="mistral-ocr-latest",
            )

        assert "B.4.1.1" in text
        assert status == "fallback"
        assert model == "pymupdf"
        assert images == []

    def test_falls_back_on_mistral_error(self):
        mock_client = MagicMock()
        mock_client.ocr.process.side_effect = Exception("API error")

        fake_page = MagicMock()
        fake_page.get_text.return_value = "B Schienenwege\ninhalt"
        fake_doc = MagicMock()
        fake_doc.__iter__ = lambda self: iter([fake_page])
        fake_doc.__enter__ = lambda self: fake_doc
        fake_doc.__exit__ = MagicMock(return_value=False)

        with patch("dashboard_backend.tasks.vib_ocr.Mistral", return_value=mock_client), \
             patch("dashboard_backend.tasks.vib_ocr.fitz") as mock_fitz:
            mock_fitz.open.return_value = fake_doc
            text, model, status, images = extract_full_pdf_text(
                pdf_bytes=b"fakepdf",
                api_key="sk-test",
                base_url="https://api.mistral.ai",
                model="mistral-ocr-latest",
            )

        assert status == "fallback"
        assert model == "pymupdf"
