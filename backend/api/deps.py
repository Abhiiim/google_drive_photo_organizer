"""
Dependency injection for API endpoints.

This module provides FastAPI dependencies for:
- Database sessions
- Service instances
- Authentication (future)
- Configuration
"""
from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.logger import get_logger
from database import get_db
from services.cache_service import CacheService
from services.drive_service import DriveService
from services.face_service import FaceService
from services.job_service import JobService
from services.organization_service import OrganizationService
from services.person_service import PersonService
logger = get_logger(__name__)


# Database dependency
def get_database() -> Generator[Session, None, None]:
    """
    Provide a database session for API endpoints.
    
    Yields:
        Database session
    """
    yield from get_db()


# Settings dependency
def get_app_settings() -> Settings:
    """
    Provide application settings.
    
    Returns:
        Settings instance
    """
    return get_settings()


# Service dependencies
def get_face_service() -> FaceService:
    """
    Provide FaceService instance.
    
    Returns:
        FaceService instance
    """
    return FaceService()


def get_drive_service() -> DriveService:
    """
    Provide DriveService instance.
    
    Returns:
        DriveService instance
    """
    return DriveService()


def get_organization_service(
    db: Session = Depends(get_database),
) -> OrganizationService:
    """
    Provide OrganizationService instance with database session.
    
    Args:
        db: Database session
        
    Returns:
        OrganizationService instance
    """
    return OrganizationService(db)


def get_person_service(
    db: Session = Depends(get_database),
) -> PersonService:
    """
    Provide PersonService instance with database session.
    
    Args:
        db: Database session
        
    Returns:
        PersonService instance
    """
    return PersonService(db)


def get_job_service(
    db: Session = Depends(get_database),
) -> JobService:
    """Provide JobService instance with database session."""

    return JobService(db)


def get_cache_service() -> CacheService:
    """
    Provide CacheService instance.
    
    Returns:
        CacheService instance
    """
    return CacheService()


# Future: Authentication dependency
# def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
#     """
#     Get current authenticated user from JWT token.
#     
#     Args:
#         token: JWT access token
#         
#     Returns:
#         Current user
#         
#     Raises:
#         HTTPException: If authentication fails
#     """
#     # TODO: Implement in Phase 3 (Security & Authentication)
#     pass

