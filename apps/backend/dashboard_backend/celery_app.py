from celery import Celery
from dashboard_backend.core.config import settings

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
)
