"""Pydantic schemas for the photo organizer API with comprehensive validation."""

import re
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

from pydantic import BaseModel, Field, field_validator, ValidationInfo

from core.config import get_settings
from core.exceptions import ValidationError


settings = get_settings()


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict = Field(default_factory=dict, description="Additional error context")
    timestamp: str = Field(..., description="ISO 8601 timestamp when error occurred")
    path: Optional[str] = Field(None, description="API endpoint that generated error")


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    status: str
    message: str
    phase: str
    progress_percentage: int
    total_photos: int
    processed: int
    faces_detected: int
    persons_found: int
    folders_created: int
    processing_stats: dict
    multi_face_summary: dict
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class OrganizeRequest(BaseModel):
    """Request model for photo organization with comprehensive validation."""

    drive_folder_link: str = Field(
        ...,
        description="Google Drive folder link or folder ID",
        min_length=1,
        max_length=1000,
    )

    max_photos: Optional[int] = Field(
        None,
        description="Maximum number of photos to process",
        ge=1,
        le=settings.max_photos_per_job,
    )

    distance_threshold: float = Field(
        default=settings.face_distance_threshold,
        description="Face distance threshold for clustering (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    verification_threshold: float = Field(
        default=settings.face_quality_threshold,
        description="Face quality threshold for detection (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    face_detection_model: str = Field(
        default=settings.face_detection_backend,
        description="Face detection backend to use",
    )

    @field_validator("drive_folder_link", mode="before")
    @classmethod
    def validate_drive_folder_link(cls, value: str) -> str:
        """Validate and extract folder ID from Google Drive link."""
        if not value or not isinstance(value, str):
            raise ValidationError(
                message="Drive folder link is required",
                details={"field": "drive_folder_link"}
            )

        # Clean the input
        value = value.strip()

        # Check if it's already a folder ID (simple alphanumeric check)
        if re.match(r'^[a-zA-Z0-9_-]+$', value):
            return value

        # Try to extract folder ID from Google Drive URL
        try:
            parsed_url = urlparse(value)
            if 'drive.google.com' not in parsed_url.netloc:
                raise ValidationError(
                    message="Invalid Google Drive URL. Must be a drive.google.com link",
                    details={"field": "drive_folder_link", "provided_url": value}
                )

            # Handle different Google Drive URL formats
            path_parts = parsed_url.path.strip('/').split('/')

            # Format: /drive/folders/{folder_id}
            if 'folders' in path_parts:
                folder_index = path_parts.index('folders')
                if folder_index + 1 < len(path_parts):
                    folder_id = path_parts[folder_index + 1]
                    if folder_id:
                        return folder_id

            # Format: /open?id={folder_id}
            query_params = parse_qs(parsed_url.query)
            if 'id' in query_params and query_params['id']:
                return query_params['id'][0]

            # Format: /drive/u/0/folders/{folder_id}
            if len(path_parts) >= 4 and path_parts[-2] == 'folders':
                return path_parts[-1]

            raise ValidationError(
                message="Could not extract folder ID from Google Drive URL",
                details={
                    "field": "drive_folder_link",
                    "provided_url": value,
                    "supported_formats": [
                        "https://drive.google.com/drive/folders/{folder_id}",
                        "https://drive.google.com/open?id={folder_id}",
                        "https://drive.google.com/drive/u/0/folders/{folder_id}"
                    ]
                }
            )

        except Exception as e:
            raise ValidationError(
                message="Invalid Google Drive folder link format",
                details={
                    "field": "drive_folder_link",
                    "provided_url": value,
                    "error": str(e)
                }
            )

    @field_validator("face_detection_model", mode="before")
    @classmethod
    def validate_face_detection_model(cls, value: str) -> str:
        """Validate face detection model choice."""
        valid_models = ["retinaface", "mtcnn", "opencv", "ssd", "dlib"]
        if value not in valid_models:
            raise ValidationError(
                message=f"Invalid face detection model: {value}",
                details={
                    "field": "face_detection_model",
                    "provided_value": value,
                    "valid_options": valid_models
                }
            )
        return value

    @field_validator("max_photos", mode="before")
    @classmethod
    def validate_max_photos(cls, value: Optional[int], info: ValidationInfo) -> Optional[int]:
        """Validate max_photos against system limits."""
        if value is not None and value > settings.max_photos_per_job:
            raise ValidationError(
                message=f"max_photos ({value}) exceeds system limit ({settings.max_photos_per_job})",
                details={
                    "field": "max_photos",
                    "provided_value": value,
                    "max_allowed": settings.max_photos_per_job
                }
            )
        return value


class JobCreateResponse(BaseModel):
    """Response model for job creation."""

    job_id: str
    status: str = "pending"
    message: str = "Organization job created successfully"
