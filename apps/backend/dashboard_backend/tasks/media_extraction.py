"""Semi-automatic extraction for the Medien/Presse importer (#48).

Given an article URL or pasted text, optionally use the configured LLM
(``settings.llm_base_url``, OpenAI-compatible — same as VIB extraction) to pull
out publication, date, the referenced project, an asserted planning phase and a
supporting quote. When no LLM is configured the extraction degrades gracefully
to an empty result and the editor fills the fields manually. There is always a
human-in-the-loop confirmation before anything is materialised.
"""

from __future__ import annotations

import logging
import re

from dashboard_backend.core.config import settings
from dashboard_backend.services.llm import call_llm_json

logger = logging.getLogger(__name__)

# Phases the LLM may assert, aligned with models.projects.progress_enums.MainPhase.
_ALLOWED_PHASES = {
    "NICHT_GESTARTET",
    "VORPLANUNG",
    "GENEHMIGUNGSPLANUNG",
    "BAU",
    "IN_BETRIEB",
}

_SYSTEM_PROMPT = (
    "Du analysierst deutsche Presseartikel über Bahn-Infrastrukturprojekte. "
    "Antworte ausschließlich mit einem validen JSON-Objekt, ohne Erklärungen."
)

_USER_PROMPT_TEMPLATE = """\
Artikel{url_line}:

--- TEXT ---
{text}
--- ENDE ---

Extrahiere als JSON:
{{
  "publication": "<Medium/Quelle oder null>",
  "published_date": "<YYYY-MM-DD oder null>",
  "project_name": "<Name des betroffenen Bahnprojekts oder null>",
  "phase": "<eine von NICHT_GESTARTET|VORPLANUNG|GENEHMIGUNGSPLANUNG|BAU|IN_BETRIEB, oder null>",
  "observed_date": "<YYYY-MM-DD des berichteten Phasenstands, oder null>",
  "quote": "<wörtliches Zitat, das die Phase belegt, oder null>"
}}

Wähle die Phase nur, wenn der Text sie klar stützt. Erfinde nichts.
"""

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"[ \t]+")
_BLANKLINES_RE = re.compile(r"\n\s*\n\s*\n+")

_MAX_TEXT_CHARS = 12000


def fetch_url_text(url: str, timeout: float = 20.0) -> str:
    """Fetch an article URL and return a rough plain-text rendering.

    Strips scripts/styles and HTML tags. Raises ``httpx.HTTPError`` on failure.
    """

    import httpx  # lazy import

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html"}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text
    return _html_to_text(html)


def _html_to_text(html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    text = _WS_RE.sub(" ", text)
    text = _BLANKLINES_RE.sub("\n\n", text)
    return text.strip()[:_MAX_TEXT_CHARS]


def _normalize_phase(value) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    return candidate if candidate in _ALLOWED_PHASES else None


def extract_media_report(text: str, url: str | None = None) -> dict:
    """Return extracted fields for a press article.

    Keys: ``publication``, ``published_date``, ``project_name``, ``phase``
    (validated against the allowed set, else None), ``observed_date``, ``quote``.
    Returns all-None when no LLM is configured or extraction fails — the editor
    completes the draft manually.
    """

    empty = {
        "publication": None,
        "published_date": None,
        "project_name": None,
        "phase": None,
        "observed_date": None,
        "quote": None,
    }
    if not settings.llm_base_url or not (text or "").strip():
        return empty

    prompt = _USER_PROMPT_TEMPLATE.format(
        url_line=f" (Quelle: {url})" if url else "",
        text=text[:_MAX_TEXT_CHARS],
    )
    try:
        result = call_llm_json(_SYSTEM_PROMPT, prompt)
    except Exception as exc:  # noqa: BLE001 - extraction is best-effort
        logger.warning("Media LLM extraction failed: %s", exc)
        return empty

    return {
        "publication": result.get("publication") or None,
        "published_date": result.get("published_date") or None,
        "project_name": result.get("project_name") or None,
        "phase": _normalize_phase(result.get("phase")),
        "observed_date": result.get("observed_date") or None,
        "quote": result.get("quote") or None,
    }
