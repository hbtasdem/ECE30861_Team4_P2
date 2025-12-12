"""FastAPI application for Model Registry API - OpenAPI v3.4.4 BASELINE endpoints only.

FILE PURPOSE:
Creates and configures the main FastAPI application with all 11 BASELINE endpoints for
managing artifacts from URLs. Initializes the database connection and includes
all BASELINE route handlers.

ENDPOINTS PROVIDED (10/10 BASELINE):
1-4. POST /artifact, GET/PUT /artifacts (in artifact_routes.py)
5. DELETE /reset (in artifact_routes.py)
6. GET /artifact/{type}/{id}/cost (in artifact_routes.py)
7. GET /artifact/model/{id}/lineage (in artifact_routes.py)
8. POST /artifact/byRegEx (in artifact_routes.py)
9. GET /health (defined below)
10. GET /artifact/model/{id}/rate (in rate/routes.py)
"""
# app.py

import logging
import sys
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Add src and parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.authentication_routes import router as auth_router  # noqa: E402
from src.crud.rate_route import router as rate_router  # noqa: E402
from src.crud.upload.artifact_routes import \
    router as artifact_router  # noqa: E402
from src.database import init_db  # noqa: E402
from src.health_monitor import HealthComponentCollection  # noqa: E402
from src.health_monitor import health_monitor  # noqa: E402

templates = Jinja2Templates(directory="templates")

# Initialize FastAPI app
app = FastAPI(
    title="Model Registry API",
    description="Registry for managing ML models, datasets, and code from URLs",
    version="1.0.0",
)


# Per spec Section 3.2.1: S3-based artifact storage
# Database tables are used for authentication and audit logging
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup"""
    init_db()


# --------------- Configure logging ---------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")
# silence logs we don't want
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")

    try:
        body = await request.json()
        logger.info(f"Request body: {body}")
    except Exception:
        body = None

    response = await call_next(request)

    logger.info(f"Response status: {response.status_code}")
    if hasattr(response, "body") and response.body is not None:
        try:
            logger.info(f"Response body: {response.body.decode('utf-8')}")
        except Exception:
            logger.info(f"Response body (binary or non-text): {response.body}")

    return response


# --------------- Include routers ---------------
app.include_router(artifact_router)  # POST/GET/PUT /artifact(s)/{type}/{id}, POST /artifacts
app.include_router(rate_router)  # GET /artifact/model/{id}/rate
app.include_router(auth_router)  # PUT /authenticate, POST /register


# @app.get("/")
# def root() -> Dict[str, Any]:
#     """API root - returns available endpoints"""
#     return {
#         "message": "Model Registry API",
#         "endpoints": {
#             "health": "/health",
#             "upload": "/api/models/upload",
#             "docs": "/docs",
#             "redoc": "/redoc",
#         },
#     }

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/health/components", response_model=HealthComponentCollection)
def get_health_components(
    windowMinutes: int = Query(60, ge=5, le=1440),
    includeTimeline: bool = Query(False),
) -> HealthComponentCollection:
    """Get detailed health diagnostics for registry components (NON-BASELINE).

    Per OpenAPI v3.4.4 spec /health/components endpoint:
    - Returns per-component health diagnostics
    - Includes status, metrics, issues, and logs from observation window
    - Optional timeline sampling available

    Args:
        windowMinutes: Observation window in minutes (5-1440, default 60)
        includeTimeline: Include activity timelines if true (default false)

    Returns:
        HealthComponentCollection with all component details
    """
    return health_monitor.get_health_components(window_minutes=windowMinutes, include_timeline=includeTimeline)


@app.get("/tracks")
def extended_track() -> Dict[str, List]:
    return {"plannedTracks": ["Access control track"]}


# uvicorn src.crud.app:app --host 127.0.0.1 --port 8000 --reload
# go to local host website in browser

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
