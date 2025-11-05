"""Job model and related enumerations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import DateTime, Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin, VersionedMixin, generate_uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobPhase(str, Enum):
    INITIALIZATION = "initialization"
    FACE_DETECTION = "face_detection"
    CLUSTERING = "clustering"
    ORGANIZING = "organizing"


class Job(Base, TimestampMixin, SoftDeleteMixin, VersionedMixin):
    """Track end-to-end organization jobs."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    folder_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    folder_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    phase: Mapped[Optional[JobPhase]] = mapped_column(
        SQLEnum(JobPhase, name="job_phase"),
        nullable=True,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_photos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_photos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    faces_detected: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    persons_found: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    result_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="jobs")
    persons: Mapped[List["Person"]] = relationship("Person", back_populates="job")
    photos: Mapped[List["Photo"]] = relationship("Photo", back_populates="job")


__all__ = ["Job", "JobStatus", "JobPhase"]


