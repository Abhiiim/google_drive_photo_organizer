from typing import Any, Callable, Dict, Optional

from schemas.organizer_shemas import OrganizeRequest
from photo_organizer.photo_organizer import PhotoOrganizer
from core.logger import bind_contextvars, clear_contextvars, get_logger


logger = get_logger(__name__)


JobState = Dict[str, Any]
StatusUpdater = Callable[[JobState], None]


def _initial_job_state(job_id: str) -> JobState:
    """Return the default job state structure."""

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Starting enhanced photo organization...",
        "phase": "initialization",
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
        "clusters": {},
        "review_required": [],
    }


def _clone_state(state: JobState) -> JobState:
    """Return a shallow copy of the job state with nested structures copied."""

    cloned: JobState = state.copy()
    cloned["processing_stats"] = dict(state.get("processing_stats", {}))
    cloned["multi_face_summary"] = dict(state.get("multi_face_summary", {}))
    cloned["clusters"] = dict(state.get("clusters", {}))
    cloned["review_required"] = list(state.get("review_required", []))
    return cloned


def _calculate_progress(processed: int, total: int) -> int:
    """Calculate progress percentage with bounds checking."""

    if total <= 0:
        return 0
    return min(100, max(0, round((processed / total) * 100)))


async def process_photos_enhanced(
    job_id: str,
    request: OrganizeRequest,
    status_updater: StatusUpdater,
) -> JobState:
    """Enhanced photo processing orchestrator with structured progress updates."""

    organizer = None
    job_state = _initial_job_state(job_id)
    status_updater(_clone_state(job_state))

    try:
        bind_contextvars(job_id=job_id)
        try:
            organizer = PhotoOrganizer(
                distance_threshold=request.distance_threshold,
                verification_threshold=request.verification_threshold,
            )
            logger.info("jobs.organizer_initialized", job_id=job_id)
        except Exception as init_error:  # pragma: no cover - defensive
            raise Exception(f"Failed to initialize organizer: {str(init_error)}") from init_error

        try:
            organizer.face_detector.face_detection_model = request.face_detection_model
        except AttributeError:
            logger.warning(
                "jobs.face_detection_model_not_set",
                job_id=job_id,
                requested_model=request.face_detection_model,
            )

        def emit_state(
            *,
            message: str,
            phase: Optional[str] = None,
            processed: Optional[int] = None,
            total_photos: Optional[int] = None,
            status: Optional[str] = None,
        ) -> None:
            if status is not None:
                job_state["status"] = status
            if phase is not None:
                job_state["phase"] = phase
            job_state["message"] = message

            if processed is not None:
                job_state["processed"] = processed
            if total_photos is not None:
                job_state["total_photos"] = total_photos

            stats = getattr(organizer, "processing_stats", {}) or {}
            if stats:
                job_state["processing_stats"] = dict(stats)
                job_state["faces_detected"] = stats.get("faces_detected", job_state["faces_detected"])
                photos_processed = stats.get("photos_processed")
                if (
                    photos_processed is not None
                    and photos_processed >= 0
                    and photos_processed >= job_state["processed"]
                ):
                    job_state["processed"] = photos_processed
                total_photos_stat = stats.get("total_photos")
                if (
                    total_photos_stat is not None
                    and total_photos_stat >= 0
                    and total_photos_stat >= job_state["total_photos"]
                ):
                    job_state["total_photos"] = total_photos_stat
                job_state["multi_face_summary"] = {
                    "single_face_photos": stats.get("photos_with_single_face", 0),
                    "multi_face_photos": stats.get("photos_with_multiple_faces", 0),
                    "no_face_photos": stats.get("photos_without_faces", 0),
                }

            job_state["progress_percentage"] = _calculate_progress(
                job_state["processed"],
                job_state["total_photos"],
            )

            status_updater(_clone_state(job_state))

        def update_progress(message: str, **kwargs: Any) -> None:
            try:
                phase = kwargs.get("phase")
                if phase is None:
                    lower_message = message.lower()
                    if "phase 1" in lower_message or "face_detection" in lower_message:
                        phase = "face_detection"
                    elif "phase 2" in lower_message or "clustering" in lower_message:
                        phase = "clustering"
                    elif "phase 3" in lower_message or "folder_creation" in lower_message:
                        phase = "folder_creation"
                    elif "phase 4" in lower_message or "organization" in lower_message:
                        phase = "organization"
                    elif "phase 5" in lower_message or "report" in lower_message:
                        phase = "reporting"

                emit_state(
                    message=message,
                    phase=phase,
                    processed=kwargs.get("processed"),
                    total_photos=kwargs.get("total_photos"),
                )

                logger.debug(
                    "jobs.progress_update",
                    job_id=job_id,
                    message=message,
                    phase=phase,
                    processed=kwargs.get("processed"),
                    total_photos=kwargs.get("total_photos"),
                )
            except Exception as progress_error:  # pragma: no cover - logging safeguard
                logger.warning(
                    "jobs.progress_update_failed",
                    job_id=job_id,
                    error=str(progress_error),
                )

        emit_state(message="Organizer initialized", phase="initialization")

        await organizer.organize_folder(
            request.drive_folder_link,
            update_progress,
            max_photos=request.max_photos,
        )

        stats = getattr(organizer, "processing_stats", {})
        persons_found = len(getattr(organizer, "face_database", {}))
        job_state["processing_stats"] = dict(stats)
        job_state["faces_detected"] = stats.get("faces_detected", job_state["faces_detected"])
        photos_processed = stats.get("photos_processed")
        if (
            photos_processed is not None
            and photos_processed >= 0
            and photos_processed >= job_state["processed"]
        ):
            job_state["processed"] = photos_processed
        total_photos_stat = stats.get("total_photos")
        if (
            total_photos_stat is not None
            and total_photos_stat >= 0
            and total_photos_stat >= job_state["total_photos"]
        ):
            job_state["total_photos"] = total_photos_stat
        job_state["progress_percentage"] = _calculate_progress(
            job_state["processed"],
            job_state["total_photos"],
        )
        job_state["persons_found"] = persons_found
        job_state["folders_created"] = persons_found
        job_state["multi_face_summary"] = {
            "single_face_photos": stats.get("photos_with_single_face", 0),
            "multi_face_photos": stats.get("photos_with_multiple_faces", 0),
            "no_face_photos": stats.get("photos_without_faces", 0),
        }

        job_state["status"] = "completed"
        job_state["phase"] = "completed"
        job_state["message"] = "Organization completed successfully"

        logger.info("jobs.completed", job_id=job_id)
        final_state = _clone_state(job_state)
        status_updater(final_state)
        return final_state

    except Exception as err:
        job_state["status"] = "error"
        job_state["phase"] = "error"
        job_state["message"] = f"Error: {str(err)}"
        status_updater(_clone_state(job_state))
        logger.exception("jobs.failed", job_id=job_id, error=str(err))
        raise

    finally:
        if organizer is not None:
            try:
                organizer.cleanup()
                logger.debug("jobs.cleanup_completed", job_id=job_id)
            except Exception as cleanup_error:  # pragma: no cover - cleanup safeguard
                logger.warning(
                    "jobs.cleanup_failed",
                    job_id=job_id,
                    error=str(cleanup_error),
                )
        clear_contextvars()
