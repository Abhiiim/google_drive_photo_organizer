from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logger import get_logger, setup_logging
from database import get_db, init_db
from middleware import RequestLoggingMiddleware
from routers.organizer_router import organizer_router


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

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("application.startup", message="Improved Google Drive Face Organizer API started")

app.include_router(organizer_router)

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