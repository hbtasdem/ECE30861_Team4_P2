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
from typing import Any, Dict

from fastapi import FastAPI

from crud.rate.routes import router as rate_router
from crud.upload.routes import router as upload_router
from src.database import init_db

# Initialize FastAPI app
app = FastAPI(
    title="Model Registry API",
    description="Upload and manage ML models in ZIP format",
    version="1.0.0",
)

# Initialize database only if not in test mode
if os.getenv("TESTING") != "true":
    init_db()

# Include routers
app.include_router(upload_router)
app.include_router(rate_router)  # /artifact/model/{id}/rate


@app.get("/")
def root() -> Dict[str, Any]:
    """API root - returns available endpoints"""
    return {
        "message": "Model Registry API",
        "endpoints": {
            "health": "/health",
            "upload": "/api/models/upload",
            "docs": "/docs",
            "redoc": "/redoc",
        },
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
