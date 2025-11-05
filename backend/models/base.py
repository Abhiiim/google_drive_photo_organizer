"""SQLAlchemy declarative base and shared mixins."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


def generate_uuid() -> str:
    """Return a string-based UUID suitable for primary keys."""

    return str(uuid4())


# Ensure deterministic constraint names for Alembic
NAMING_CONVENTION: Dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base class with a shared naming convention."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Mixin providing created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """Mixin adding soft-delete support via a nullable timestamp."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )


class VersionedMixin:
    """Mixin enabling optimistic locking via a version column."""

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    @declared_attr.directive
    def __mapper_args__(cls) -> Dict[str, Any]:  # type: ignore[override]
        return {
            "version_id_col": cls.version,
            "version_id_generator": False,
        }


class IntegerPrimaryKeyMixin:
    """Mixin that defines an autoincrementing integer primary key."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "VersionedMixin",
    "IntegerPrimaryKeyMixin",
    "generate_uuid",
]


