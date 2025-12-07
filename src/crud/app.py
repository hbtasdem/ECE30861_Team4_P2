# """FastAPI application for Model Registry API - OpenAPI v3.4.4 BASELINE endpoints only.

# FILE PURPOSE:
# Creates and configures the main FastAPI application with all 11 BASELINE endpoints for
# managing artifacts from URLs. Initializes the database connection and includes
# all BASELINE route handlers.

# ENDPOINTS PROVIDED (11/11 BASELINE):
# 1-4. POST /artifact, GET/PUT /artifacts (in artifact_routes.py)
# 5. DELETE /reset (in artifact_routes.py)
# 6. GET /artifact/{type}/{id}/cost (in artifact_routes.py)
# 7. GET /artifact/model/{id}/lineage (in artifact_routes.py)
# 8. POST /artifact/model/{id}/license-check (in artifact_routes.py)
# 9. POST /artifact/byRegEx (in artifact_routes.py)
# 10. GET /health (defined below)
# 11. GET /artifact/model/{id}/rate (in rate/routes.py)
# """

# # app.py
# import os
# import sys
# from pathlib import Path
# from typing import Any, Dict

# from fastapi import FastAPI

# # Add src and parent to path for imports
# sys.path.insert(0, str(Path(__file__).parent))
# sys.path.insert(0, str(Path(__file__).parent.parent))

# from src.crud.rate.rate_route import router as rate_router  # noqa: E402
# from src.crud.upload.artifact_routes import router as artifact_router  # noqa: E402
# from src.database import init_db  # noqa: E402
# from src.lineage_tree import router as lineage_router  # noqa: E402

# # Initialize FastAPI app
# app = FastAPI(
#     title="Model Registry API",
#     description="Registry for managing ML models, datasets, and code from URLs",
#     version="1.0.0",
# )

# # Initialize database only if not in test mode
# # if os.getenv("TESTING") != "true":
# #     init_db()

# # Include routers - BASELINE endpoints only
# app.include_router(
#     artifact_router
# )  # POST/GET/PUT /artifact(s)/{type}/{id}, POST /artifacts
# app.include_router(rate_router)  # GET /artifact/model/{id}/rate
# app.include_router(lineage_router)


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


# @app.get("/health")
# def health_check() -> Dict[str, str]:
#     """Health check endpoint"""
#     return {"status": "ok"}


# # uvicorn src.crud.app:app --host 127.0.0.1 --port 8000 --reload
# # go to local host website in browser

# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="127.0.0.1", port=8000)


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
12. POST /api/score-model (NEW - for frontend scoring)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add src and parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crud.rate.rate_route import router as rate_router  # noqa: E402
from src.crud.upload.artifact_routes import router as artifact_router  # noqa: E402
from src.database import init_db  # noqa: E402
from src.lineage_tree import router as lineage_router  # noqa: E402

# Initialize FastAPI app
app = FastAPI(
    title="Model Registry API",
    description="Registry for managing ML models, datasets, and code from URLs",
    version="1.0.0",
)

# Set up templates directory
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Get paths for scoring
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SCORER_PATH = SRC_DIR / "main.py"

# Initialize database only if not in test mode
# if os.getenv("TESTING") != "true":
#     init_db()

# Include routers - BASELINE endpoints only
app.include_router(
    artifact_router, prefix="/api"
)  # POST/GET/PUT /artifact(s)/{type}/{id}, POST /artifacts
app.include_router(rate_router, prefix="/api")  # GET /artifact/model/{id}/rate
app.include_router(lineage_router, prefix="/api")


# Frontend Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Serve the main frontend page"""
    return templates.TemplateResponse("index.html", {"request": request})


# Model Scoring Endpoint (for frontend)
class ModelScoreRequest(BaseModel):
    model_url: str


@app.post("/api/score-model")
async def score_model(request: ModelScoreRequest) -> JSONResponse:
    """Score a model from a HuggingFace URL - called by frontend"""
    model_url = request.model_url.strip()

    if not model_url:
        raise HTTPException(status_code=400, detail="model_url is required")

    # Check if scorer exists
    if not SCORER_PATH.exists():
        raise HTTPException(
            status_code=500, detail=f"main.py not found at {SCORER_PATH}"
        )

    temp_file = None
    try:
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            f.write(f",,{model_url}\n")
            temp_file = f.name

        # Run model scorer (main) with proper PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)  # Add project root to Python path

        result = subprocess.run(
            [sys.executable, str(SCORER_PATH), temp_file],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(SRC_DIR),  # Run from src directory
            env=env,  # Use modified environment
        )

        # Clean up temp file
        os.unlink(temp_file)
        temp_file = None

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            raise HTTPException(status_code=500, detail=error_msg)

        # Parse JSON output
        output_lines = result.stdout.strip().split("\n")
        if not output_lines:
            raise HTTPException(status_code=500, detail="No output from scorer")

        json_output = output_lines[-1]
        model_data = json.loads(json_output)

        return JSONResponse(content=model_data)

    except subprocess.TimeoutExpired:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        raise HTTPException(status_code=504, detail="Scoring timed out after 5 minutes")

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse output: {str(e)}")

    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "ok",
        "scorer_path": str(SCORER_PATH),
        "scorer_exists": SCORER_PATH.exists(),
    }


# uvicorn src.crud.app:app --host 127.0.0.1 --port 8000 --reload
# go to local host website in browser

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("🚀 Model Registry API with Frontend")
    print("=" * 60)
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"Source Directory: {SRC_DIR}")
    print(f"Scorer Path: {SCORER_PATH}")

    if not SCORER_PATH.exists():
        print("\n⚠️  WARNING: main.py not found!")
        print(f"\nExpected at: {SCORER_PATH}")
        print("\nFrontend will still load, but scoring will fail.")
    else:
        print("\n✅ Found main.py")

    print("\n🌐 Starting server on http://127.0.0.1:8000")
    print("📄 Frontend: http://127.0.0.1:8000")
    print("📚 API Docs: http://127.0.0.1:8000/docs")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="127.0.0.1", port=8000)