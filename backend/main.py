from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncio
from typing import Dict, Any, List, Optional
import uuid
import json
import os

from routers.organizer_router import organizer_router
from database import init_db, get_db, Person, PhotoFace

app = FastAPI(
    title="Improved Google Drive Face Organizer",
    description="Advanced face detection and organization with manual review capabilities",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 Improved Google Drive Face Organizer API started")

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
            "version": "2.0.0",
            "features": [
                "Enhanced face detection with face_recognition library",
                "Advanced clustering with verification",
                "Manual review and correction capabilities",
                "Detailed processing statistics",
                "Face verification endpoints"
            ]
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)