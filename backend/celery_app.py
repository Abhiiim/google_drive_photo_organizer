"""Celery application instance for the Google Drive Face Organizer backend."""

from __future__ import annotations

from celery import Celery

from core.config import get_settings


settings = get_settings()

celery_app = Celery("google_drive_face_organizer")
celery_app.config_from_object("backend.celeryconfig")
celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
)
celery_app.autodiscover_tasks(["backend.tasks"])


__all__ = ["celery_app"]

