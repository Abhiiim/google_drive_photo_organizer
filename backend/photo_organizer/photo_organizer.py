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
            num_jitters=1,
            min_face_size=60,  # More lenient - captures visible faces without being too strict
            quality_threshold=0.35  # Balanced threshold to catch most visible faces
        )
        self.temp_dir = tempfile.mkdtemp()
        self.distance_threshold = 0.65      # Balanced threshold - adaptive detection improves quality
        self.verification_threshold = verification_threshold
        self.max_embeddings_per_person = 30  # Allow more embeddings for better matching
        self.min_quality_for_db = 0.40  # More lenient - adaptive detection gives better embeddings

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
                for face_idx, embedding_data in enumerate(embeddings):
                    embedding = embedding_data['embedding']
                    quality = embedding_data['quality']
                    face_size = embedding_data['face_size']
                    
                    # Try to match with existing persons
                    person_id, avg_distance = self.match_average_top_k(embedding, quality, face_size)
                    
                    if person_id is None:
                        # New person found
                        person_id = len(self.face_database)
                        self.face_database[person_id] = {
                            'embeddings': [],
                            'embedding_metadata': [],  # Track quality and size
                            'photos': []
                        }
                        
                        # Add initial embedding
                        self.face_database[person_id]['embeddings'].append(embedding)
                        self.face_database[person_id]['embedding_metadata'].append({
                            'quality': quality,
                            'face_size': face_size,
                            'distance': 0.0
                        })
                        
                        print(f"    ✨ New person {person_id} created (quality={quality:.3f}, size={face_size}px)")
                    else:
                        # Smart embedding addition strategy
                        # Add embeddings that are either high quality OR provide diversity
                        current_count = len(self.face_database[person_id]['embeddings'])
                        
                        # Always add if we have few embeddings (building initial profile)
                        if current_count < 5:
                            should_add = quality >= 0.35  # Very lenient for initial learning
                            reason = "building initial profile"
                        # Be selective once we have enough
                        elif current_count < self.max_embeddings_per_person:
                            # Add if decent quality AND good match (to add variety)
                            should_add = (quality >= self.min_quality_for_db or 
                                        (quality >= 0.38 and avg_distance < 0.4))  # Good match even if lower quality
                            reason = "adding diversity"
                        else:
                            # At limit - only add if better than worst existing
                            should_add = False
                            reason = "embedding limit reached"
                        
                        if should_add:
                            self.face_database[person_id]['embeddings'].append(embedding)
                            self.face_database[person_id]['embedding_metadata'].append({
                                'quality': quality,
                                'face_size': face_size,
                                'distance': avg_distance
                            })
                            print(f"    ✅ Added embedding to person {person_id} (quality={quality:.3f}, dist={avg_distance:.3f}, {reason})")
                        else:
                            print(f"    ⏭️  Skipped embedding for person {person_id} ({reason}, quality={quality:.3f})")

                    # Add photo to person's collection (avoid duplicates)
                    photo_exists = any(
                        p['name'] == image['name'] for p in self.face_database[person_id]['photos']
                    )
                    if not photo_exists:
                        self.face_database[person_id]['photos'].append({
                            'name': image['name'],
                            'id': image['id'],
                            'temp_path': temp_path,
                            'face_count': len(embeddings),  # Track if it's a group photo
                            'face_quality': quality,
                            'face_size': face_size
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

    def match_average_top_k(self, embedding, quality, face_size, k=5):
        """
        Simplified matching focusing on embedding similarity
        Uses pure cosine distance without aggressive quality weighting
        This works better for matching across solo and group photos
        
        Args:
            embedding: Face embedding (already normalized from InsightFace)
            quality: Face detection quality score (0-1)
            face_size: Size of detected face in pixels
            k: Number of top matches to average
        """
        face_database = self.face_database
        best_match_id = None
        best_distance = float('inf')
        all_person_distances = {}  # Track for debugging
        
        # Embedding is already normalized from InsightFace
        embedding_array = np.array(embedding)
        if np.linalg.norm(embedding_array) > 0:
            embedding_norm = embedding_array / np.linalg.norm(embedding_array)
        else:
            embedding_norm = embedding_array
        
        for person_id, person_data in face_database.items():
            if not person_data['embeddings']:
                continue
            
            # Calculate pure cosine distances for this person
            distances = []
            for known_emb in person_data['embeddings']:
                known_emb_array = np.array(known_emb)
                # Ensure normalization
                if np.linalg.norm(known_emb_array) > 0:
                    known_emb_norm = known_emb_array / np.linalg.norm(known_emb_array)
                else:
                    known_emb_norm = known_emb_array
                
                # Pure cosine distance without weighting
                # This is the most reliable metric for InsightFace embeddings
                cosine_similarity = np.dot(embedding_norm, known_emb_norm)
                cosine_distance = 1 - cosine_similarity
                distances.append(cosine_distance)
            
            # Strategy: Use minimum distance (best match) rather than average
            # This is more forgiving when person has variety of photos
            # But also check average of top-k for robustness
            min_distance = min(distances)
            
            # Also calculate average of top K for additional validation
            distances_sorted = sorted(distances)
            adaptive_k = min(k, max(2, len(distances_sorted) // 3))  # Use fewer for robustness
            top_k_distances = distances_sorted[:adaptive_k]
            avg_top_k = np.mean(top_k_distances)
            
            # Use weighted combination: 60% best match, 40% average
            # This balances finding good matches while avoiding outliers
            combined_distance = min_distance * 0.6 + avg_top_k * 0.4
            
            all_person_distances[person_id] = {
                'min': min_distance,
                'avg': avg_top_k,
                'combined': combined_distance,
                'sample_count': len(distances)
            }
            
            if combined_distance < best_distance:
                best_distance = combined_distance
                best_match_id = person_id
        
        # Use fixed threshold for consistency
        # Quality-based adjustments were causing issues with group photos
        threshold = self.distance_threshold
        
        # Debug info with more details
        if best_match_id is not None:
            match_info = all_person_distances[best_match_id]
            print(f"    🎯 Match: Person {best_match_id} | Dist: {best_distance:.3f} | Min: {match_info['min']:.3f} | Avg: {match_info['avg']:.3f} | Samples: {match_info['sample_count']} | Quality: {quality:.2f}")
            
            # Show runner-up if exists
            if len(all_person_distances) > 1:
                sorted_matches = sorted(all_person_distances.items(), key=lambda x: x[1]['combined'])
                if len(sorted_matches) > 1:
                    runner_up_id, runner_up_info = sorted_matches[1]
                    print(f"    🥈 Runner-up: Person {runner_up_id} | Dist: {runner_up_info['combined']:.3f}")
        else:
            print(f"    ❓ No match | Best distance: {best_distance:.3f} | Threshold: {threshold:.3f} | Quality: {quality:.2f}")
        
        if best_distance < threshold:
            return best_match_id, best_distance
        
        return None, None

