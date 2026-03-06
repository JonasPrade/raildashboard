import time

from dashboard_backend.celery_app import celery_app


@celery_app.task
def add(x: int, y: int) -> int:
    """Demo task: adds two numbers after a short delay."""
    time.sleep(2)
    return x + y
