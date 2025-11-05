"""User model definition."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, IntegerPrimaryKeyMixin, SoftDeleteMixin, TimestampMixin, VersionedMixin
from models.types import EncryptedText


class User(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionedMixin):
    """Application user record holding authentication and Drive data."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    google_drive_token: Mapped[Optional[str]] = mapped_column(EncryptedText(), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    persons: Mapped[List["Person"]] = relationship(
        "Person",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    photos: Mapped[List["Photo"]] = relationship(
        "Photo",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


__all__ = ["User"]


