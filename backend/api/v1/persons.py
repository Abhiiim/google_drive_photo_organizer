"""
API endpoints for person management.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_person_service
from services.person_service import PersonService
from core.logger import get_logger


logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_persons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    person_service: PersonService = Depends(get_person_service),
) -> List[Dict[str, Any]]:
    """
    List all persons.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session (injected)
        
    Returns:
        List of persons with statistics
    """
    try:
        logger.info(f"Listing persons (skip={skip}, limit={limit})")
        persons = person_service.get_all_persons()
        
        # Apply pagination
        paginated = persons[skip:skip + limit]
        
        logger.info(f"Found {len(persons)} person(s), returning {len(paginated)}")
        return paginated
    except Exception as e:
        logger.error(f"Error listing persons: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list persons: {str(e)}"
        )


@router.get("/{person_id}", response_model=Dict[str, Any])
async def get_person(
    person_id: int,
    person_service: PersonService = Depends(get_person_service),
) -> Dict[str, Any]:
    """
    Get a specific person by ID.
    
    Args:
        person_id: Person ID
        db: Database session (injected)
        
    Returns:
        Person information
        
    Raises:
        HTTPException: If person not found
    """
    try:
        logger.info(f"Getting person: {person_id}")
        person = person_service.get_person(person_id)
        
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Person not found: {person_id}"
            )
        
        return person
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get person: {str(e)}"
        )


@router.get("/{person_id}/statistics", response_model=Dict[str, Any])
async def get_person_statistics(
    person_id: int,
    person_service: PersonService = Depends(get_person_service),
) -> Dict[str, Any]:
    """
    Get statistics for a specific person.
    
    Args:
        person_id: Person ID
        db: Database session (injected)
        
    Returns:
        Person statistics
        
    Raises:
        HTTPException: If person not found
    """
    try:
        logger.info(f"Getting statistics for person: {person_id}")
        stats = person_service.get_person_statistics(person_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Person not found: {person_id}"
            )
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics for person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get person statistics: {str(e)}"
        )


@router.patch("/{person_id}", response_model=Dict[str, Any])
async def update_person(
    person_id: int,
    name: Optional[str] = None,
    person_service: PersonService = Depends(get_person_service),
) -> Dict[str, Any]:
    """
    Update person information.
    
    Args:
        person_id: Person ID
        name: Optional new name
        db: Database session (injected)
        
    Returns:
        Updated person information
        
    Raises:
        HTTPException: If person not found
    """
    try:
        logger.info(f"Updating person: {person_id}")
        
        updated_person = person_service.update_person(person_id, name=name)
        
        if not updated_person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Person not found: {person_id}"
            )
        
        logger.info(f"Person {person_id} updated successfully")
        return updated_person
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update person: {str(e)}"
        )


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: int,
    person_service: PersonService = Depends(get_person_service),
):
    """
    Delete a person.
    
    Args:
        person_id: Person ID
        db: Database session (injected)
        
    Raises:
        HTTPException: If person not found
    """
    try:
        logger.info(f"Deleting person: {person_id}")
        
        success = person_service.delete_person(person_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Person not found: {person_id}"
            )
        
        logger.info(f"Person {person_id} deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete person: {str(e)}"
        )


@router.get("/search/", response_model=List[Dict[str, Any]])
async def search_persons(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    person_service: PersonService = Depends(get_person_service),
) -> List[Dict[str, Any]]:
    """
    Search persons by name.
    
    Args:
        q: Search query
        limit: Maximum number of results
        db: Database session (injected)
        
    Returns:
        List of matching persons
    """
    try:
        logger.info(f"Searching persons with query: {q}")
        results = person_service.search_persons(q, limit)
        
        logger.info(f"Found {len(results)} matching person(s)")
        return results
    except Exception as e:
        logger.error(f"Error searching persons: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search persons: {str(e)}"
        )

