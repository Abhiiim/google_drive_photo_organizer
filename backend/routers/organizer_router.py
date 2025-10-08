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
        "processing_stats": {},
        "clusters": {},
        "review_required": []
    }
    
    # Start background task with enhanced organizer
    background_tasks.add_task(process_photos_enhanced, job_id, request, jobs)
    
    return {"job_id": job_id, "status": "processing"}

