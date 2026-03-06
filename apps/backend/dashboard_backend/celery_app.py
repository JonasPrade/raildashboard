from celery import Celery
from dashboard_backend.core.config import settings

celery_app = Celery(
    "dashboard_backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["dashboard_backend.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,  # results expire after 1 hour
)
