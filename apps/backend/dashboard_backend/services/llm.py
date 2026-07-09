"""Shared LLM client for the extraction tasks (VIB, Fulda-Runde, media).

Single site for the OpenAI-compatible chat call (``json_object`` response
format, ``temperature=0``) and for classifying API errors into the short
labels shown in the review UIs. Timeout/retry policy changes belong here.
"""

from __future__ import annotations

import json

from dashboard_backend.core.config import settings


def call_llm_json(system_prompt: str, prompt: str) -> dict:
    """Send a prompt to the configured LLM and return the parsed JSON object.

    Caller is responsible for checking ``settings.llm_base_url`` beforehand
    and for handling exceptions (extraction is best-effort in all importers).
    """
    from openai import OpenAI  # lazy import — only loaded when extraction runs

    client = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "no-key",
    )
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def summarise_error(exc: Exception) -> str:
    """Return a short human-readable error label for display in the review UI.

    Detects common API error patterns (rate limit, auth, timeout) and returns
    a concise label; falls back to the first 120 chars of the exception string.
    """
    msg = str(exc)
    if "429" in msg or "capacity exceeded" in msg.lower() or "rate limit" in msg.lower():
        return "429 – Kapazität überschritten"
    if "401" in msg or "unauthorized" in msg.lower() or "authentication" in msg.lower():
        return "401 – Authentifizierungsfehler"
    if "503" in msg or "unavailable" in msg.lower():
        return "503 – Service nicht verfügbar"
    if "timeout" in msg.lower():
        return "Timeout"
    return msg[:120]
