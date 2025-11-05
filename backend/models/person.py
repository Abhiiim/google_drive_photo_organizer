"""Person model definition."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import (
    Base,
    IntegerPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
    VersionedMixin,
)


class Person(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionedMixin):
    """Represents a clustered person in an organization job."""

    __tablename__ = "persons"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Person")
    folder_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sample_face_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    face_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="persons")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="persons")
    photo_links: Mapped[List["PhotoPerson"]] = relationship(
        "PhotoPerson",
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


__all__ = ["Person"]


