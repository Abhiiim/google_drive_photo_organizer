from typing import Any, Dict

from schemas.organizer_shemas import OrganizeRequest
from photo_organizer.photo_organizer import PhotoOrganizer
from core.logger import bind_contextvars, clear_contextvars, get_logger


logger = get_logger(__name__)


async def process_photos_enhanced(job_id: str, request: OrganizeRequest, jobs: Dict[str, Dict[str, Any]]):
    """
    Enhanced photo processing with the improved organizer and comprehensive error handling
    
    Args:
        job_id: Unique identifier for this processing job
        request: Organization request with parameters
        jobs: Shared dictionary to track job status
    """
    organizer = None
    
    try:
        bind_contextvars(job_id=job_id)
        # Initialize organizer
        try:
            organizer = PhotoOrganizer(
                distance_threshold=request.distance_threshold,
                verification_threshold=request.verification_threshold
            )
            logger.info("jobs.organizer_initialized", job_id=job_id)
        except Exception as init_error:
            raise Exception(f"Failed to initialize organizer: {str(init_error)}")
        
        # Configure face detector based on request
        try:
            organizer.face_detector.face_detection_model = request.face_detection_model
        except AttributeError:
            # face_detection_model attribute might not exist in current implementation
            logger.warning(
                "jobs.face_detection_model_not_set",
                job_id=job_id,
                requested_model=request.face_detection_model,
            )
        
        # Update job status with progress callback
        def update_progress(message: str, **kwargs):
            try:
                jobs[job_id].update({"message": message, **kwargs})
                logger.debug(
                    "jobs.progress_update",
                    job_id=job_id,
                    message=message,
                    **kwargs,
                )
                
                # Update phase based on message content
                if "Phase 1" in message or "face_detection" in message.lower():
                    jobs[job_id]["phase"] = "face_detection"
                elif "Phase 2" in message or "clustering" in message.lower():
                    jobs[job_id]["phase"] = "clustering"
                elif "Phase 3" in message or "folder_creation" in message.lower():
                    jobs[job_id]["phase"] = "folder_creation"
                elif "Phase 4" in message or "organization" in message.lower():
                    jobs[job_id]["phase"] = "organization"
                elif "Phase 5" in message or "report" in message.lower():
                    jobs[job_id]["phase"] = "reporting"
            except Exception as progress_error:
                logger.warning(
                    "jobs.progress_update_failed",
                    job_id=job_id,
                    error=str(progress_error),
                )
        
        # Process photos
        await organizer.organize_folder(
            request.drive_folder_link, 
            update_progress, 
            max_photos=request.max_photos
        )
        
        # Store processing results for review
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "Organization completed successfully"
        jobs[job_id]["phase"] = "completed"
        jobs[job_id]["processing_stats"] = organizer.processing_stats
        
        # Add clusters for manual review (this would need to be extracted from the organizer)
        jobs[job_id]["clusters"] = {}  # Would contain actual cluster data
        
        # Identify clusters that might need manual review
        review_required = []
        # This logic would identify low-confidence clusters
        jobs[job_id]["review_required"] = review_required
        
        logger.info("jobs.completed", job_id=job_id)
        
    except Exception as e:
        error_message = f"Error: {str(e)}"
        logger.exception("jobs.failed", job_id=job_id, error=str(e))
        
        # Update job status
        if job_id in jobs:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["message"] = error_message
            jobs[job_id]["phase"] = "error"
        
        # Re-raise to allow upper layers to handle if needed
        raise
        
    finally:
        # Ensure cleanup happens even if there was an error
        if organizer is not None:
            try:
                organizer.cleanup()
                logger.debug("jobs.cleanup_completed", job_id=job_id)
            except Exception as cleanup_error:
                logger.warning(
                    "jobs.cleanup_failed",
                    job_id=job_id,
                    error=str(cleanup_error),
                )
        clear_contextvars()
