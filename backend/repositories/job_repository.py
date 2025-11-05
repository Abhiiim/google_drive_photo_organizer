"""Repository for Job tracking operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.job import Job, JobPhase, JobStatus
from repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository providing job-specific helpers."""

    def __init__(self, db: Session):
        super().__init__(Job, db)

    def create_job(self, job_data: Dict[str, Any]) -> Job:
        return super().create(job_data)

    def get(self, job_id: str) -> Optional[Job]:  # type: ignore[override]
        return self._query().filter(Job.id == job_id).first()

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
        phase: Optional[JobPhase] = None,
    ) -> Optional[Job]:
        update_payload: Dict[str, Any] = {"status": status}
        if progress is not None:
            update_payload["progress"] = progress
        if error_message is not None:
            update_payload["error_message"] = error_message
        if phase is not None:
            update_payload["phase"] = phase
        return self.update(job_id, update_payload)

    def get_by_status(self, status: JobStatus) -> List[Job]:
        return self._query().filter(Job.status == status).all()

    def list_jobs(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[JobStatus] = None,
    ) -> List[Job]:
        query = self._query()
        if status is not None:
            query = query.filter(Job.status == status)
        return (
            query.order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_jobs(self, status: Optional[JobStatus] = None) -> int:
        query = self._query()
        if status is not None:
            query = query.filter(Job.status == status)
        return query.count()


