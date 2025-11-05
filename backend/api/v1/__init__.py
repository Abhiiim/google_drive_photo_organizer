"""
API v1 endpoints.
"""
from fastapi import APIRouter

from api.v1 import jobs, persons


api_router = APIRouter()

# Include route modules
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(persons.router, prefix="/persons", tags=["persons"])

