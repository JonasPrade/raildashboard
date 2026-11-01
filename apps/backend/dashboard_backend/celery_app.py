from celery import Celery
from dashboard_backend.core.config import settings
from dashboard_backend.schedule import TIMEZONE, build_beat_schedule

celery_app = Celery(
    "dashboard_backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "dashboard_backend.tasks.vib",
        "dashboard_backend.tasks.vib_ai_extraction",
        "dashboard_backend.tasks.haushalt",
        "dashboard_backend.tasks.gvfg",
        "dashboard_backend.tasks.infraplan",
        "dashboard_backend.tasks.parliament",
        "dashboard_backend.tasks.progress",
        "dashboard_backend.tasks.project_overlap",
        "dashboard_backend.tasks.bauportal",
        "dashboard_backend.tasks.routine",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,  # results expire after 1 hour
    # A worker crash must not silently lose an import: acknowledge only after
    # the task ran, so a lost worker puts it back on the queue. Hard limit
    # 30 min, soft limit 25 min so a hanging OCR/LLM call ends with an error.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=1800,
    task_soft_time_limit=1500,
    # Scheduled routine jobs, run by the `scheduler` service (`celery beat`).
    # The timetable lives in dashboard_backend/schedule.py; crontab entries are
    # read in Europe/Berlin. ROUTINE_JOBS_ENABLED=false leaves it empty, so Beat
    # queues nothing. Beat's state file goes to /tmp: crontab schedules need no
    # history, and nothing stays in the container outside a volume.
    timezone=TIMEZONE,
    beat_schedule=build_beat_schedule(settings.routine_jobs_enabled),
    beat_schedule_filename="/tmp/celerybeat-schedule",
)
