"""Celery tasks handling photo organization workflows."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from celery import shared_task, states
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import ProcessingError, ValidationError
from core.logger import bind_contextvars, clear_contextvars, get_logger
from database import session_scope
from helper.process_photos_enhanced import process_photos_enhanced
from schemas.organizer_shemas import OrganizeRequest
from services.job_service import JobService


logger = get_logger(__name__)


def _clone_state(state: Dict[str, Any]) -> Dict[str, Any]:
    cloned = state.copy()
    if "processing_stats" in state:
        cloned["processing_stats"] = dict(state["processing_stats"])
    if "multi_face_summary" in state:
        cloned["multi_face_summary"] = dict(state["multi_face_summary"])
    if "clusters" in state:
        cloned["clusters"] = dict(state["clusters"])
    if "review_required" in state:
        cloned["review_required"] = list(state["review_required"])
    return cloned


@shared_task(
    bind=True,
    name="backend.tasks.photo_tasks.organize_photos_task",
    autoretry_for=(ProcessingError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def organize_photos_task(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point for the full photo organization workflow."""

    job_id = self.request.id
    current_state: Dict[str, Any] = {
        "job_id": job_id,
        "status": "processing",
        "message": "Queued for processing",
        "phase": "initialization",
        "progress_percentage": 0,
        "total_photos": 0,
        "processed": 0,
        "faces_detected": 0,
        "persons_found": 0,
        "folders_created": 0,
        "processing_stats": {},
        "multi_face_summary": {},
    }

    def _persist_state(state: Dict[str, Any]) -> None:
        try:
            with session_scope() as session:
                JobService(session).update_job_state(job_id, state)
        except Exception as exc:  # pragma: no cover - persistence safeguard
            logger.warning(
                "tasks.job_state_persist_failed",
                job_id=job_id,
                error=str(exc),
            )

    def status_updater(update: Dict[str, Any]) -> None:
        nonlocal current_state

        current_state.update(update)
        current_state.setdefault("job_id", job_id)
        meta = _clone_state(current_state)

        status = current_state.get("status", "processing")
        if status == "completed":
            state_name = states.SUCCESS
        elif status == "error":
            state_name = states.FAILURE
        else:
            state_name = "PROGRESS"

        self.update_state(state=state_name, meta=meta)
        _persist_state(meta)

    status_updater({})

    try:
        bind_contextvars(job_id=job_id)

        try:
            request_model = OrganizeRequest.model_validate(request_payload)
        except (ValidationError, PydanticValidationError) as validation_error:
            current_state["status"] = "error"
            current_state["message"] = str(validation_error)
            status_updater({})
            raise

        final_state = asyncio.run(
            process_photos_enhanced(job_id, request_model, status_updater)
        )

        current_state.update(final_state)
        return _clone_state(current_state)

    except Exception as exc:
        logger.exception("tasks.organize_photos.failed", job_id=job_id, error=str(exc))
        current_state["status"] = "error"
        current_state["message"] = f"Error: {exc}"
        current_state["error_message"] = str(exc)
        status_updater({})
        raise

    finally:
        clear_contextvars()


@shared_task(
    bind=True,
    name="backend.tasks.photo_tasks.process_single_photo_task",
    max_retries=0,
)
def process_single_photo_task(self, photo_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder task for per-photo processing; returns metadata for now."""

    photo_id = photo_payload.get("id")
    logger.info("tasks.process_single_photo.received", photo_id=photo_id)

    return {
        "photo_id": photo_id,
        "status": "queued",
        "details": {
            "name": photo_payload.get("name"),
            "metadata": photo_payload.get("metadata", {}),
        },
    }

