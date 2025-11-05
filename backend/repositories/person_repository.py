"""Repository for Person model database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from models.person import Person
from repositories.base import BaseRepository


class PersonRepository(BaseRepository[Person]):
    """Repository wrapper with additional Person-specific queries."""

    def __init__(self, db: Session):
        super().__init__(Person, db)

    def get_by_folder_id(self, folder_id: str) -> Optional[Person]:
        return self._query().filter(Person.folder_id == folder_id).first()

    def get_by_name(self, name: str) -> Optional[Person]:
        return self._query().filter(Person.name == name).first()

    def search_by_name(self, name_pattern: str, limit: int = 10) -> List[Person]:
        return (
            self._query()
            .filter(Person.name.ilike(f"%{name_pattern}%"))
            .limit(limit)
            .all()
        )

    def get_all(self) -> List[Person]:
        return self._query().order_by(Person.created_at.asc()).all()

    def update_sample_face(self, person_id: int, sample_face_path: str) -> Optional[Person]:
        return self.update(person_id, {"sample_face_path": sample_face_path})

