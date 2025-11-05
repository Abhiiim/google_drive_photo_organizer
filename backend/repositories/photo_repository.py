"""Repository for Photo model database operations."""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models.photo import Photo, PhotoPerson
from repositories.base import BaseRepository


class PhotoRepository(BaseRepository[Photo]):
    """Repository with helpers for photo lookups and statistics."""

    def __init__(self, db: Session):
        super().__init__(Photo, db)

    def get_by_drive_id(self, drive_id: str) -> Optional[Photo]:
        return self._query().filter(Photo.drive_id == drive_id).first()

    def get_by_photo_name(self, photo_name: str) -> Optional[Photo]:
        return self._query().filter(Photo.name == photo_name).first()

    def get_links_by_person(self, person_id: int) -> List[PhotoPerson]:
        return (
            self.db.query(PhotoPerson)
            .join(Photo, Photo.id == PhotoPerson.photo_id)
            .filter(PhotoPerson.person_id == person_id)
            .filter(Photo.deleted_at.is_(None))
            .all()
        )

    def get_stats_for_person(self, person_id: int) -> Dict[str, int]:
        total_count, original_count = (
            self.db.query(
                func.count(PhotoPerson.id),
                func.coalesce(
                    func.sum(
                        case((PhotoPerson.is_original_location.is_(True), 1), else_=0)
                    ),
                    0,
                ),
            )
            .join(Photo, Photo.id == PhotoPerson.photo_id)
            .filter(PhotoPerson.person_id == person_id)
            .filter(Photo.deleted_at.is_(None))
            .one()
        )

        return {
            "total": int(total_count or 0),
            "original": int(original_count or 0),
            "copies": int(total_count or 0) - int(original_count or 0),
        }

    def get_multi_face_photos(self) -> List[Photo]:
        return self._query().filter(Photo.is_multi_face.is_(True)).all()

    def get_photos_in_folder(self, folder_id: str) -> List[Photo]:
        return self._query().filter(Photo.original_folder_id == folder_id).all()

