"""Celery task: LLM-based sub-block extraction for VIB entries."""
from __future__ import annotations

import json
import logging
import re

from celery import Task

from dashboard_backend.celery_app import celery_app
from dashboard_backend.core.config import settings
from dashboard_backend.crud.vib import get_draft_by_task_id, update_draft_ai_result
from dashboard_backend.database import Session
from dashboard_backend.schemas.vib import VibEntryProposed, VibParseTaskResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Du analysierst Abschnitte aus dem Verkehrsinvestitionsbericht (VIB) des Bundes. "
    "Antworte ausschließlich mit einem validen JSON-Objekt, ohne Erklärungen."
)

_USER_PROMPT_TEMPLATE = """\
Sektionsnummer: {vib_section}
Projektname: {vib_name_raw}

--- ROHTEXT ---
{raw_text}
--- ENDE ---

Extrahiere folgende Felder als JSON:
{{
  "verkehrliche_zielsetzung": "<Text oder null>",
  "durchgefuehrte_massnahmen": "<Text oder null>",
  "noch_umzusetzende_massnahmen": "<Text oder null>",
  "bauaktivitaeten": "<Text oder null>",
  "teilinbetriebnahmen": "<Text oder null — bei status_abgeschlossen=true: Inbetriebnahmedatum oder -beschreibung aus dem Text>",
  "planungsstand": "<Text oder null>",
  "status_planung": "<true wenn das Projekt sich in der Planungsphase befindet, sonst false>",
  "status_bau": "<true wenn das Projekt sich im Bau befindet, sonst false>",
  "status_abgeschlossen": "<true wenn das Projekt fertiggestellt / in Betrieb genommen wurde, sonst false>",
  "strecklaenge_km": "<float oder null>",
  "gesamtkosten_mio_eur": "<float oder null>",
  "entwurfsgeschwindigkeit": "<z.B. '200/250' oder null>",
  "pfa_entries": [
    {{
      "nr_pfa": "<z.B. '1.1'>",
      "oertlichkeit": "<Text oder null>",
      "entwurfsplanung": "<'abgeschlossen' | 'offen' | 'in Überarbeitung' | null>",
      "abschluss_finve": "<Datum oder null>",
      "datum_pfb": "<Datum oder null>",
      "baubeginn": "<Datum oder null>",
      "inbetriebnahme": "<Datum oder null>"
    }}
  ]
}}

Hinweis zu Projektstatus: status_planung, status_bau und status_abgeschlossen können gleichzeitig true sein \
(z.B. wenn Teilabschnitte bereits in Betrieb sind während andere noch geplant werden).
"""

_TEXT_FIELDS = [
    "verkehrliche_zielsetzung",
    "durchgefuehrte_massnahmen",
    "noch_umzusetzende_massnahmen",
    "bauaktivitaeten",
    "teilinbetriebnahmen",
    "planungsstand",
    "entwurfsgeschwindigkeit",
]

_BOOL_STATUS_FIELDS = ["status_planung", "status_bau", "status_abgeschlossen"]


def _call_llm(prompt: str) -> dict:
    """Send prompt to configured LLM, return parsed JSON dict."""
    from openai import OpenAI  # lazy import

    client = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "no-key",
    )
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


_TEILINBETRIEBNAHMEN_NONE_RE = re.compile(r"^\s*[-–]\s*[Kk]eine\.?\s*$")


def _summarise_error(exc: Exception) -> str:
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


def _normalize_teilinbetriebnahmen(val: str) -> str | None:
    """Normalize '- Keine.' and variants to None (no partial commissioning)."""
    if _TEILINBETRIEBNAHMEN_NONE_RE.match(val):
        return None
    return val


def _merge_ai_result(entry_dict: dict, ai: dict) -> dict:
    """Merge LLM-extracted fields into an entry dict. Returns updated dict."""
    for field in _TEXT_FIELDS:
        val = ai.get(field)
        if val is not None:
            if isinstance(val, list):
                val = "\n".join(str(item) for item in val)
            if field == "teilinbetriebnahmen":
                val = _normalize_teilinbetriebnahmen(val)
            entry_dict[field] = val

    for num_field in ("strecklaenge_km", "gesamtkosten_mio_eur"):
        val = ai.get(num_field)
        if val is not None:
            try:
                entry_dict[num_field] = float(val)
            except (TypeError, ValueError):
                pass

    for bool_field in _BOOL_STATUS_FIELDS:
        val = ai.get(bool_field)
        if val is not None:
            entry_dict[bool_field] = bool(val)

    if ai.get("pfa_entries"):
        entry_dict["pfa_entries"] = ai["pfa_entries"]

    entry_dict["ai_extracted"] = True
    return entry_dict


@celery_app.task(bind=True)
def extract_vib_blocks(
    self: Task,
    parse_task_id: str,
    user_info: dict,
) -> dict:
    """Run LLM extraction on each VIB entry in the draft identified by parse_task_id."""
    logger.info(
        "extract_vib_blocks started: parse_task_id=%s user=%s",
        parse_task_id,
        user_info.get("username") if user_info else "unknown",
    )

    if not settings.llm_base_url:
        raise RuntimeError("LLM not configured: LLM_BASE_URL is empty")

    db = Session()
    try:
        draft = get_draft_by_task_id(db, parse_task_id)
        if draft is None:
            raise RuntimeError(f"Draft not found for task_id={parse_task_id}")

        result = VibParseTaskResult.model_validate_json(draft.raw_result_json)
        entries_as_dicts = [e.model_dump() for e in result.entries]
        total = len(entries_as_dicts)

        for idx, entry_dict in enumerate(entries_as_dicts):
            self.update_state(
                state="PROGRESS",
                meta={"current": idx + 1, "total": total},
            )
            raw_text = entry_dict.get("raw_text") or ""
            if not raw_text.strip():
                logger.warning(
                    "Entry %s has no raw_text — skipping LLM call",
                    entry_dict.get("vib_section"),
                )
                continue
            try:
                prompt = _USER_PROMPT_TEMPLATE.format(
                    vib_section=entry_dict.get("vib_section") or "?",
                    vib_name_raw=entry_dict.get("vib_name_raw") or "?",
                    raw_text=raw_text[:6000],
                )
                ai_result = _call_llm(prompt)
                entries_as_dicts[idx] = _merge_ai_result(entry_dict, ai_result)
                entries_as_dicts[idx]["ai_extraction_failed"] = False
                entries_as_dicts[idx]["ai_extraction_error"] = None
                logger.debug("LLM extraction OK for %s", entry_dict.get("vib_section"))
            except Exception as exc:
                logger.warning(
                    "LLM extraction failed for %s: %s",
                    entry_dict.get("vib_section"),
                    exc,
                )
                entries_as_dicts[idx]["ai_extraction_failed"] = True
                entries_as_dicts[idx]["ai_extraction_error"] = _summarise_error(exc)

        updated_result = VibParseTaskResult(
            year=result.year,
            drucksache_nr=result.drucksache_nr,
            report_date=result.report_date,
            entries=[VibEntryProposed(**e) for e in entries_as_dicts],
        )
        update_draft_ai_result(db, parse_task_id, updated_result.model_dump_json())
        db.commit()

        logger.info("extract_vib_blocks finished: %d entries processed", total)
        return updated_result.model_dump()

    except Exception as exc:
        logger.exception("extract_vib_blocks failed: %s", exc)
        raise
    finally:
        db.close()
