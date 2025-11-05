"""Celery tasks for Google Drive related operations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from celery import shared_task

from core.exceptions import GoogleDriveError
from core.logger import get_logger
from google_drive.google_drive import GoogleDriveClient


logger = get_logger(__name__)


@shared_task(
    bind=True,
    name="backend.tasks.drive_tasks.download_photo_task",
    autoretry_for=(GoogleDriveError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def download_photo_task(
    self,
    file_id: str,
    destination_path: str,
) -> Dict[str, Any]:
    """Download a single photo from Google Drive."""

    logger.info("tasks.download_photo.start", file_id=file_id, destination=destination_path)

    client = GoogleDriveClient()
    try:
        client.download_file(file_id, destination_path)
    except Exception as exc:
        logger.exception(
            "tasks.download_photo.failed",
            file_id=file_id,
            destination=destination_path,
            error=str(exc),
        )
        raise GoogleDriveError(
            message="Failed to download photo from Google Drive",
            details={"file_id": file_id, "destination_path": destination_path},
        ) from exc

    logger.info("tasks.download_photo.completed", file_id=file_id, destination=destination_path)
    return {"file_id": file_id, "destination_path": destination_path}


@shared_task(
    bind=True,
    name="backend.tasks.drive_tasks.list_folder_images_task",
    autoretry_for=(GoogleDriveError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def list_folder_images_task(
    self,
    folder_id: str,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """List images within a Google Drive folder."""

    logger.info("tasks.list_folder_images.start", folder_id=folder_id, max_results=max_results)

    client = GoogleDriveClient()
    try:
        images = client.list_images(folder_id)
    except Exception as exc:
        logger.exception("tasks.list_folder_images.failed", folder_id=folder_id, error=str(exc))
        raise GoogleDriveError(
            message="Failed to list images from Google Drive folder",
            details={"folder_id": folder_id},
        ) from exc

    if max_results is not None and max_results > 0:
        images = images[:max_results]

    logger.info(
        "tasks.list_folder_images.completed",
        folder_id=folder_id,
        image_count=len(images),
    )
    return {"folder_id": folder_id, "images": images}

