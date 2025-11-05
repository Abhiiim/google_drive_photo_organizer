"""
Repositories module for data access layer.
"""
from .base import BaseRepository
from .person_repository import PersonRepository
from .photo_repository import PhotoRepository
from .job_repository import JobRepository

__all__ = [
    "BaseRepository",
    "PersonRepository",
    "PhotoRepository",
    "JobRepository",
]

