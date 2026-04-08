# Task modules are imported here so that the Celery worker discovers them
# automatically when started with -A dashboard_backend.celery_app.
from dashboard_backend.tasks import debug  # noqa: F401
from dashboard_backend.tasks import haushalt  # noqa: F401
from dashboard_backend.tasks import vib  # noqa: F401
