"""ETag-based revalidation for large, rarely changing GET responses.

The body is serialised once, hashed, and sent with a strong ``ETag`` plus
``Cache-Control: no-cache``: browsers keep the response and revalidate on every
use, and an unchanged payload is answered with ``304 Not Modified`` and no body.
Because the tag is derived from the content itself, every write path is covered
without any explicit invalidation.
"""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import Request, Response
from pydantic import TypeAdapter

CACHE_CONTROL = "no-cache"


def _matches(if_none_match: str, etag: str) -> bool:
    if if_none_match.strip() == "*":
        return True
    # Weak comparison (RFC 9110 §13.1.2): proxies may weaken the tag when they
    # transform the body, e.g. nginx after compressing it.
    candidates = (tag.strip().removeprefix("W/") for tag in if_none_match.split(","))
    return etag in candidates


def etag_json_response(request: Request, content: Any, adapter: TypeAdapter) -> Response:
    """Serialise *content* with *adapter* and answer 304 when the client's copy is current."""
    body = adapter.dump_json(adapter.validate_python(content, from_attributes=True))
    etag = f'"{hashlib.sha1(body).hexdigest()}"'
    headers = {"ETag": etag, "Cache-Control": CACHE_CONTROL}

    if_none_match = request.headers.get("if-none-match")
    if if_none_match and _matches(if_none_match, etag):
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)
