from deepface import DeepFace  # pyright: ignore[reportMissingImports]
from insightface.app import FaceAnalysis
import numpy as np
import cv2
import tempfile
import os


class FaceDetector:
    """
    Optimized face detector using InsightFace for accurate detection and embedding extraction
    """
    def __init__(self, tolerance=0.6, face_detection_model='hog', num_jitters=1, min_face_size=80, quality_threshold=0.3):
        """
        Initialize face detector with parameters
        
        Args:
            tolerance: Face recognition tolerance (kept for compatibility)
            face_detection_model: Detection model (kept for compatibility) 
            num_jitters: Number of jitters (kept for compatibility)
            min_face_size: Minimum face size in pixels for detection
            quality_threshold: Minimum face quality score (0-1, higher = better quality)
        """
        self.tolerance = tolerance
        self.face_detection_model = face_detection_model
        self.num_jitters = num_jitters
        self.min_face_size = min_face_size
        self.quality_threshold = quality_threshold
        
        # Initialize the model once for efficiency
        try:
            self.app = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            print("✅ InsightFace model initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing InsightFace model: {e}")
            self.app = None

    def detect_and_extract_faces(self, image_path):
        """
        Extract all high-quality faces from an image and generate individual embeddings
        
        Returns:
            Tuple of (faces, embeddings) where embeddings correspond to individual faces
            Each embedding dict contains: {'embedding': np.array, 'quality': float, 'bbox': tuple, 'age': int, 'gender': str}
        """
        if self.app is None:
            print("❌ InsightFace model not initialized")
            return [], []
            
        try:
            # Validate image loading
            img = cv2.imread(image_path)
            if img is None:
                print(f"❌ Could not load image: {image_path}")
                return [], []
                
            # Convert to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Detect all faces
            faces = self.app.get(img_rgb)
            
            if not faces:
                print(f"No faces detected in {image_path}")
                return [], []
            
            # Filter and process faces based on quality and size
            high_quality_faces = []
            embeddings = []
            
            for idx, face in enumerate(faces):
                # Calculate face size from bounding box
                bbox = face.bbox.astype(int)
                face_width = bbox[2] - bbox[0]
                face_height = bbox[3] - bbox[1]
                face_size = min(face_width, face_height)
                
                # Get face quality score (det_score from InsightFace)
                quality_score = getattr(face, 'det_score', 0.5)
                
                # Filter based on size and quality
                # if face_size < self.min_face_size:
                #     print(f"  ⚠️  Face {idx+1} too small ({face_size}px), skipping")
                #     continue
                    
                if quality_score < self.quality_threshold:
                    print(f"  ⚠️  Face {idx+1} low quality ({quality_score:.3f}), skipping")
                    continue
                
                # Extract normalized embedding
                embedding = face.embedding
                embedding_norm = embedding / np.linalg.norm(embedding)
                
                # Get additional face attributes
                age = getattr(face, 'age', 0)
                gender = 'M' if getattr(face, 'gender', 0) == 1 else 'F'
                
                # Store face data
                high_quality_faces.append(face)
                embeddings.append({
                    "embedding": embedding_norm,  # Normalized embedding
                    "quality": quality_score,
                    "bbox": tuple(bbox),
                    "face_size": face_size,
                    "age": age,
                    "gender": gender
                })
                
                print(f"  ✅ Face {idx+1}: size={face_size}px, quality={quality_score:.3f}, age={age}, gender={gender}")
            
            print(f"Detected {len(embeddings)} high-quality faces out of {len(faces)} total faces")
            return high_quality_faces, embeddings

        except Exception as e:
            print(f"❌ Error in face detection: {e}")
            import traceback
            traceback.print_exc()
            return [], []