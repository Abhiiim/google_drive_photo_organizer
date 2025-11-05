"""
API endpoints for job management.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_job_service, get_organization_service
from core.logger import get_logger
from schemas.organizer_shemas import JobCreateResponse, JobStatusResponse, OrganizeRequest
from services.job_service import JobService
from services.organization_service import OrganizationService


logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/organize",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_organization_job(
    request: OrganizeRequest,
    org_service: OrganizationService = Depends(get_organization_service),
    job_service: JobService = Depends(get_job_service),
) -> JobCreateResponse:
    """
    Create a new photo organization job.
    
    This endpoint starts an asynchronous job to organize photos from
    a Google Drive folder by detecting and clustering faces.
    
    Args:
        request: Organization request with folder_id
        db: Database session (injected)
        org_service: Organization service (injected)
        
    Returns:
        Job information with job_id
        
    Raises:
        HTTPException: If folder validation fails
    """
    try:
        logger.info("Received organization request", folder=request.drive_folder_link)

        folder_id = request.drive_folder_link

        validation = org_service.validate_folder(folder_id)
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid folder: {', '.join(validation['errors'])}"
            )
        
        folder_name = validation.get("folder_name")
        total_photos = validation.get("photo_count", 0)

        job_id = org_service.start_organization_job(
            folder_id,
            folder_name=folder_name,
            total_photos=total_photos,
            config=request.model_dump(),
        )

        job_service.update_job_state(
            job_id,
            {
                "status": "pending",
                "message": "Organization job created, queued for processing",
                "phase": "initialization",
                "total_photos": total_photos,
                "processed": 0,
                "faces_detected": 0,
                "persons_found": 0,
            },
        )

        logger.info("Organization job created", job_id=job_id)

        return JobCreateResponse(job_id=job_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization job: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> Dict[str, Any]:
    """
    Get the status of an organization job.
    
    Args:
        job_id: Job ID to query
        
    Returns:
        Job status information
        
    Raises:
        HTTPException: If job not found
    """
    try:
        logger.debug(f"Getting status for job: {job_id}")
        
        job = job_service.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )

        logger.debug("Job status", job_id=job_id, status=job.get("status"))
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/", response_model=Dict[str, Any])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    job_service: JobService = Depends(get_job_service),
) -> Dict[str, Any]:
    """
    List all organization jobs.
    
    Args:
        skip: Number of jobs to skip (pagination)
        limit: Maximum number of jobs to return
        status_filter: Optional status filter
        
    Returns:
        List of jobs
    """
    try:
        logger.debug(f"Listing jobs (skip={skip}, limit={limit}, status={status_filter})")
        
        page = job_service.paginate_jobs(
            skip=skip,
            limit=limit,
            status=status_filter,
        )

        return {
            "total": page["total"],
            "skip": skip,
            "limit": limit,
            "jobs": page["items"],
        }
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
):
    """
    Delete (cancel) an organization job.
    
    Args:
        job_id: Job ID to delete
        
    Raises:
        HTTPException: If job not found
    """
    try:
        logger.info(f"Deleting job: {job_id}")
        
        job = job_service.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )

        job_service.delete_job(job_id)
        logger.info("Job deleted", job_id=job_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )

