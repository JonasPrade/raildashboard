# Feature: Systemstatus der Hintergrund-Aufträge

## Goal

Make a stalled background job explain itself. Every import (Haushalt, VIB,
Fulda, Bauportal, Abgeordnete) runs as a Celery job; if no worker is running,
the upload still succeeds, Celery answers `PENDING` forever and the import page
spins without ever saying why. The admin area gets a place to check broker and
workers, and a waiting job names its own cause instead of leaving the user to
guess whether the file, the parser or the stack is at fault.

## Scope

Three separate things, all triggered by the same failure mode:

1. **Honest progress.** The Haushalt parse reported `rows_found: 0` on every
   page, so the page read „Seite 12 / 42 — 0 Zeilen gefunden" for the whole run
   and a working import looked like one that finds nothing. The counter now
   holds the table rows actually read, and every stage after the extraction
   (Spaltenzuordnung, OCR, Speichern) reports a label of its own instead of
   freezing on the last page number.
2. **Worker check in the admin area.** `/admin/system` shows broker
   reachability, every worker that answers a ping with what it is working on,
   the queue length, and the commands to run when something is off. The admin
   overview carries a badge so an offline worker is visible without opening the
   page.
3. **Actionable errors.** A pending job carries a `hint` explaining *why* it has
   not started (no worker / broker unreachable), and a failed one names the
   exception class, its message and the file and line it was raised in, plus
   where the full traceback lives.

Out of scope: restarting a worker from the UI, retrying or cancelling a job,
metrics history. The page diagnoses, it does not operate the stack.

## Behaviour

| Situation | What the user sees |
|---|---|
| Worker online, job running | stage label from the task („Seite 12 / 42 gelesen — 318 Tabellenzeilen", „Tabellen zuordnen…", „141 Maßnahmen — Ergebnis wird gespeichert…") |
| Job pending > 12 s, no worker | orange note under the progress bar naming the cause, with a link to `/admin/system` |
| Broker unreachable | same, with the Redis wording and the `docker compose ps redis` command |
| Job failed | red toast (does not auto-close) with `ExceptionClass: message`, the file:line it was raised in, and the worker-log command |

The 12-second grace period keeps a healthy stack from ever showing the warning —
a running worker picks a job up within a poll or two.

## Technical notes

- `services/worker_health.py` — one bounded probe: broker connection, Celery
  `inspect.ping()/active()/stats()`, Redis queue length. Every failure becomes a
  value (`status` + `detail`), never an exception; the broker URL is handed out
  without its credentials. A 5-second TTL cache keeps the 1.5-second status
  polling from broadcasting a ping per poll.
- `GET /api/v1/tasks/workers` (capability `settings.manage`, `?refresh=true`
  bypasses the cache) — the admin page.
- `GET /api/v1/tasks/{task_id}` gained `hint`; it is filled from the cached
  health while a job is `PENDING` and from the traceback on `FAILURE`.
- Frontend: `useWorkerHealth` / `useRecheckWorkerHealth`,
  `features/admin/SystemStatusPage.tsx`, and `useImportTask().warning` which the
  three import pages render under their progress bar.

## Acceptance criteria

- [x] The Haushalt progress counter grows with the pages read and never sticks
      at 0 while rows are being found.
- [x] Each stage of the parse reports its own label.
- [x] `/admin/system` shows broker, workers and queue length and re-probes on
      demand; the admin overview badges an offline worker.
- [x] An import whose job nobody picks up says so within ~15 seconds and links
      to the status page.
- [x] A failed job reports exception, location and where to find the traceback.
- [x] A dead broker never hangs a request (every probe carries a timeout).
