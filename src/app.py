# app.py
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from typing import Any, Dict  # noqa: E402

from fastapi import FastAPI  # noqa: E402

from database import init_db  # noqa: E402
from upload.routes import router as upload_router  # noqa: E402

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
async def root() -> Dict[str, Any]:
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
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
