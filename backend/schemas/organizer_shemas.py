from typing import Optional

from pydantic import BaseModel

from core.config import get_settings


settings = get_settings()


class OrganizeRequest(BaseModel):
    drive_folder_link: str
    max_photos: Optional[int] = None
    distance_threshold: float = settings.face_distance_threshold
    verification_threshold: float = settings.face_quality_threshold
    face_detection_model: str = settings.face_detection_backend
