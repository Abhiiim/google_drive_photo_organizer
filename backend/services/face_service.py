"""
Service layer for face detection and recognition operations.
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np

from core.logger import get_logger
from face_detector.face_detector import FaceDetector


logger = get_logger(__name__)


class FaceService:
    """
    Service for face detection, embedding generation, and face comparison.
    
    This service encapsulates all face-related operations and provides
    a clean interface for face detection workflows.
    """
    
    def __init__(self):
        """
        Initialize FaceService with a face detector instance.
        """
        self.face_detector = FaceDetector()
        logger.info("FaceService initialized")
    
    def detect_faces_in_image(
        self,
        image_path: str,
        confidence_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Detect faces in a single image.
        
        Args:
            image_path: Path to the image file
            confidence_threshold: Minimum confidence score for face detection
            
        Returns:
            List of detected faces with bounding boxes and embeddings
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image cannot be processed
        """
        try:
            logger.debug(f"Detecting faces in image: {image_path}")
            
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            faces = self.face_detector.detect_faces(image_path, confidence_threshold)
            logger.info(f"Detected {len(faces)} face(s) in {image_path}")
            
            return faces
        except Exception as e:
            logger.error(f"Error detecting faces in {image_path}: {str(e)}")
            raise
    
    def generate_face_embeddings(
        self,
        image_path: str,
        face_locations: Optional[List[Tuple[int, int, int, int]]] = None
    ) -> List[np.ndarray]:
        """
        Generate face embeddings for detected faces.
        
        Args:
            image_path: Path to the image file
            face_locations: Optional list of face bounding boxes (top, right, bottom, left)
            
        Returns:
            List of face embeddings as numpy arrays
        """
        try:
            logger.debug(f"Generating embeddings for: {image_path}")
            embeddings = self.face_detector.get_face_embeddings(image_path, face_locations)
            logger.info(f"Generated {len(embeddings)} embedding(s)")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def compare_faces(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        threshold: float = 0.5
    ) -> Tuple[bool, float]:
        """
        Compare two face embeddings.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            threshold: Distance threshold for matching (lower = more similar)
            
        Returns:
            Tuple of (is_match, distance)
        """
        try:
            distance = self.face_detector.calculate_distance(embedding1, embedding2)
            is_match = distance < threshold
            logger.debug(f"Face comparison - Distance: {distance:.4f}, Match: {is_match}")
            return is_match, distance
        except Exception as e:
            logger.error(f"Error comparing faces: {str(e)}")
            raise
    
    def cluster_faces(
        self,
        embeddings: List[np.ndarray],
        threshold: float = 0.5
    ) -> List[int]:
        """
        Cluster face embeddings into groups of similar faces.
        
        Args:
            embeddings: List of face embeddings
            threshold: Distance threshold for clustering
            
        Returns:
            List of cluster labels for each embedding
        """
        try:
            logger.info(f"Clustering {len(embeddings)} face embeddings")
            clusters = self.face_detector.cluster_faces(embeddings, threshold)
            logger.info(f"Created {len(set(clusters))} cluster(s)")
            return clusters
        except Exception as e:
            logger.error(f"Error clustering faces: {str(e)}")
            raise
    
    def validate_face_quality(
        self,
        image_path: str,
        min_size: int = 50,
        min_confidence: float = 0.3
    ) -> Dict[str, Any]:
        """
        Validate face quality in an image.
        
        Args:
            image_path: Path to the image file
            min_size: Minimum face size in pixels
            min_confidence: Minimum confidence score
            
        Returns:
            Dictionary with quality assessment
        """
        try:
            faces = self.detect_faces_in_image(image_path, min_confidence)
            
            quality = {
                "has_face": len(faces) > 0,
                "face_count": len(faces),
                "faces_meet_quality": [],
            }
            
            for face in faces:
                width = face.get("width", 0)
                height = face.get("height", 0)
                confidence = face.get("confidence", 0)
                
                meets_quality = (
                    width >= min_size and
                    height >= min_size and
                    confidence >= min_confidence
                )
                
                quality["faces_meet_quality"].append(meets_quality)
            
            quality["all_faces_valid"] = all(quality["faces_meet_quality"])
            
            logger.info(f"Face quality check: {quality}")
            return quality
        except Exception as e:
            logger.error(f"Error validating face quality: {str(e)}")
            raise
    
    def extract_face_region(
        self,
        image_path: str,
        face_location: Tuple[int, int, int, int],
        padding: int = 20
    ) -> np.ndarray:
        """
        Extract face region from image with padding.
        
        Args:
            image_path: Path to the image file
            face_location: Face bounding box (top, right, bottom, left)
            padding: Padding around face in pixels
            
        Returns:
            Face region as numpy array
        """
        try:
            face_region = self.face_detector.extract_face(
                image_path,
                face_location,
                padding
            )
            logger.debug(f"Extracted face region from {image_path}")
            return face_region
        except Exception as e:
            logger.error(f"Error extracting face region: {str(e)}")
            raise

