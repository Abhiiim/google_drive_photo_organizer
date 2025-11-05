from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from core.config import get_settings
from core.logger import get_logger, setup_logging
from core.exceptions import AppException, ValidationError, JobNotFoundError, ProcessingError, GoogleDriveError
from database import get_db, init_db
from middleware import RequestLoggingMiddleware
from routers.organizer_router import organizer_router
from schemas.organizer_shemas import ErrorResponse
from api.v1 import api_router as api_v1_router


setup_logging()

settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.project_name,
    description="Advanced face detection and organization with manual review capabilities",
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


# Global exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions."""
    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        timestamp=exc.timestamp.isoformat(),
        path=exc.path or str(request.url)
    )

    logger.warning(
        "app.exception",
        error_code=exc.error_code,
        message=exc.message,
        path=error_response.path,
        status_code=exc.status_code,
        details=exc.details
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
    """Handle Pydantic validation errors."""
    error_details = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        error_details[field] = error["msg"]

    error_response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"validation_errors": error_details},
        timestamp=datetime.utcnow().isoformat(),
        path=str(request.url)
    )

    logger.warning(
        "validation.exception",
        message="Request validation failed",
        path=str(request.url),
        validation_errors=error_details
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions."""
    error_response = ErrorResponse(
        error_code="HTTP_ERROR",
        message=exc.detail,
        details={"status_code": exc.status_code},
        timestamp=datetime.utcnow().isoformat(),
        path=str(request.url)
    )

    # Only log non-404 errors as warnings
    if exc.status_code >= 500:
        logger.error(
            "http.exception",
            status_code=exc.status_code,
            message=exc.detail,
            path=str(request.url)
        )
    elif exc.status_code >= 400:
        logger.warning(
            "http.exception",
            status_code=exc.status_code,
            message=exc.detail,
            path=str(request.url)
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    error_response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        details={"error_type": type(exc).__name__},
        timestamp=datetime.utcnow().isoformat(),
        path=str(request.url)
    )

    logger.exception(
        "unhandled.exception",
        message="An unexpected error occurred",
        error_type=type(exc).__name__,
        path=str(request.url),
        error=str(exc)
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )


@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("application.startup", message="Improved Google Drive Face Organizer API started")

# Include API routers
# Legacy router (for backward compatibility)
app.include_router(organizer_router)

# New v1 API with service layer architecture
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check"""
    try:
        # Test database connection
        db = next(get_db())
        db.close()
        
        return {
            "status": "healthy",
            "version": settings.version,
            "features": [
                "Enhanced face detection with face_recognition library",
                "Advanced clustering with verification",
                "Manual review and correction capabilities",
                "Detailed processing statistics",
                "Face verification endpoints"
            ]
        }
    except Exception as e:
        logger.exception("health_check.failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)