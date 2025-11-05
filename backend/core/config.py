"""Application configuration management using Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    project_name: str = Field(
        default="Improved Google Drive Face Organizer",
        alias="PROJECT_NAME",
    )
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    version: str = Field(default="2.0.0", alias="VERSION")
    cors_allow_origins: List[str] = Field(
        default=["*"],
        alias="CORS_ALLOW_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_backup_count: int = Field(default=14, alias="LOG_BACKUP_COUNT", ge=1)
    logs_dir: Path = Field(default=Path("./logs"), alias="LOGS_DIR")
    app_log_filename: str = Field(default="app.log", alias="APP_LOG_FILENAME")
    error_log_filename: str = Field(default="error.log", alias="ERROR_LOG_FILENAME")
    access_log_filename: str = Field(default="access.log", alias="ACCESS_LOG_FILENAME")
    logging_config_path: Optional[Path] = Field(
        default=None,
        alias="LOGGING_CONFIG_PATH",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./face_organizer.db",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")

    # Google Drive
    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(
        default=None,
        alias="GOOGLE_CLIENT_SECRET",
    )
    google_redirect_uri: Optional[str] = Field(
        default=None,
        alias="GOOGLE_REDIRECT_URI",
    )
    google_scopes: List[str] = Field(
        default=["https://www.googleapis.com/auth/drive"],
        alias="GOOGLE_SCOPES",
    )

    # Face detection
    face_distance_threshold: float = Field(
        default=0.5,
        alias="FACE_DISTANCE_THRESHOLD",
        ge=0.0,
        le=1.0,
    )
    face_min_size: int = Field(default=50, alias="FACE_MIN_SIZE", ge=1)
    face_quality_threshold: float = Field(
        default=0.3,
        alias="FACE_QUALITY_THRESHOLD",
        ge=0.0,
        le=1.0,
    )
    face_detection_backend: str = Field(
        default="retinaface",
        alias="FACE_DETECTION_BACKEND",
    )

    # Processing
    max_workers: int = Field(default=4, alias="MAX_WORKERS", ge=1)
    max_photos_per_job: int = Field(default=1000, alias="MAX_PHOTOS_PER_JOB", ge=1)
    temp_dir: Path = Field(default=Path("./tmp"), alias="TEMP_DIR")
    organized_photos_dir: Path = Field(
        default=Path("./organized_photos"),
        alias="ORGANIZED_PHOTOS_DIR",
    )

    # Redis / caching (placeholders for future phases)
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    redis_db: int = Field(default=0, alias="REDIS_DB", ge=0)
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL", ge=0)

    @field_validator("google_scopes", "cors_allow_origins", mode="before")
    @classmethod
    def split_comma_separated(
        cls,
        value: Optional[Union[str, List[str]]],
        info: ValidationInfo,
    ) -> List[str]:
        """Allow comma-separated entries in environment variables."""

        if value is None:
            if info.field_name == "google_scopes":
                return ["https://www.googleapis.com/auth/drive"]
            if info.field_name == "cors_allow_origins":
                return ["*"]
            return []

        if isinstance(value, list):
            return [item for item in (v.strip() for v in value) if item]

        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]

        raise ValueError(f"Invalid value for {info.field_name}")

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: Optional[Union[str, int]]) -> str:
        """Normalize log level values to uppercase strings."""

        if value is None:
            return "INFO"
        return str(value).upper()

    @field_validator("temp_dir", "organized_photos_dir", "logs_dir", mode="after")
    @classmethod
    def resolve_directories(cls, value: Path) -> Path:
        """Ensure directory paths are absolute and expanded."""

        return value.expanduser().resolve()

    @field_validator("logging_config_path", mode="after")
    @classmethod
    def resolve_optional_path(cls, value: Optional[Path]) -> Optional[Path]:
        """Resolve optional configuration paths."""

        if value is None:
            return None
        return value.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    settings = Settings()
    return settings


