"""Token format and permission rules for personal API keys.

Format: ``rdb_<prefix>_<secret>``. The 12-character base32 prefix is stored in
clear text and indexed (one index hit per lookup); the 256-bit secret is stored
as a plain SHA-256 hash. PBKDF2 (as for passwords) buys nothing against a
256-bit secret and would cost ~100 ms on every agent tool call.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta

TOKEN_PREFIX = "rdb_"
PREFIX_LENGTH = 12
# Every new key expires after 90 days (decided with the product owner).
DEFAULT_KEY_LIFETIME = timedelta(days=90)
# Capability a key (and its owner) must hold to talk to ``/mcp``.
MCP_PERMISSION = "mcp.access"


@dataclass(frozen=True)
class GeneratedKey:
    token: str
    prefix: str
    key_hash: str


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_key() -> GeneratedKey:
    prefix = base64.b32encode(secrets.token_bytes(10)).decode("ascii").lower()[:PREFIX_LENGTH]
    secret = secrets.token_urlsafe(32)
    return GeneratedKey(
        token=f"{TOKEN_PREFIX}{prefix}_{secret}",
        prefix=prefix,
        key_hash=hash_secret(secret),
    )


def parse_token(token: str) -> tuple[str, str] | None:
    """Split a token into ``(prefix, secret)``; None if it is not an API key.

    The secret is URL-safe base64 and may itself contain ``_``, so only the
    first separator after the prefix counts.
    """

    if not token.startswith(TOKEN_PREFIX):
        return None
    prefix, sep, secret = token[len(TOKEN_PREFIX):].partition("_")
    if not sep or len(prefix) != PREFIX_LENGTH or not secret:
        return None
    return prefix, secret


def secret_matches(secret: str, key_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(secret), key_hash)


def key_permissions(user_permissions: Iterable[str], scopes: Iterable[str] | None) -> set[str]:
    """Effective capabilities of a key request: owner's set ∩ scopes.

    There is deliberately no super-admin bypass here — otherwise an admin's key
    could not be narrowed by ``scopes``, which is their whole purpose.
    """

    granted = set(user_permissions)
    if scopes is None:
        return granted
    return granted & set(scopes)
