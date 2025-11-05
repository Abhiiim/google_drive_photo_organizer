"""Base repository for common database operations with soft-delete support."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from models.base import Base


ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with convenience methods for CRUD operations."""

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    # Query helpers -----------------------------------------------------------------
    def _query(self):
        query = self.db.query(self.model)
        if hasattr(self.model, "deleted_at"):
            query = query.filter(getattr(self.model, "deleted_at").is_(None))
        return query

    # CRUD operations ----------------------------------------------------------------
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get(self, id: Any) -> Optional[ModelType]:
        return self._query().filter(self.model.id == id).first()

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        query = self._query()
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
        return query.offset(skip).limit(limit).all()

    def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        db_obj = self.get(id)
        if db_obj is None:
            return None
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: Any) -> bool:
        db_obj = self.get(id)
        if db_obj is None:
            return False

        if hasattr(db_obj, "deleted_at"):
            setattr(db_obj, "deleted_at", datetime.now(timezone.utc))
        else:
            self.db.delete(db_obj)

        self.db.commit()
        return True

    def hard_delete(self, id: Any) -> bool:
        db_obj = self._query().filter(self.model.id == id).first()
        if db_obj is None:
            return False
        self.db.delete(db_obj)
        self.db.commit()
        return True

    def restore(self, id: Any) -> Optional[ModelType]:
        if not hasattr(self.model, "deleted_at"):
            return self.get(id)
        obj = self.db.query(self.model).filter(self.model.id == id).first()
        if obj is None or getattr(obj, "deleted_at") is None:
            return obj
        setattr(obj, "deleted_at", None)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        query = self._query()
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
        return query.count()

    def exists(self, id: Any) -> bool:
        return self._query().filter(self.model.id == id).count() > 0

