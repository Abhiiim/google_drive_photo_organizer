"""Photo-related models and association tables."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import (
    Base,
    IntegerPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
    VersionedMixin,
)


class PhotoProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Photo(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionedMixin):
    """Metadata for photos processed during an organization job."""

    __tablename__ = "photos"

    job_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    drive_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_folder_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_multi_face: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    face_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_status: Mapped[PhotoProcessingStatus] = mapped_column(
        SQLEnum(PhotoProcessingStatus, name="photo_processing_status"),
        nullable=False,
        default=PhotoProcessingStatus.PENDING,
    )
    processing_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="photos")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="photos")
    person_links: Mapped[List["PhotoPerson"]] = relationship(
        "PhotoPerson",
        back_populates="photo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PhotoPerson(Base, IntegerPrimaryKeyMixin, TimestampMixin, VersionedMixin):
    """Association table linking photos and persons."""

    __tablename__ = "photo_persons"

    photo_id: Mapped[int] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_original_location: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    photo: Mapped["Photo"] = relationship("Photo", back_populates="person_links")
    person: Mapped["Person"] = relationship("Person", back_populates="photo_links")


Index("ix_photo_persons_photo_id_person_id", PhotoPerson.photo_id, PhotoPerson.person_id, unique=True)


__all__ = ["Photo", "PhotoPerson", "PhotoProcessingStatus"]


