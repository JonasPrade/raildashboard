"""One run at a time per routine job (feature-routine-abrufe.md, E4).

A Redis ``SET NX`` with a TTL under ``routine-lock:<job>``. Whoever starts a
job — the button endpoint or the scheduler's wrapper task — takes the lock
*before* queueing and hands its token to the task; the task releases it when
it is done, also after a failure. The TTL is the task's time limit, so a lost
worker cannot block a job for longer than one run could take; before a retry
the task extends it by the backoff.

The value holds the start time, which is what the 409 says („Läuft bereits
seit …“). Release compares the token, so a run whose lock had expired cannot
drop the lock of the run that took over.

Without a Redis broker (the test suite runs on ``memory://``) an in-process
store with the same semantics stands in.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone

from dashboard_backend.core.config import settings

logger = logging.getLogger(__name__)

KEY_PREFIX = "routine-lock:"

# Celery's hard limit (celery_app: task_time_limit) — one run never takes longer.
DEFAULT_TTL_SECONDS = 1800

_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""

_EXTEND_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""


class JobAlreadyRunning(Exception):
    """The job holds a lock; ``since`` is when the running run started."""

    def __init__(self, job: str, since: datetime | None) -> None:
        self.job = job
        self.since = since
        super().__init__(f"{job} läuft bereits")


def _encode(token: str, started_at: datetime) -> str:
    return json.dumps({"token": token, "started_at": started_at.isoformat()})


def _decode(raw: str | bytes | None) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


class _MemoryStore:
    """Same semantics as the Redis calls below, for the test suite."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._mutex = threading.Lock()

    def _get_live(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        value, expires = item
        if expires <= time.monotonic():
            del self._data[key]
            return None
        return value

    def set_nx(self, key: str, value: str, ttl: int) -> bool:
        with self._mutex:
            if self._get_live(key) is not None:
                return False
            self._data[key] = (value, time.monotonic() + ttl)
            return True

    def get(self, key: str) -> str | None:
        with self._mutex:
            return self._get_live(key)

    def release(self, key: str, value: str) -> bool:
        with self._mutex:
            if self._get_live(key) == value:
                del self._data[key]
                return True
            return False

    def extend(self, key: str, value: str, ttl: int) -> bool:
        with self._mutex:
            if self._get_live(key) == value:
                self._data[key] = (value, time.monotonic() + ttl)
                return True
            return False

    def clear(self) -> None:
        with self._mutex:
            self._data.clear()


class _RedisStore:
    def __init__(self, url: str) -> None:
        import redis  # celery[redis] dependency

        self._client = redis.Redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)

    def set_nx(self, key: str, value: str, ttl: int) -> bool:
        return bool(self._client.set(key, value, nx=True, ex=ttl))

    def get(self, key: str) -> str | None:
        raw = self._client.get(key)
        return raw.decode() if isinstance(raw, bytes) else raw

    def release(self, key: str, value: str) -> bool:
        return bool(self._client.eval(_RELEASE_SCRIPT, 1, key, value))

    def extend(self, key: str, value: str, ttl: int) -> bool:
        return bool(self._client.eval(_EXTEND_SCRIPT, 1, key, value, ttl))


_store: _MemoryStore | _RedisStore | None = None


def _get_store() -> _MemoryStore | _RedisStore:
    global _store
    if _store is None:
        url = settings.celery_broker_url or ""
        _store = _RedisStore(url) if url.startswith(("redis://", "rediss://")) else _MemoryStore()
    return _store


def reset_for_tests() -> None:
    """Drop every lock of the in-process store (no-op against Redis)."""
    store = _get_store()
    if isinstance(store, _MemoryStore):
        store.clear()


def acquire(job: str, ttl: int = DEFAULT_TTL_SECONDS) -> str:
    """Take the lock of ``job`` and return its token.

    Raises :class:`JobAlreadyRunning` when another run holds it.
    """
    token = uuid.uuid4().hex
    value = _encode(token, datetime.now(timezone.utc))
    store = _get_store()
    if store.set_nx(KEY_PREFIX + job, value, ttl):
        return token
    raise JobAlreadyRunning(job, held_since(job))


def held_since(job: str) -> datetime | None:
    """Start time of the run that holds the lock, or ``None`` if it is free."""
    value = _decode(_get_store().get(KEY_PREFIX + job))
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value["started_at"])
    except (KeyError, TypeError, ValueError):
        return None


def _current_value(job: str, token: str) -> str | None:
    raw = _get_store().get(KEY_PREFIX + job)
    value = _decode(raw)
    if value is None or value.get("token") != token:
        return None
    return raw


def release(job: str, token: str | None) -> None:
    """Release the lock if ``token`` still holds it. Never raises."""
    if not token:
        return
    try:
        raw = _current_value(job, token)
        if raw is not None:
            _get_store().release(KEY_PREFIX + job, raw)
    except Exception:  # noqa: BLE001 — the TTL frees it anyway
        logger.warning("Could not release routine lock for %s", job, exc_info=True)


def extend(job: str, token: str | None, ttl: int) -> None:
    """Keep the lock for another ``ttl`` seconds (before a retry). Never raises."""
    if not token:
        return
    try:
        raw = _current_value(job, token)
        if raw is not None:
            _get_store().extend(KEY_PREFIX + job, raw, ttl)
    except Exception:  # noqa: BLE001
        logger.warning("Could not extend routine lock for %s", job, exc_info=True)
