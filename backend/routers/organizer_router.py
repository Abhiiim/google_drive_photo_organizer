"""Photo organizer API router with Celery-backed job orchestration."""

from typing import Any, Dict

from celery import states
from celery.result import AsyncResult
from fastapi import APIRouter, Request

from backend.celery_app import celery_app
from core.config import get_settings
from core.exceptions import JobNotFoundError, ProcessingError, ValidationError
from core.logger import get_logger
from database import session_scope
from schemas.organizer_shemas import JobCreateResponse, JobStatusResponse, OrganizeRequest
from tasks.photo_tasks import organize_photos_task
from services.job_service import JobService

organizer_router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


def _default_job_state(job_id: str) -> Dict[str, Any]:
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Job is queued for processing",
        "phase": "queued",
        "progress_percentage": 0,
        "total_photos": 0,
        "processed": 0,
        "faces_detected": 0,
        "persons_found": 0,
        "folders_created": 0,
        "processing_stats": {
            "total_photos": 0,
            "photos_processed": 0,
            "faces_detected": 0,
            "clusters_created": 0,
            "photos_with_faces": 0,
            "photos_without_faces": 0,
            "photos_with_single_face": 0,
            "photos_with_multiple_faces": 0,
            "processing_errors": 0,
        },
        "multi_face_summary": {
            "single_face_photos": 0,
            "multi_face_photos": 0,
            "no_face_photos": 0,
        },
    }


def _build_job_status(async_result: AsyncResult) -> Dict[str, Any]:
    job_id = async_result.id
    job_data = _default_job_state(job_id)

    meta = async_result.info if isinstance(async_result.info, dict) else {}
    result_payload = (
        async_result.result
        if async_result.successful() and isinstance(async_result.result, dict)
        else {}
    )

    for source in (meta, result_payload):
        for key, value in source.items():
            if key in {"processing_stats", "multi_face_summary"} and isinstance(value, dict):
                job_data[key].update(value)
            else:
                job_data[key] = value

    state = async_result.state
    if state == states.PENDING:
        job_data["status"] = "queued"
        job_data["message"] = "Job is waiting for an available worker"
        job_data["phase"] = "queued"
    elif state == states.STARTED:
        job_data["status"] = job_data.get("status", "processing")
        job_data["message"] = job_data.get("message", "Job is being processed")
        job_data["phase"] = job_data.get("phase", "processing")
    elif state == "PROGRESS":
        job_data["status"] = job_data.get("status", "processing")
    elif state == states.SUCCESS:
        job_data["status"] = job_data.get("status", "completed")
        job_data["phase"] = job_data.get("phase", "completed")
        job_data["progress_percentage"] = job_data.get("progress_percentage", 100)
    elif state == states.FAILURE:
        job_data["status"] = "error"
        if not job_data.get("message"):
            job_data["message"] = str(async_result.result)
        job_data["phase"] = "error"
        job_data["progress_percentage"] = job_data.get("progress_percentage", 0)

    job_data.setdefault(
        "multi_face_summary",
        {
            "single_face_photos": 0,
            "multi_face_photos": 0,
            "no_face_photos": 0,
        },
    )

    progress = job_data.get("progress_percentage", 0)
    try:
        job_data["progress_percentage"] = max(0, min(100, int(progress)))
    except (TypeError, ValueError):
        job_data["progress_percentage"] = 0

    return job_data


@organizer_router.post(
    "/api/organize",
    response_model=JobCreateResponse,
    tags=["Organization"],
    summary="Start photo organization job",
    description="Start a new photo organization job with face detection and clustering."
)
async def organize_photos(
    request: OrganizeRequest,
    req: Request,
):
    """
    Start enhanced photo organization process with configurable parameters.

    - **drive_folder_link**: Google Drive folder URL or folder ID
    - **max_photos**: Maximum number of photos to process (optional)
    - **distance_threshold**: Face similarity threshold for clustering (0.0-1.0)
    - **verification_threshold**: Face quality threshold for detection (0.0-1.0)
    - **face_detection_model**: Face detection backend to use
    """
    try:
        with session_scope() as session:
            job_service = JobService(session)
            job = job_service.create_job(
                folder_id=request.drive_folder_link,
                folder_name=None,
                total_photos=request.max_photos or 0,
            )

        async_result = organize_photos_task.apply_async(
            args=(request.model_dump(),),
            task_id=job.id,
            queue=settings.celery_task_default_queue,
        )

        with session_scope() as session:
            job_service = JobService(session)
            job_service.set_celery_task(job.id, async_result.id)
            job_service.update_job_state(
                job.id,
                {
                    "status": "pending",
                    "message": "Job queued for processing",
                    "phase": "initialization",
                    "total_photos": request.max_photos or 0,
                    "processed": 0,
                    "faces_detected": 0,
                    "persons_found": 0,
                },
            )

        logger.info(
            "job.enqueued",
            job_id=job.id,
            queue=settings.celery_task_default_queue,
            drive_folder_link=request.drive_folder_link,
            max_photos=request.max_photos,
            face_detection_model=request.face_detection_model,
        )

        return JobCreateResponse(job_id=job.id)

    except ValidationError as e:
        # Re-raise validation errors (handled by global error handler)
        e.path = str(req.url)
        raise e
    except Exception as e:
        logger.exception("job.creation.failed", error=str(e))
        raise ProcessingError(
            message="Failed to create photo organization job",
            details={"error": str(e)},
            path=str(req.url)
        )


@organizer_router.get(
    "/api/status/{job_id}",
    response_model=JobStatusResponse,
    tags=["Organization"],
    summary="Get job status",
    description="Retrieve the current status and progress of a photo organization job."
)
async def get_job_status(job_id: str, req: Request):
    """
    Get the status of a photo organization job.

    Returns detailed information about the job including:
    - Current status and phase
    - Progress percentage
    - Processing statistics
    - Face detection results
    """
    try:
        async_result = AsyncResult(job_id, app=celery_app)

        if async_result is None or (async_result.state == states.PENDING and not async_result.info):
            raise JobNotFoundError(job_id=job_id, path=str(req.url))

        job_state = _build_job_status(async_result)

        logger.debug("job.status.retrieved", job_id=job_id, status=job_state.get("status"))

        return job_state

    except JobNotFoundError:
        # Re-raise to be handled by global error handler
        raise
    except Exception as e:
        logger.exception("job.status.retrieval.failed", job_id=job_id, error=str(e))
        raise ProcessingError(
            message="Failed to retrieve job status",
            details={"job_id": job_id, "error": str(e)},
            path=str(req.url)
        )

