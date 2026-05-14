"""
Celery worker entry point.
Run via: celery -A worker.main worker --loglevel=info
Or via Docker CMD in Dockerfile.worker.
"""
from worker.celery_app import celery_app  # noqa: F401 — triggers task registration
import worker.tasks  # noqa: F401
