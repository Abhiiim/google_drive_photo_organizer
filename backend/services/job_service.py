"""Service layer for job persistence and status tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.logger import get_logger
from models.job import Job, JobPhase, JobStatus
from repositories.job_repository import JobRepository


logger = get_logger(__name__)


def _default_result_metadata() -> Dict[str, Any]:
    return {
        "message": "Job created",
        "processing_stats": {},
        "multi_face_summary": {},
        "folders_created": 0,
        "review_required": [],
    }


STATUS_MAPPING: Dict[str, JobStatus] = {
    "pending": JobStatus.PENDING,
    "queued": JobStatus.PENDING,
    "processing": JobStatus.PROCESSING,
    "running": JobStatus.PROCESSING,
    "completed": JobStatus.COMPLETED,
    "success": JobStatus.COMPLETED,
    "failed": JobStatus.FAILED,
    "error": JobStatus.FAILED,
}


PHASE_MAPPING: Dict[str, JobPhase] = {
    "initialization": JobPhase.INITIALIZATION,
    "face_detection": JobPhase.FACE_DETECTION,
    "clustering": JobPhase.CLUSTERING,
    "organizing": JobPhase.ORGANIZING,
}


class JobService:
    """Business logic for job persistence."""

    def __init__(self, db: Session):
        self.db = db
        self.job_repo = JobRepository(db)

    # ------------------------------------------------------------------
    # Creation & retrieval
    # ------------------------------------------------------------------
    def create_job(
        self,
        *,
        folder_id: str,
        folder_name: Optional[str],
        total_photos: int = 0,
        user_id: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> Job:
        payload: Dict[str, Any] = {
            "folder_id": folder_id,
            "folder_name": folder_name,
            "status": JobStatus.PENDING,
            "phase": JobPhase.INITIALIZATION,
            "progress": 0,
            "total_photos": total_photos,
            "result_metadata": _default_result_metadata(),
            "user_id": user_id,
        }

        if job_id is not None:
            payload["id"] = job_id

        job = self.job_repo.create_job(payload)
        logger.info(
            "jobs.created",
            job_id=job.id,
            folder_id=folder_id,
            folder_name=folder_name,
            total_photos=total_photos,
        )
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.job_repo.get(job_id)
        if job is None:
            return None
        return self._serialize_job(job)

    def list_jobs(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        status_enum = STATUS_MAPPING.get(status.lower()) if status else None
        jobs = self.job_repo.list_jobs(skip=skip, limit=limit, status=status_enum)
        return [self._serialize_job(job) for job in jobs]

    def paginate_jobs(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        status_enum = STATUS_MAPPING.get(status.lower()) if status else None
        total = self.job_repo.count_jobs(status_enum)
        jobs = self.job_repo.list_jobs(skip=skip, limit=limit, status=status_enum)
        return {
            "total": total,
            "items": [self._serialize_job(job) for job in jobs],
        }

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------
    def update_job_state(self, job_id: str, state: Dict[str, Any]) -> Optional[Job]:
        job = self.job_repo.get(job_id)
        if job is None:
            logger.warning("jobs.update_state_missing", job_id=job_id)
            return None

        status_value = state.get("status")
        status_enum = STATUS_MAPPING.get(str(status_value).lower(), job.status)

        phase_value = state.get("phase")
        phase_enum = None
        if phase_value is not None:
            phase_enum = PHASE_MAPPING.get(str(phase_value).lower())

        def _coerce_int(value: Any, fallback: Optional[int]) -> Optional[int]:
            if value is None:
                return fallback
            try:
                return int(value)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                return fallback

        update_payload: Dict[str, Any] = {
            "status": status_enum,
            "progress": _coerce_int(state.get("progress_percentage"), job.progress),
            "processed_photos": _coerce_int(state.get("processed"), job.processed_photos),
            "total_photos": _coerce_int(state.get("total_photos"), job.total_photos),
            "faces_detected": _coerce_int(state.get("faces_detected"), job.faces_detected),
            "persons_found": _coerce_int(state.get("persons_found"), job.persons_found),
        }

        if phase_enum is not None:
            update_payload["phase"] = phase_enum

        message = state.get("message")
        folders_created = state.get("folders_created")
        metadata = dict(job.result_metadata or _default_result_metadata())
        if message is not None:
            metadata["message"] = message
        if folders_created is not None:
            metadata["folders_created"] = folders_created

        processing_stats = state.get("processing_stats")
        if isinstance(processing_stats, dict):
            metadata["processing_stats"] = processing_stats

        multi_face_summary = state.get("multi_face_summary")
        if isinstance(multi_face_summary, dict):
            metadata["multi_face_summary"] = multi_face_summary

        review_required = state.get("review_required")
        if isinstance(review_required, list):
            metadata["review_required"] = review_required

        clusters = state.get("clusters")
        if isinstance(clusters, dict):
            metadata["clusters"] = clusters

        update_payload["result_metadata"] = metadata

        error_message = state.get("error_message")
        if error_message:
            update_payload["error_message"] = error_message

        if status_enum == JobStatus.PROCESSING and job.started_at is None:
            update_payload["started_at"] = state.get("started_at") or datetime.utcnow()

        if status_enum in {JobStatus.COMPLETED, JobStatus.FAILED}:
            update_payload["completed_at"] = state.get("completed_at") or datetime.utcnow()

        updated_job = self.job_repo.update(job_id, update_payload)
        if updated_job:
            logger.debug("jobs.state_updated", job_id=job_id, status=status_enum.value)
        return updated_job

    def mark_failed(self, job_id: str, error_message: str) -> Optional[Job]:
        return self.job_repo.update(
            job_id,
            {
                "status": JobStatus.FAILED,
                "error_message": error_message,
            },
        )

    def set_celery_task(self, job_id: str, task_id: str) -> Optional[Job]:
        return self.job_repo.update(job_id, {"celery_task_id": task_id})

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------
    def delete_job(self, job_id: str) -> bool:
        return self.job_repo.delete(job_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _serialize_job(self, job: Job) -> Dict[str, Any]:
        metadata = job.result_metadata or _default_result_metadata()
        message = metadata.get("message", "")
        processing_stats = metadata.get("processing_stats", {}) or {}
        multi_face_summary = metadata.get("multi_face_summary", {}) or {}
        folders_created = metadata.get("folders_created", job.persons_found or 0)

        return {
            "job_id": job.id,
            "status": job.status.value if isinstance(job.status, JobStatus) else job.status,
            "message": message,
            "phase": (job.phase.value if isinstance(job.phase, JobPhase) else job.phase) or "initialization",
            "progress_percentage": job.progress or 0,
            "total_photos": job.total_photos or 0,
            "processed": job.processed_photos or 0,
            "faces_detected": job.faces_detected or 0,
            "persons_found": job.persons_found or 0,
            "folders_created": folders_created or 0,
            "processing_stats": processing_stats,
            "multi_face_summary": multi_face_summary,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }


__all__ = ["JobService"]


