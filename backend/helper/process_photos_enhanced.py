from typing import Any, Dict

from schemas.organizer_shemas import OrganizeRequest
from photo_organizer.photo_organizer import PhotoOrganizer


async def process_photos_enhanced(job_id: str, request: OrganizeRequest, jobs: Dict[str, Dict[str, Any]]):
    """Enhanced photo processing with the improved organizer"""
    try:
        organizer = PhotoOrganizer(
            distance_threshold=request.distance_threshold,
            verification_threshold=request.verification_threshold
        )
        
        # Configure face detector based on request
        organizer.face_detector.face_detection_model = request.face_detection_model
        
        # Update job status with progress callback
        def update_progress(message: str, **kwargs):
            jobs[job_id].update({"message": message, **kwargs})
            
            # Update phase based on message content
            if "Phase 1" in message:
                jobs[job_id]["phase"] = "face_detection"
            elif "Phase 2" in message:
                jobs[job_id]["phase"] = "clustering"
            elif "Phase 3" in message:
                jobs[job_id]["phase"] = "folder_creation"
            elif "Phase 4" in message:
                jobs[job_id]["phase"] = "organization"
            elif "Phase 5" in message or "report" in message.lower():
                jobs[job_id]["phase"] = "reporting"
        
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
        
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = f"Error: {str(e)}"
        jobs[job_id]["phase"] = "error"
        print(f"Error in job {job_id}: {e}")
