from typing import Any, Dict
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends

from schemas.organizer_shemas import OrganizeRequest
from helper.process_photos_enhanced import process_photos_enhanced

organizer_router = APIRouter()

jobs: Dict[str, Dict[str, Any]] = {}

@organizer_router.post("/api/organize", tags=["Organization"])
async def organize_photos(request: OrganizeRequest, background_tasks: BackgroundTasks):
    """
    Start enhanced photo organization process with configurable parameters
    """
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "message": "Starting enhanced photo organization...",
        "phase": "initialization",
        "total_photos": 0,
        "processed": 0,
        "faces_detected": 0,
        "clusters_created": 0,
        "persons_found": 0,
        "folders_created": 0,
        "processing_stats": {
            "photos_with_single_face": 0,
            "photos_with_multiple_faces": 0,
            "photos_without_faces": 0,
            "processing_errors": 0
        },
        "clusters": {},
        "review_required": []
    }
    
    # Start background task with enhanced organizer
    background_tasks.add_task(process_photos_enhanced, job_id, request, jobs)
    
    return {"job_id": job_id, "status": "processing"}


@organizer_router.get("/api/status/{job_id}", tags=["Organization"])
async def get_job_status(job_id: str):
    """
    Get the status of a photo organization job
    """
    if job_id not in jobs:
        return {"error": "Job not found"}, 404
    
    job_data = jobs[job_id]
    
    # Calculate progress percentage
    progress_percentage = 0
    if job_data.get("total_photos", 0) > 0:
        progress_percentage = round((job_data.get("processed", 0) / job_data["total_photos"]) * 100)
    
    return {
        "job_id": job_id,
        "status": job_data.get("status", "unknown"),
        "message": job_data.get("message", ""),
        "phase": job_data.get("phase", "unknown"),
        "progress_percentage": progress_percentage,
        "total_photos": job_data.get("total_photos", 0),
        "processed": job_data.get("processed", 0),
        "faces_detected": job_data.get("faces_detected", 0),
        "persons_found": job_data.get("persons_found", 0),
        "folders_created": job_data.get("folders_created", 0),
        "processing_stats": job_data.get("processing_stats", {}),
        "multi_face_summary": {
            "single_face_photos": job_data.get("processing_stats", {}).get("photos_with_single_face", 0),
            "multi_face_photos": job_data.get("processing_stats", {}).get("photos_with_multiple_faces", 0),
            "no_face_photos": job_data.get("processing_stats", {}).get("photos_without_faces", 0)
        }
    }

