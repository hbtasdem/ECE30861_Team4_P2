"""FastAPI application for Model Registry API - OpenAPI v3.4.4 BASELINE endpoints only.

FILE PURPOSE:
Creates and configures the main FastAPI application with all 11 BASELINE endpoints for
managing artifacts from URLs. Initializes the database connection and includes
all BASELINE route handlers.

ENDPOINTS PROVIDED (11/11 BASELINE):
1-4. POST /artifact, GET/PUT /artifacts (in artifact_routes.py)
5. DELETE /reset (in artifact_routes.py)
6. GET /artifact/{type}/{id}/cost (in artifact_routes.py)
7. GET /artifact/model/{id}/lineage (in artifact_routes.py)
8. POST /artifact/model/{id}/license-check (in artifact_routes.py)
9. POST /artifact/byRegEx (in artifact_routes.py)
10. GET /health (defined below)
11. GET /artifact/model/{id}/rate (in rate/routes.py)
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

from src.crud.rate.routes import router as rate_router  # noqa: E402
from src.crud.upload.artifact_routes import router as artifact_router  # noqa: E402
from src.database import init_db  # noqa: E402
from src.lineage_tree import router as lineage_router  # noqa: E402

# Initialize FastAPI app
app = FastAPI(
    title="Model Registry API",
    description="Registry for managing ML models, datasets, and code from URLs",
    version="1.0.0",
)

# Initialize database only if not in test mode
if os.getenv("TESTING") != "true":
    init_db()

# Include routers - BASELINE endpoints only
app.include_router(
    artifact_router
)  # POST/GET/PUT /artifact(s)/{type}/{id}, POST /artifacts
app.include_router(rate_router)  # GET /artifact/model/{id}/rate
app.include_router(lineage_router)


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
