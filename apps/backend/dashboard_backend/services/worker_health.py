"""Is anything actually working off the queue? — health of the Celery workers.

A background job nobody picks up looks exactly like a slow one: Celery reports
``PENDING`` for both, and the import pages poll that status forever without ever
saying why.  This module answers what the status alone cannot — is the broker
reachable, is a worker online, what is it working on — so the admin area can
show it and a hanging import can name its own cause.

Two rules hold for every probe here:

* **Bounded.** Each call carries a timeout; a health check that hangs would be
  worse than the problem it reports.
* **Never raising.** Every failure becomes a value (``status`` plus ``detail``),
  because the caller asks this precisely when something is already broken.

The broker URL is only ever handed out with its credentials stripped — the
answer names the host, never the password.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit, urlunsplit

from dashboard_backend.celery_app import celery_app
from dashboard_backend.core.config import settings
from dashboard_backend.schemas.tasks import WorkerHealthSchema, WorkerSchema

logger = logging.getLogger(__name__)

# Long enough for a worker on the same docker network to answer a broadcast,
# short enough that an admin page never feels stuck on a dead broker.
PROBE_TIMEOUT_SECONDS = 1.0

# The task-status endpoint is polled every 1.5 s per running import; without a
# cache every poll would broadcast a ping to every worker.
_CACHE_TTL_SECONDS = 5.0

_cached: tuple[float, WorkerHealthSchema] | None = None


def sanitize_broker_url(url: str | None) -> str:
    """The broker URL without its credentials — safe to show in the UI."""
    if not url:
        return ""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "(unlesbare Broker-URL)"
    if not parts.hostname:
        return url
    host = parts.hostname
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def _probe_broker(timeout: float) -> tuple[bool, str | None]:
    """Can we reach the broker at all? Returns (reachable, error description)."""
    try:
        with celery_app.connection() as connection:
            connection.ensure_connection(max_retries=0, timeout=timeout)
        return True, None
    except Exception as exc:  # any transport error — this is the diagnosis
        return False, f"{type(exc).__name__}: {exc}"[:300]


def _probe_workers(timeout: float) -> tuple[list[WorkerSchema], str | None]:
    """Every worker that answers the broadcast ping, with what it is doing."""
    try:
        inspector = celery_app.control.inspect(timeout=timeout)
        # Each broadcast waits out the full timeout — nobody knows how many
        # workers should answer — so the "no worker" case, the one this whole
        # module exists for, must not pay for three of them.
        ping = inspector.ping() or {}
        if not ping:
            return [], None
        active = inspector.active() or {}
        stats = inspector.stats() or {}
    except Exception as exc:
        logger.warning("Worker inspection failed: %s", exc)
        return [], f"{type(exc).__name__}: {exc}"[:300]

    workers: list[WorkerSchema] = []
    for name in sorted(ping):
        running = active.get(name) or []
        pool = (stats.get(name) or {}).get("pool") or {}
        workers.append(
            WorkerSchema(
                name=name,
                active_tasks=len(running),
                active_task_names=sorted({str(task.get("name") or "?") for task in running}),
                concurrency=pool.get("max-concurrency"),
            )
        )
    return workers, None


def _queued_tasks(timeout: float) -> int | None:
    """How many jobs wait in the default queue — Redis brokers only, else None."""
    url = settings.celery_broker_url or ""
    if not url.startswith(("redis://", "rediss://")):
        return None
    queue = celery_app.conf.task_default_queue or "celery"
    try:
        with celery_app.connection_for_read() as connection:
            connection.ensure_connection(max_retries=0, timeout=timeout)
            return int(connection.default_channel.client.llen(queue))
    except Exception as exc:
        logger.debug("Queue length unavailable: %s", exc)
        return None


# What to do about it — the message is the point of the whole check, so it names
# the next command instead of just the state.
_BROKER_DOWN = (
    "Die Aufgaben-Warteschlange (Redis) ist nicht erreichbar. Hintergrund-Aufträge "
    "können weder angenommen noch abgearbeitet werden. Prüfen: "
    "`docker compose ps redis` und `docker compose logs --tail=50 redis`."
)
_NO_WORKERS = (
    "Kein Worker online. Aufträge werden angenommen, aber niemand arbeitet sie ab — "
    "ein Import bleibt dann endlos im Status „wird verarbeitet“. Prüfen: "
    "`docker compose ps worker` und `docker compose logs --tail=50 worker` "
    "(lokal: `make celery-worker`)."
)


def worker_health(timeout: float = PROBE_TIMEOUT_SECONDS) -> WorkerHealthSchema:
    """One bounded look at broker and workers, with a next step in the message."""
    broker_url = sanitize_broker_url(settings.celery_broker_url)
    reachable, detail = _probe_broker(timeout)

    if not reachable:
        return WorkerHealthSchema(
            status="broker_unreachable",
            broker_reachable=False,
            broker_url=broker_url,
            workers=[],
            queued_tasks=None,
            message=_BROKER_DOWN,
            detail=detail,
            checked_at=time.time(),
        )

    workers, inspect_error = _probe_workers(timeout)
    queued = _queued_tasks(timeout)

    if not workers:
        return WorkerHealthSchema(
            status="no_workers",
            broker_reachable=True,
            broker_url=broker_url,
            workers=[],
            queued_tasks=queued,
            message=_NO_WORKERS,
            detail=inspect_error,
            checked_at=time.time(),
        )

    busy = sum(worker.active_tasks for worker in workers)
    waiting = f", {queued} in der Warteschlange" if queued else ""
    return WorkerHealthSchema(
        status="ok",
        broker_reachable=True,
        broker_url=broker_url,
        workers=workers,
        queued_tasks=queued,
        message=(
            f"{len(workers)} Worker online, {busy} Auftrag/Aufträge in Arbeit{waiting}."
        ),
        detail=None,
        checked_at=time.time(),
    )


def cached_worker_health(ttl: float = _CACHE_TTL_SECONDS) -> WorkerHealthSchema:
    """``worker_health`` for the polling path — at most one probe per ``ttl``."""
    global _cached
    now = time.time()
    if _cached is not None and now - _cached[0] < ttl:
        return _cached[1]
    health = worker_health()
    _cached = (now, health)
    return health


def reset_cache() -> None:
    """Drop the cached probe — for an explicit re-check and for the tests."""
    global _cached
    _cached = None
