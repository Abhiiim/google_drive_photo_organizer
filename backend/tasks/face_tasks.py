"""Celery tasks for face detection and clustering operations."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from celery import shared_task

from core.config import get_settings
from core.logger import get_logger
from face_detector.face_detector import FaceDetector


logger = get_logger(__name__)
settings = get_settings()


@shared_task(bind=True, name="backend.tasks.face_tasks.detect_faces_task")
def detect_faces_task(
    self,
    image_path: str,
    detection_model: str | None = None,
) -> Dict[str, Any]:
    """Detect faces and embeddings for a single image."""

    logger.info("tasks.detect_faces.start", image_path=image_path, detection_model=detection_model)

    detector = FaceDetector(
        min_face_size=settings.face_min_size,
        quality_threshold=settings.face_quality_threshold,
    )

    if detection_model:
        try:
            detector.face_detection_model = detection_model
        except AttributeError:
            logger.warning(
                "tasks.detect_faces.unsupported_model",
                detection_model=detection_model,
            )

    faces, embeddings = detector.detect_and_extract_faces(image_path)
    logger.info(
        "tasks.detect_faces.completed",
        image_path=image_path,
        faces_detected=len(faces or []),
    )

    return {
        "faces": faces,
        "embeddings": embeddings,
    }


@shared_task(bind=True, name="backend.tasks.face_tasks.cluster_faces_task")
def cluster_faces_task(self, embeddings: List[Tuple[str, List[float]]]) -> Dict[str, Any]:
    """Placeholder clustering task that groups embeddings by identifier."""

    logger.info("tasks.cluster_faces.start", embedding_count=len(embeddings))

    clusters: Dict[str, List[List[float]]] = {}
    for identifier, embedding in embeddings:
        clusters.setdefault(identifier, []).append(embedding)

    logger.info("tasks.cluster_faces.completed", cluster_count=len(clusters))

    return {"clusters": clusters, "status": "aggregated"}

