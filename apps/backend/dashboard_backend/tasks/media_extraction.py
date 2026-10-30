"""Semi-automatic extraction for the Medien/Presse importer (#48).

Given an article URL or pasted text, optionally use the configured LLM
(``settings.llm_base_url``, OpenAI-compatible — same as VIB extraction) to pull
out publication, date, the referenced project, an asserted planning phase and a
supporting quote. When no LLM is configured the extraction degrades gracefully
to an empty result and the editor fills the fields manually. There is always a
human-in-the-loop confirmation before anything is materialised.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from urllib.parse import urlsplit

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


_MAX_REDIRECTS = 5
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class UnsafeUrlError(ValueError):
    """The URL points somewhere the importer must not fetch (SSRF guard)."""


def _ensure_public_url(url: str) -> None:
    """Allow only http(s) URLs whose host resolves to public addresses.

    Blocks the internal network (redis, db, GraphHopper), loopback, link-local
    (cloud metadata) and other non-global ranges. Checked again for every
    redirect target.
    """

    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("Nur http- und https-URLs sind erlaubt.")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL ohne Host.")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (OSError, ValueError) as exc:
        raise UnsafeUrlError(f"Host {host} nicht auflösbar.") from exc
    if not infos:
        raise UnsafeUrlError(f"Host {host} nicht auflösbar.")
    for info in infos:
        address = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        if (
            not address.is_global
            or address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise UnsafeUrlError(f"Host {host} zeigt auf eine nicht öffentliche Adresse.")


def _read_limited(response) -> bytes:
    declared = response.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > _MAX_RESPONSE_BYTES:
        raise UnsafeUrlError("Antwort zu groß.")
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > _MAX_RESPONSE_BYTES:
            raise UnsafeUrlError("Antwort zu groß.")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_url_text(url: str, timeout: float = 20.0, transport=None) -> str:
    """Fetch an article URL and return a rough plain-text rendering.

    Strips scripts/styles and HTML tags. Only public http(s) hosts are fetched,
    redirects are followed by hand (each target re-checked, at most
    ``_MAX_REDIRECTS``) and the body is capped at ``_MAX_RESPONSE_BYTES``.
    Raises ``UnsafeUrlError`` (a ``ValueError``) for a blocked URL and
    ``httpx.HTTPError`` on network failure. ``transport`` is a test seam.
    """

    import httpx  # lazy import

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html"}
    with httpx.Client(
        timeout=timeout, headers=headers, follow_redirects=False, transport=transport
    ) as client:
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            _ensure_public_url(current)
            with client.stream("GET", current) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise UnsafeUrlError("Weiterleitung ohne Ziel.")
                    current = str(response.url.join(location))
                    continue
                response.raise_for_status()
                body = _read_limited(response)
                html = body.decode(response.encoding or "utf-8", errors="replace")
            return _html_to_text(html)
    raise UnsafeUrlError("Zu viele Weiterleitungen.")


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
