"""
Service layer for photo organization workflow.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.logger import get_logger
from services.face_service import FaceService
from services.drive_service import DriveService
from services.job_service import JobService
from services.person_service import PersonService
from repositories.photo_repository import PhotoRepository


logger = get_logger(__name__)


class OrganizationService:
    """
    Service for photo organization workflow.
    
    This service orchestrates the complete photo organization process:
    - Downloading photos from Google Drive
    - Detecting faces in photos
    - Clustering faces by similarity
    - Creating person folders
    - Organizing photos into folders
    """
    
    def __init__(self, db: Session):
        """
        Initialize OrganizationService.
        
        Args:
            db: Database session
        """
        self.db = db
        self.face_service = FaceService()
        self.drive_service = DriveService()
        self.person_service = PersonService(db)
        self.job_service = JobService(db)
        self.photo_repo = PhotoRepository(db)
        logger.debug("OrganizationService initialized")
    
    def start_organization_job(
        self,
        folder_id: str,
        *,
        folder_name: Optional[str] = None,
        total_photos: int = 0,
        user_id: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a photo organization job.
        
        Args:
            folder_id: Google Drive folder ID to organize
            config: Optional configuration for the job
            
        Returns:
            Job ID
            
        Note:
            This method creates a job and delegates the actual processing
            to Celery tasks. The actual implementation should use
            tasks.photo_tasks.organize_photos_task
        """
        try:
            logger.info(
                "Starting organization job",
                folder_id=folder_id,
                folder_name=folder_name,
                total_photos=total_photos,
            )

            job = self.job_service.create_job(
                folder_id=folder_id,
                folder_name=folder_name,
                total_photos=total_photos,
                user_id=user_id,
            )

            logger.info("Organization job persisted", job_id=job.id)
            return job.id
        except Exception as e:
            logger.error(f"Error starting organization job: {str(e)}")
            raise
    
    def process_photo(
        self,
        photo_path: str,
        photo_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single photo for face detection.
        
        Args:
            photo_path: Local path to the photo
            photo_metadata: Photo metadata from Google Drive
            
        Returns:
            Processing result with detected faces
        """
        try:
            logger.info(f"Processing photo: {photo_path}")
            
            # Detect faces
            faces = self.face_service.detect_faces_in_image(photo_path)
            
            result = {
                "photo_name": photo_metadata.get("name"),
                "photo_id": photo_metadata.get("id"),
                "face_count": len(faces),
                "faces": faces,
                "has_faces": len(faces) > 0,
                "is_multi_face": len(faces) > 1
            }
            
            logger.info(
                f"Photo processed: {len(faces)} face(s) detected in {photo_metadata.get('name')}"
            )
            return result
        except Exception as e:
            logger.error(f"Error processing photo {photo_path}: {str(e)}")
            raise
    
    def cluster_and_organize(
        self,
        photos_data: List[Dict[str, Any]],
        output_folder_id: str,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Cluster faces and organize photos into person folders.
        
        Args:
            photos_data: List of processed photo data with face embeddings
            output_folder_id: Google Drive folder ID for output
            threshold: Distance threshold for face clustering
            
        Returns:
            Organization result with statistics
        """
        try:
            logger.info(f"Clustering and organizing {len(photos_data)} photos")
            
            # Collect all face embeddings
            all_embeddings = []
            embedding_to_photo = []
            
            for photo_data in photos_data:
                for face_idx, face in enumerate(photo_data.get("faces", [])):
                    if "embedding" in face:
                        all_embeddings.append(face["embedding"])
                        embedding_to_photo.append({
                            "photo_data": photo_data,
                            "face_idx": face_idx,
                            "face": face
                        })
            
            if not all_embeddings:
                logger.warning("No face embeddings found for clustering")
                return {
                    "status": "no_faces",
                    "message": "No faces detected in photos",
                    "persons_created": 0,
                    "photos_organized": 0
                }
            
            # Cluster faces
            cluster_labels = self.face_service.cluster_faces(all_embeddings, threshold)
            
            # Organize by clusters (persons)
            clusters = {}
            for i, label in enumerate(cluster_labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(embedding_to_photo[i])
            
            logger.info(f"Created {len(clusters)} person cluster(s)")
            
            # Create person folders and organize photos
            persons_created = 0
            photos_organized = 0
            
            for cluster_id, cluster_items in clusters.items():
                # Create person folder
                person_name = f"Person_{cluster_id + 1}"
                folder = self.drive_service.create_folder(person_name, output_folder_id)
                
                # Create person record in database
                person = self.person_service.create_person(
                    name=person_name,
                    folder_id=folder["id"],
                    sample_face_path=cluster_items[0]["photo_data"].get("photo_name"),
                    face_count=len(cluster_items),
                )
                
                persons_created += 1
                
                # Move/copy photos to person folder
                for item in cluster_items:
                    photo_data = item["photo_data"]
                    try:
                        self.drive_service.copy_file(
                            photo_data["photo_id"],
                            folder["id"]
                        )
                        photos_organized += 1
                    except Exception as e:
                        logger.error(f"Error copying photo: {str(e)}")
            
            result = {
                "status": "success",
                "persons_created": persons_created,
                "photos_organized": photos_organized,
                "total_faces": len(all_embeddings),
                "clusters": len(clusters)
            }
            
            logger.info(f"Organization complete: {result}")
            return result
        except Exception as e:
            logger.error(f"Error clustering and organizing: {str(e)}")
            raise
    
    def get_organization_statistics(self) -> Dict[str, Any]:
        """
        Get overall organization statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            persons = self.person_service.get_all_persons()
            total_photos = sum(p.get("photo_count", 0) for p in persons)
            
            stats = {
                "total_persons": len(persons),
                "total_photos": total_photos,
                "persons": persons
            }
            
            logger.info(f"Organization statistics: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting organization statistics: {str(e)}")
            raise
    
    def validate_folder(self, folder_id: str) -> Dict[str, Any]:
        """
        Validate a Google Drive folder for organization.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            Validation result
        """
        try:
            logger.info(f"Validating folder: {folder_id}")
            
            # Check folder accessibility
            folder_name = self.drive_service.get_folder_name(folder_id)
            
            # List photos in folder
            photos = self.drive_service.list_photos_in_folder(folder_id)
            
            validation = {
                "valid": True,
                "folder_id": folder_id,
                "folder_name": folder_name,
                "photo_count": len(photos),
                "can_access": True,
                "errors": []
            }
            
            if len(photos) == 0:
                validation["errors"].append("No photos found in folder")
            
            logger.info(f"Folder validation: {validation}")
            return validation
        except Exception as e:
            logger.error(f"Error validating folder {folder_id}: {str(e)}")
            return {
                "valid": False,
                "folder_id": folder_id,
                "can_access": False,
                "errors": [str(e)]
            }

