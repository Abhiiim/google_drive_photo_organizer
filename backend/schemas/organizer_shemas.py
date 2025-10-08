from typing import Optional

from pydantic import BaseModel


class OrganizeRequest(BaseModel):
    drive_folder_link: str
    max_photos: Optional[int] = None
    distance_threshold: float = 0.7
    verification_threshold: float = 0.7
    face_detection_model: str = 'hog'  # 'hog' (faster) or 'cnn' (more accurate)
