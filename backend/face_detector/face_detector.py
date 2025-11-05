from deepface import DeepFace  # pyright: ignore[reportMissingImports]
from insightface.app import FaceAnalysis
import numpy as np
import cv2
import tempfile
import os
from pathlib import Path

from core.logger import get_logger


class FaceDetector:
    """
    Optimized face detector using InsightFace for accurate detection and embedding extraction
    """
    def __init__(self, min_face_size=50, quality_threshold=0.3):
        """
        Initialize face detector with parameters
        
        Args:
            min_face_size: Minimum face size in pixels for detection
            quality_threshold: Minimum face quality score (0-1, higher = better quality)
        """
        self.min_face_size = min_face_size
        self.quality_threshold = quality_threshold
        self.logger = get_logger(__name__)

    def detect_and_extract_faces(self, image_path):
        """
        Extract all faces from an image with improved multi-face detection
        
        Returns:
            Tuple of (faces, embeddings) where embeddings is a list of embedding dictionaries
        """
        try:
            self.logger.debug(
                "face_detector.process_image_start",
                image_name=Path(image_path).name,
            )
            
            # Extract faces with embeddings - try multiple backends for better detection
            faces = None
            detector_backends = ['retinaface', 'mtcnn', 'opencv']
            
            for backend in detector_backends:
                try:
                    faces = DeepFace.extract_faces(
                        img_path=str(image_path),
                        detector_backend=backend,
                        enforce_detection=False,
                        align=True
                    )
                    if faces and len(faces) > 0:
                        self.logger.info(
                            "face_detector.backend_success",
                            backend=backend,
                            face_count=len(faces),
                        )
                        break
                except Exception as backend_error:
                    self.logger.warning(
                        "face_detector.backend_failed",
                        backend=backend,
                        error=str(backend_error),
                    )
                    continue
            
            if not faces:
                self.logger.info("face_detector.no_faces_detected", image_name=Path(image_path).name)
                return [], []

            # Validate faces
            valid_faces = self.extract_valid_faces(faces, min_confidence=self.quality_threshold, min_face_size=self.min_face_size)
            
            if not valid_faces:
                self.logger.info(
                    "face_detector.no_valid_faces",
                    image_name=Path(image_path).name,
                )
                return [], []
            
            # Generate embeddings for valid faces
            embeddings = []
            for i, face_data in enumerate(valid_faces):
                try:
                    # Generate embedding from the extracted face numpy array
                    embedding_result = DeepFace.represent(
                        img_path=face_data['face'],  # This is a numpy array
                        model_name='Facenet512',
                        detector_backend='skip',  # IMPORTANT: Skip detection since face is already extracted
                        enforce_detection=False
                    )
                    
                    embeddings.append(embedding_result[0])
                    self.logger.debug(
                        "face_detector.embedding_generated",
                        face_index=i + 1,
                        image_name=Path(image_path).name,
                    )
                    
                except Exception as embed_error:
                    self.logger.warning(
                        "face_detector.embedding_failed",
                        face_index=i + 1,
                        error=str(embed_error),
                    )
                    continue
            
            self.logger.info(
                "face_detector.processing_complete",
                image_name=Path(image_path).name,
                embedding_count=len(embeddings),
            )
            return faces, embeddings
        
        except Exception as e:
            self.logger.exception(
                "face_detector.processing_failed",
                image_name=Path(image_path).name,
                error=str(e),
            )
            return [], []
        
    def extract_valid_faces(self, faces, min_confidence=0.3, min_face_size=50):
        """
        Extract faces with validation to reduce false positives
        Note: Lowered thresholds to better detect faces in group photos
        """
        try:
            valid_faces = []
            for i, face in enumerate(faces):
                # DeepFace.extract_faces doesn't always return confidence
                # So we'll be more lenient and focus on face size
                confidence = face.get('confidence', 1.0)  # Default to 1.0 if not available
                facial_area = face.get('facial_area', {})
                
                # Calculate face size
                width = facial_area.get('w', 0)
                height = facial_area.get('h', 0)
                face_size = min(width, height) if width > 0 and height > 0 else 100  # Default size if not available
                
                # More lenient validation for multi-face detection
                if confidence >= min_confidence and face_size >= min_face_size:
                    valid_faces.append(face)
                    self.logger.debug(
                        "face_detector.face_valid",
                        face_index=i + 1,
                        confidence=round(confidence, 3),
                        face_size=face_size,
                    )
                else:
                    self.logger.debug(
                        "face_detector.face_rejected",
                        face_index=i + 1,
                        confidence=round(confidence, 3),
                        face_size=face_size,
                        min_confidence=min_confidence,
                        min_face_size=min_face_size,
                    )
            
            self.logger.info(
                "face_detector.validation_summary",
                accepted=len(valid_faces),
                total=len(faces),
            )
            return valid_faces
            
        except Exception as e:
            self.logger.exception("face_detector.validation_failed", error=str(e))
            return []
