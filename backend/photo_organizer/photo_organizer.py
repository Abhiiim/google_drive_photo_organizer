import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Dict, List, Tuple, Optional
import shutil

import numpy as np

from google_drive.google_drive import GoogleDriveClient
from face_detector.face_detector import FaceDetector

class PhotoOrganizer:
    def __init__(self, distance_threshold=0.7, verification_threshold=0.7):
        """
        Initialize the improved photo organizer
        
        Args:
            distance_threshold: Minimum confidence to consider a face match
            verification_threshold: Minimum confidence for cluster verification
        """
        self.drive_client = GoogleDriveClient()
        self.face_detector = FaceDetector(
            tolerance=0.6,
            face_detection_model='hog',  # Use 'cnn' for better accuracy but slower
            num_jitters=1
        )
        self.temp_dir = tempfile.mkdtemp()
        self.distance_threshold = 0.6      # cosine distance threshold (0.4 is good for face recognition)
        self.verification_threshold = verification_threshold

        self.face_database = {}  # List of persons with their face encodings
        self.output_dir = Path(os.path.abspath("organized_photos"))
        self.output_dir.mkdir(exist_ok=True)
        
        # Enhanced logging
        self.processing_stats = {
            'total_photos': 0,
            'photos_processed': 0,
            'faces_detected': 0,
            'clusters_created': 0,
            'photos_with_faces': 0,
            'photos_without_faces': 0,
            'processing_errors': 0
        }
    
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
            progress_callback("Extracting folder ID...")
            
            # Check folder permissions
            progress_callback("Checking folder permissions...")
            permissions = self.drive_client.check_folder_permissions(folder_id)
            
            if not permissions['can_create_folders']:
                raise Exception(f"Insufficient permissions! You need 'Editor' access to folder '{permissions['folder_name']}' to create person folders. Current access is read-only.")
            
            progress_callback(f"✅ Access confirmed for folder: {permissions['folder_name']}")
            
            # Get all images
            progress_callback("Fetching image list...")
            images = self.drive_client.list_images(folder_id)
            
            total_photos = len(images)
            if max_photos:
                images = images[:max_photos]
                total_photos = len(images)
            
            self.processing_stats['total_photos'] = total_photos
            progress_callback(f"Found {total_photos} images", total_photos=total_photos)
            
            if total_photos == 0:
                progress_callback("No images found in folder")
                return
            
            self._organize_photos(images, progress_callback)
            
        except Exception as e:
            progress_callback(f"❌ Error: {str(e)}")
            raise
    
    def _organize_photos(self, images: List[Dict], progress_callback: Callable):
        """
        Organize photos into person folders with verification and manual review
        
        Args:
            image_data: List of (photo_name, photo_id, face_encodings, face_metadata)
            progress_callback: Function to report progress
        """
        for i, image in enumerate(images):
            progress_callback(f"Processing image {i+1}/{len(images)}: {image['name']}", processed=i)
            
            temp_path = os.path.join(self.temp_dir, f"temp_{i}_{image['name']}")
            try:
                # Download image
                self.drive_client.download_file(image['id'], temp_path)
                
                # Detect faces
                faces, embeddings = self.face_detector.detect_and_extract_faces(temp_path)

                if not embeddings:
                    # No faces found, move to 'no_faces' folder
                    no_faces_dir = self.output_dir / "no_faces"
                    no_faces_dir.mkdir(exist_ok=True)
                    # Use Path for temp_path to get filename
                    temp_path_obj = Path(temp_path)
                    dest_path = no_faces_dir / temp_path_obj.name
                    shutil.copy2(temp_path, dest_path)
                    progress_callback(f"  ➡️ No faces found: moved to {dest_path}", processed=i+1)
                    continue

                # Process each face in the image
                for embedding_data in embeddings:
                    embedding = embedding_data['embedding']
                    
                    # Try to match with existing persons
                    # person_id = self._find_matching_person(embedding)
                    person_id, avg_distance = self.match_average_top_k(embedding)
                    
                    if person_id is None:
                        # New person found
                        person_id = len(self.face_database)
                        self.face_database[person_id] = {}
                        self.face_database[person_id]['embeddings'] = [embedding]
                        self.face_database[person_id]['photos'] = []
                    else:
                        # Add embedding to existing person
                        self.face_database[person_id]['embeddings'].append(embedding)

                    # Add photo to person's collection  
                    self.face_database[person_id]['photos'].append({
                        'name': image['name'],
                        'id': image['id'],
                        'temp_path': temp_path
                    })

            except Exception as e:
                print(f"Error processing {image['name']}: {e}")
                self.processing_stats['processing_errors'] += 1
                progress_callback(f"  ❌ Error processing {image['name']}: {str(e)}", processed=i+1)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # Copy photos to person folders
        self._create_person_folders()
        
        # Save metadata
        self._save_metadata()
        
        print(f"\nOrganization complete!")
        print(f"Found {len(self.face_database)} unique persons")
        print(f"Results saved to: {self.output_dir}")
    
    def _create_person_folders(self):
        """Create folders for each person and copy their photos"""
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
                    temp_path = os.path.join(self.temp_dir, f"download_{photo_name}")
                    try:
                        self.drive_client.download_file(photo_info['id'], temp_path)
                        
                        dest_path = person_dir / photo_name
                        # Handle duplicate filenames
                        counter = 1
                        while dest_path.exists():
                            name_stem = Path(photo_name).stem
                            name_suffix = Path(photo_name).suffix
                            dest_path = person_dir / f"{name_stem}_{counter}{name_suffix}"
                            counter += 1
                        
                        shutil.copy2(temp_path, dest_path)
                        os.remove(temp_path)  # Clean up temp file
                    except Exception as e:
                        print(f"Error copying photo {photo_name}: {e}")
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
            
            print(f"Person {person_id + 1}: {len(unique_photos)} photos")
    
    def _save_metadata(self):
        """Save organization metadata to JSON"""
        metadata = {
            'total_persons': len(self.face_database),
            'distance_threshold': self.distance_threshold,
            'persons': []
        }
        
        for person_id, person_data in self.face_database.items():
            # Extract unique photo names
            unique_photo_names = set()
            for photo_info in person_data['photos']:
                if isinstance(photo_info, dict):
                    unique_photo_names.add(photo_info['name'])
                else:
                    # Fallback for string paths
                    unique_photo_names.add(str(photo_info))
            
            metadata['persons'].append({
                'person_id': person_id + 1,
                'photo_count': len(unique_photo_names),
                'photos': list(unique_photo_names)
            })
        
        with open(self.output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)

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
            print(f"Best match: Person {best_match_id}, Distance: {best_avg_distance:.3f}")
        else:
            print(f"No match found, Best distance: {best_avg_distance:.3f}")
        
        if best_avg_distance < self.distance_threshold:
            return best_match_id, best_avg_distance
        
        return None, None

