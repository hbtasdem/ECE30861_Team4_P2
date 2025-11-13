"""FastAPI application instance for the Model Registry API.

This file creates and configures the main FastAPI application object that handles
all HTTP requests. It sets up the database and includes all API route handlers.

Key features:
- Creates the FastAPI app with title and description
- Initializes the database connection
- Registers all model upload and retrieval routes
- Provides health check endpoint
"""

# app.py
import os
import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI

# Add src and parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from crud.rate.rate_route import router as rate_route  # noqa: E402
from crud.upload.auth_routes import router as auth_router  # noqa: E402
from crud.upload.routes import router as upload_router  # noqa: E402
from src.database import init_db  # noqa: E402

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
app.include_router(auth_router)  # NEW: Include authentication routes
app.include_router(rate_route)  # /artifact/model/{id}/rate


@app.get("/")
def root() -> Dict[str, Any]:
    """API root - returns available endpoints"""
    return {
        "message": "Model Registry API",
        "endpoints": {
            "health": "/health",
            "upload": "/api/models/upload",
            "rate": "/artifact/model/{id}/rate"
        }
    }


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}


# uvicorn crud.app:app --host 127.0.0.1 --port 8000 --reload
# go to local host website in browser

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
