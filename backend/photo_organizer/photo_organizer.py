import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np

from core.config import get_settings
from core.logger import get_logger
from google_drive.google_drive import GoogleDriveClient
from face_detector.face_detector import FaceDetector


settings = get_settings()
logger = get_logger(__name__)

class PhotoOrganizer:
    def __init__(self, distance_threshold: Optional[float] = None, verification_threshold: Optional[float] = None):
        """
        Initialize the improved photo organizer
        
        Args:
            distance_threshold: Minimum confidence to consider a face match
            verification_threshold: Minimum confidence for cluster verification
        """
        try:
            self.drive_client = GoogleDriveClient()
            self.face_detector = FaceDetector(
                min_face_size=settings.face_min_size,
                quality_threshold=settings.face_quality_threshold,
            )

            # Ensure base directories exist
            settings.temp_dir.mkdir(parents=True, exist_ok=True)
            settings.organized_photos_dir.mkdir(parents=True, exist_ok=True)

            self.temp_dir = Path(
                tempfile.mkdtemp(dir=str(settings.temp_dir))
            )
            self.distance_threshold = (
                distance_threshold
                if distance_threshold is not None
                else settings.face_distance_threshold
            )
            self.verification_threshold = (
                verification_threshold
                if verification_threshold is not None
                else settings.face_quality_threshold
            )

            self.face_database = {}  # List of persons with their face encodings
            self.output_dir = settings.organized_photos_dir
            
            # Enhanced logging
            self.processing_stats = {
                'total_photos': 0,
                'photos_processed': 0,
                'faces_detected': 0,
                'clusters_created': 0,
                'photos_with_faces': 0,
                'photos_without_faces': 0,
                'photos_with_single_face': 0,
                'photos_with_multiple_faces': 0,
                'processing_errors': 0
            }
        except Exception as e:
            # Clean up if initialization fails
            temp_dir = getattr(self, "temp_dir", None)
            if temp_dir:
                shutil.rmtree(Path(temp_dir), ignore_errors=True)
            raise Exception(f"Failed to initialize PhotoOrganizer: {str(e)}")
    
    def cleanup(self):
        """Clean up temporary directory and resources"""
        try:
            temp_dir = getattr(self, "temp_dir", None)
            if temp_dir:
                temp_path = Path(temp_dir)
                if temp_path.exists():
                    logger.debug(
                        "organizer.cleanup_directory",
                        temp_dir=str(temp_path),
                    )
                    shutil.rmtree(temp_path, ignore_errors=True)
        except Exception as e:
            logger.warning(
                "organizer.cleanup_failed",
                error=str(e),
                temp_dir=str(temp_dir) if temp_dir else None,
            )
    
    async def organize_folder(self, folder_link: str, progress_callback: Callable, max_photos: Optional[int] = None):
        """
        Main organization logic with improved face detection and verification
        
        Args:
            folder_link: Google Drive folder URL
            progress_callback: Function to report progress
            max_photos: Maximum number of photos to process (None for all)
        """
        try:
            # Initialize stats
            self.processing_stats = {key: 0 for key in self.processing_stats.keys()}
            
            # Extract folder ID
            folder_id = self.drive_client.extract_folder_id(folder_link)
            logger.info("organizer.extract_folder_id_start", folder_link=folder_link)
            progress_callback("Extracting folder ID...")
            
            # Check folder permissions
            progress_callback("Checking folder permissions...")
            logger.info("organizer.check_permissions_start", folder_id=folder_id)
            permissions = self.drive_client.check_folder_permissions(folder_id)
            
            if not permissions['can_create_folders']:
                raise Exception(f"Insufficient permissions! You need 'Editor' access to folder '{permissions['folder_name']}' to create person folders. Current access is read-only.")
            
            progress_callback(f"✅ Access confirmed for folder: {permissions['folder_name']}")
            logger.info(
                "organizer.permissions_confirmed",
                folder_name=permissions["folder_name"],
                can_create_folders=permissions["can_create_folders"],
            )
            
            # Get all images
            progress_callback("Fetching image list...")
            logger.info("organizer.fetch_images_start", folder_id=folder_id)
            images = self.drive_client.list_images(folder_id)
            
            total_photos = len(images)
            if max_photos:
                images = images[:max_photos]
                total_photos = len(images)
            
            self.processing_stats['total_photos'] = total_photos
            progress_callback(f"Found {total_photos} images", total_photos=total_photos)
            logger.info(
                "organizer.images_discovered",
                total_photos=total_photos,
                folder_id=folder_id,
            )
            
            if total_photos == 0:
                progress_callback("No images found in folder")
                return
            
            self._organize_photos(images, progress_callback)
            
        except Exception as e:
            progress_callback(f"❌ Error: {str(e)}")
            logger.exception("organizer.organize_folder_failed", error=str(e))
            raise
        finally:
            # Always cleanup temporary files
            self.cleanup()
    
    def _organize_photos(self, images: List[Dict], progress_callback: Callable):
        """
        Organize photos into person folders with verification and manual review
        
        Args:
            image_data: List of (photo_name, photo_id, face_encodings, face_metadata)
            progress_callback: Function to report progress
        """
        for i, image in enumerate(images):
            progress_callback(f"Processing image {i+1}/{len(images)}: {image['name']}", processed=i)
            logger.debug(
                "organizer.process_image_start",
                image_name=image["name"],
                image_index=i,
                total=len(images),
            )
            
            temp_path = self.temp_dir / f"temp_{i}_{image['name']}"
            try:
                # Download image
                self.drive_client.download_file(image['id'], str(temp_path))
                
                # Detect faces
                faces, embeddings = self.face_detector.detect_and_extract_faces(str(temp_path))

                if not embeddings:
                    # No faces found, move to 'no_faces' folder
                    no_faces_dir = self.output_dir / "no_faces"
                    no_faces_dir.mkdir(exist_ok=True)
                    # Use Path for temp_path to get filename
                    dest_path = no_faces_dir / temp_path.name
                    shutil.copy2(temp_path, dest_path)
                    progress_callback(f"  ➡️ No faces found: moved to {dest_path}", processed=i+1)
                    logger.info(
                        "organizer.no_faces_detected",
                        image_name=image["name"],
                        destination=str(dest_path),
                    )
                    self.processing_stats['photos_without_faces'] += 1
                    continue

                # Track persons found in this image for multi-face handling
                persons_in_image = []
                
                # Process each face in the image
                for face_idx, embedding_data in enumerate(embeddings):
                    embedding = embedding_data['embedding']
                    
                    # Try to match with existing persons
                    person_id, avg_distance = self.match_average_top_k(embedding)
                    
                    if person_id is None:
                        # New person found
                        person_id = len(self.face_database)
                        self.face_database[person_id] = {
                            'embeddings': [embedding],
                            'photos': []
                        }
                        logger.info(
                            "organizer.new_person_detected",
                            person_id=person_id + 1,
                            image_name=image["name"],
                        )
                    else:
                        # Add embedding to existing person
                        self.face_database[person_id]['embeddings'].append(embedding)
                        logger.debug(
                            "organizer.person_matched",
                            person_id=person_id + 1,
                            image_name=image["name"],
                            average_distance=avg_distance,
                        )

                    # Track this person for multi-face handling
                    if person_id not in persons_in_image:
                        persons_in_image.append(person_id)

                # Add photo to all persons found in this image
                for person_id in persons_in_image:
                    self.face_database[person_id]['photos'].append({
                        'name': image['name'],
                        'id': image['id'],
                        'temp_path': temp_path,
                        'is_multi_face': len(persons_in_image) > 1,
                        'persons_in_photo': persons_in_image.copy()
                    })

                # Update statistics
                self.processing_stats['faces_detected'] += len(embeddings)
                self.processing_stats['photos_with_faces'] += 1
                
                if len(persons_in_image) > 1:
                    self.processing_stats['photos_with_multiple_faces'] += 1
                    progress_callback(f"  👥 Multiple faces found: {len(persons_in_image)} persons in {image['name']}", processed=i+1)
                    logger.info(
                        "organizer.multiple_faces_detected",
                        image_name=image["name"],
                        person_count=len(persons_in_image),
                    )
                else:
                    self.processing_stats['photos_with_single_face'] += 1
                    progress_callback(f"  👤 Single face found in {image['name']}", processed=i+1)
                    logger.debug(
                        "organizer.single_face_detected",
                        image_name=image["name"],
                    )

            except Exception as e:
                logger.exception(
                    "organizer.process_image_failed",
                    image_name=image.get("name"),
                    error=str(e),
                )
                self.processing_stats['processing_errors'] += 1
                progress_callback(f"  ❌ Error processing {image['name']}: {str(e)}", processed=i+1)
            finally:
                if temp_path.exists():
                    temp_path.unlink()

        # Copy photos to person folders
        self._create_person_folders()
        
        # Save metadata
        self._save_metadata()
        
        logger.info(
            "organizer.completed",
            total_persons=len(self.face_database),
            photos_with_faces=self.processing_stats['photos_with_faces'],
            photos_without_faces=self.processing_stats['photos_without_faces'],
            faces_detected=self.processing_stats['faces_detected'],
            output_directory=str(self.output_dir),
        )
    
    def _create_person_folders(self):
        """Create folders for each person and copy their photos, handling multi-face photos properly"""
        
        # Track which photos have been processed as originals to avoid duplicates
        processed_originals = set()
        
        for person_id, person_data in self.face_database.items():
            person_dir = self.output_dir / f"person_{person_id + 1}"
            person_dir.mkdir(exist_ok=True)
            
            # Get unique photos for this person (avoid duplicates by name)
            unique_photos = {}
            for photo_info in person_data['photos']:
                if isinstance(photo_info, dict):
                    photo_name = photo_info['name']
                    if photo_name not in unique_photos:
                        unique_photos[photo_name] = photo_info
                else:
                    # Fallback for string paths (shouldn't happen with new code)
                    photo_path = str(photo_info)
                    photo_name = Path(photo_path).name
                    if photo_name not in unique_photos:
                        unique_photos[photo_name] = {'name': photo_name, 'path': photo_path}
            
            # Download and copy photos to person's folder
            for photo_name, photo_info in unique_photos.items():
                if 'id' in photo_info:
                    # Download from Google Drive
                    temp_path = self.temp_dir / f"download_{photo_name}"
                    try:
                        self.drive_client.download_file(photo_info['id'], str(temp_path))
                        
                        dest_path = person_dir / photo_name
                        
                        # Handle multi-face photos
                        is_multi_face = photo_info.get('is_multi_face', False)
                        persons_in_photo = photo_info.get('persons_in_photo', [person_id])
                        
                        if is_multi_face:
                            # For multi-face photos, create original in first person's folder
                            # and shortcuts/copies in other person folders
                            if photo_name not in processed_originals:
                                # This is the first person folder for this multi-face photo
                                # Handle duplicate filenames
                                counter = 1
                                while dest_path.exists():
                                    name_stem = Path(photo_name).stem
                                    name_suffix = Path(photo_name).suffix
                                    dest_path = person_dir / f"{name_stem}_{counter}{name_suffix}"
                                    counter += 1
                                
                                shutil.copy2(temp_path, dest_path)
                                processed_originals.add(photo_name)
                                logger.debug(
                                    "organizer.multi_face_original_saved",
                                    person_id=person_id + 1,
                                    photo_name=photo_name,
                                    destination=str(dest_path),
                                )
                            else:
                                # This is a subsequent person folder for this multi-face photo
                                # Create a copy with a suffix to indicate it's a multi-face photo
                                name_stem = Path(photo_name).stem
                                name_suffix = Path(photo_name).suffix
                                shortcut_name = f"{name_stem}_copy{name_suffix}"
                                dest_path = person_dir / shortcut_name
                                
                                # Handle duplicate filenames
                                counter = 1
                                while dest_path.exists():
                                    dest_path = person_dir / f"{name_stem}_copy_{counter}{name_suffix}"
                                    counter += 1
                                
                                shutil.copy2(temp_path, dest_path)
                                logger.debug(
                                    "organizer.multi_face_copy_saved",
                                    person_id=person_id + 1,
                                    photo_name=photo_name,
                                    destination=str(dest_path),
                                )
                        else:
                            # Single face photo - normal handling
                            # Handle duplicate filenames
                            counter = 1
                            while dest_path.exists():
                                name_stem = Path(photo_name).stem
                                name_suffix = Path(photo_name).suffix
                                dest_path = person_dir / f"{name_stem}_{counter}{name_suffix}"
                                counter += 1
                            
                            shutil.copy2(temp_path, dest_path)
                            logger.debug(
                                "organizer.single_face_saved",
                                person_id=person_id + 1,
                                photo_name=photo_name,
                                destination=str(dest_path),
                            )
                        
                    except Exception as e:
                        logger.exception(
                            "organizer.copy_photo_failed",
                            photo_name=photo_name,
                            person_id=person_id + 1,
                            error=str(e),
                        )
                        self.processing_stats['processing_errors'] += 1
                    finally:
                        # Always try to clean up temp file
                        if temp_path.exists():
                            try:
                                temp_path.unlink()
                            except Exception as cleanup_error:
                                logger.warning(
                                    "organizer.temp_cleanup_failed",
                                    temp_file=str(temp_path),
                                    error=str(cleanup_error),
                                )
                elif 'path' in photo_info:
                    # Copy from local path (fallback)
                    photo_file = Path(photo_info['path'])
                    dest_path = person_dir / photo_file.name
                    
                    # Handle duplicate filenames
                    counter = 1
                    while dest_path.exists():
                        dest_path = person_dir / f"{photo_file.stem}_{counter}{photo_file.suffix}"
                        counter += 1
                    
                    shutil.copy2(photo_info['path'], dest_path)
            
            logger.info(
                "organizer.person_summary",
                person_id=person_id + 1,
                total_photos=len(unique_photos),
            )
    
    def _save_metadata(self):
        """Save organization metadata to JSON"""
        try:
            metadata = {
                'total_persons': len(self.face_database),
                'distance_threshold': self.distance_threshold,
                'processing_stats': self.processing_stats,
                'persons': []
            }
            
            for person_id, person_data in self.face_database.items():
                # Extract unique photo names and categorize them
                unique_photos = {}
                single_face_photos = []
                multi_face_photos = []
                
                for photo_info in person_data['photos']:
                    if isinstance(photo_info, dict):
                        photo_name = photo_info['name']
                        if photo_name not in unique_photos:
                            unique_photos[photo_name] = photo_info
                            
                            if photo_info.get('is_multi_face', False):
                                multi_face_photos.append({
                                    'name': photo_name,
                                    'persons_in_photo': photo_info.get('persons_in_photo', [])
                                })
                            else:
                                single_face_photos.append(photo_name)
                    else:
                        # Fallback for string paths
                        photo_name = str(photo_info)
                        if photo_name not in unique_photos:
                            unique_photos[photo_name] = {'name': photo_name}
                            single_face_photos.append(photo_name)
                
                metadata['persons'].append({
                    'person_id': person_id + 1,
                    'total_photos': len(unique_photos),
                    'single_face_photos': single_face_photos,
                    'multi_face_photos': multi_face_photos,
                    'single_face_count': len(single_face_photos),
                    'multi_face_count': len(multi_face_photos)
                })
            
            metadata_path = self.output_dir / 'metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(
                "organizer.metadata_saved",
                metadata_path=str(metadata_path),
            )
            
        except Exception as e:
            logger.exception("organizer.metadata_save_failed", error=str(e))
            # Don't raise - metadata saving failure shouldn't stop the whole process

    def match_average_top_k(self, embedding, k=3):
        """
        Average cosine distance of top K closest matches per person
        ✅✅ BEST - Most robust to outliers and variations
        Uses cosine distance which is ideal for FaceNet embeddings
        """
        face_database = self.face_database
        best_match_id = None
        best_avg_distance = float('inf')
        
        embedding_array = np.array(embedding)
        # Normalize the embedding for cosine distance calculation
        embedding_norm = embedding_array / np.linalg.norm(embedding_array)
        
        for person_id, person_data in face_database.items():
            if not person_data['embeddings']:
                continue
            
            # Calculate cosine distances for this person
            distances = []
            for known_emb in person_data['embeddings']:
                known_emb_array = np.array(known_emb)
                known_emb_norm = known_emb_array / np.linalg.norm(known_emb_array)
                
                # Cosine distance = 1 - cosine similarity
                cosine_similarity = np.dot(embedding_norm, known_emb_norm)
                cosine_distance = 1 - cosine_similarity
                distances.append(cosine_distance)
            
            # Take average of top K closest
            distances_sorted = sorted(distances)
            top_k_distances = distances_sorted[:min(k, len(distances_sorted))]
            avg_distance = np.mean(top_k_distances)
            
            if avg_distance < best_avg_distance:
                best_avg_distance = avg_distance
                best_match_id = person_id

            # breakpoint()
        
        # Debug info (you can remove this later)
        if best_match_id is not None:
            logger.debug(
                "organizer.match_result",
                person_id=best_match_id + 1,
                average_distance=best_avg_distance,
            )
        else:
            logger.debug(
                "organizer.match_not_found",
                best_distance=best_avg_distance,
            )
        
        if best_avg_distance < self.distance_threshold:
            return best_match_id, best_avg_distance
        
        return None, None

