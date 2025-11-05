"""
Service layer for person management operations.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from core.logger import get_logger
from repositories.person_repository import PersonRepository
from repositories.photo_repository import PhotoRepository
from models.person import Person


logger = get_logger(__name__)


class PersonService:
    """
    Service for person CRUD operations and management.
    
    This service handles all person-related business logic including
    creation, updates, merging, splitting, and statistics.
    """
    
    def __init__(self, db: Session):
        """
        Initialize PersonService with database session.
        
        Args:
            db: Database session
        """
        self.person_repo = PersonRepository(db)
        self.photo_repo = PhotoRepository(db)
        logger.debug("PersonService initialized")
    
    def create_person(
        self,
        name: str,
        folder_id: Optional[str],
        sample_face_path: Optional[str] = None,
        user_id: Optional[int] = None,
        job_id: Optional[str] = None,
        face_count: int = 0,
        confidence_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Create a new person.
        
        Args:
            name: Person name
            folder_id: Google Drive folder ID for this person
            sample_face_path: Optional path to sample face image
            
        Returns:
            Created person data
        """
        try:
            logger.info(f"Creating person: {name}")
            
            person = self.person_repo.create(
                {
                    "name": name,
                    "folder_id": folder_id,
                    "sample_face_path": sample_face_path,
                    "user_id": user_id,
                    "job_id": job_id,
                    "face_count": face_count,
                    "confidence_score": confidence_score,
                }
            )

            logger.info(f"Person created successfully: ID {person.id}")
            return self._serialize_person(person)
        except Exception as e:
            logger.error(f"Error creating person {name}: {str(e)}")
            raise
    
    def get_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        """
        Get person by ID.
        
        Args:
            person_id: Person ID
            
        Returns:
            Person data or None
        """
        try:
            person = self.person_repo.get(person_id)
            if person:
                return self._serialize_person(person)
            return None
        except Exception as e:
            logger.error(f"Error getting person {person_id}: {str(e)}")
            raise
    
    def get_all_persons(self) -> List[Dict[str, Any]]:
        """
        Get all persons.
        
        Returns:
            List of person data dictionaries
        """
        try:
            logger.info("Getting all persons")
            persons = self.person_repo.get_all()
            
            result = []
            for person in persons:
                stats = self.photo_repo.get_stats_for_person(person.id)

                result.append({
                    **self._serialize_person(person),
                    "photo_count": stats["total"],
                    "photo_stats": stats,
                })
            
            logger.info(f"Found {len(result)} person(s)")
            return result
        except Exception as e:
            logger.error(f"Error getting all persons: {str(e)}")
            raise
    
    def update_person(
        self,
        person_id: int,
        name: Optional[str] = None,
        sample_face_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update person information.
        
        Args:
            person_id: Person ID
            name: Optional new name
            sample_face_path: Optional new sample face path
            
        Returns:
            Updated person data or None
        """
        try:
            logger.info(f"Updating person: {person_id}")
            
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if sample_face_path is not None:
                update_data["sample_face_path"] = sample_face_path
            
            if not update_data:
                logger.warning("No update data provided")
                return self.get_person(person_id)
            
            person = self.person_repo.update(person_id, update_data)
            if person:
                logger.info(f"Person {person_id} updated successfully")
                return self._serialize_person(person)
            return None
        except Exception as e:
            logger.error(f"Error updating person {person_id}: {str(e)}")
            raise
    
    def delete_person(self, person_id: int) -> bool:
        """
        Delete a person.
        
        Args:
            person_id: Person ID
            
        Returns:
            True if deleted successfully
        """
        try:
            logger.info(f"Deleting person: {person_id}")
            success = self.person_repo.delete(person_id)
            if success:
                logger.info(f"Person {person_id} deleted successfully")
            else:
                logger.warning(f"Person {person_id} not found")
            return success
        except Exception as e:
            logger.error(f"Error deleting person {person_id}: {str(e)}")
            raise
    
    def search_persons(self, name_pattern: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search persons by name pattern.
        
        Args:
            name_pattern: Name pattern to search for
            limit: Maximum number of results
            
        Returns:
            List of matching person data
        """
        try:
            logger.info(f"Searching persons with pattern: {name_pattern}")
            persons = self.person_repo.search_by_name(name_pattern, limit)
            
            result = [
                self._serialize_person(person)
                for person in persons
            ]
            
            logger.info(f"Found {len(result)} matching person(s)")
            return result
        except Exception as e:
            logger.error(f"Error searching persons: {str(e)}")
            raise
    
    def get_person_statistics(self, person_id: int) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a person.
        
        Args:
            person_id: Person ID
            
        Returns:
            Statistics dictionary or None
        """
        try:
            person = self.person_repo.get(person_id)
            if not person:
                return None
            
            stats_counts = self.photo_repo.get_stats_for_person(person_id)

            stats = {
                "person": self._serialize_person(person),
                "statistics": {
                    "total_photos": stats_counts["total"],
                    "original_photos": stats_counts["original"],
                    "copied_photos": stats_counts["copies"],
                },
            }
            
            logger.info(f"Statistics for person {person_id}: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics for person {person_id}: {str(e)}")
            raise
    
    def get_person_by_folder_id(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """
        Get person by Google Drive folder ID.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            Person data or None
        """
        try:
            person = self.person_repo.get_by_folder_id(folder_id)
            if person:
                return self._serialize_person(person)
            return None
        except Exception as e:
            logger.error(f"Error getting person by folder ID {folder_id}: {str(e)}")
            raise

    # Internal helpers ------------------------------------------------------------
    def _serialize_person(self, person: Person) -> Dict[str, Any]:
        return {
            "id": person.id,
            "name": person.name,
            "folder_id": person.folder_id,
            "sample_face_path": person.sample_face_path,
            "face_count": person.face_count,
            "confidence_score": person.confidence_score,
            "job_id": person.job_id,
            "user_id": person.user_id,
            "created_at": person.created_at.isoformat() if person.created_at else None,
            "updated_at": person.updated_at.isoformat() if person.updated_at else None,
        }

