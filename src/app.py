# app.py
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from database import init_db
from upload.routes import router as upload_router

# Initialize FastAPI app
app = FastAPI(
    title="Model Registry API",
    description="Upload and manage ML models in ZIP format",
    version="1.0.0"
)

# Initialize database only if not in test mode
if os.getenv("TESTING") != "true":
    init_db()

# Include routers
app.include_router(upload_router)

@app.get("/")
async def root():
    """API root - returns available endpoints"""
    return {
        "message": "Model Registry API",
        "endpoints": {
            "health": "/health",
            "upload": "/api/models/upload",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
