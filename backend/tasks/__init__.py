"""Celery tasks package for the Google Drive Face Organizer backend."""

from .photo_tasks import organize_photos_task

__all__ = ["organize_photos_task"]

