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
# from flask import Flask, jsonify, render_template, request
# from flask.wrappers import Response

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


#!/usr/bin/env python3
"""FastAPI web application for model scoring."""

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.templating import Jinja2Templates


app = FastAPI()

# Static + templates (Flask equivalent)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
SCORER_PATH = os.path.join(SRC_DIR, "main.py")


# --- Request model ---
class ScoreRequest(BaseModel):
    model_url: str


# --- Serve front-end ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Score model ---
@app.post("/api/score-model")
async def score_model(payload: ScoreRequest):
    model_url = payload.model_url.strip()

    if not model_url:
        raise HTTPException(status_code=400, detail="model_url is required")

    if not os.path.exists(SCORER_PATH):
        raise HTTPException(status_code=500, detail=f"main.py not found at {SCORER_PATH}")

    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            f.write(f",,{model_url}\n")
            temp_file = f.name

        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT

        result = subprocess.run(
            [sys.executable, SCORER_PATH, temp_file],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=SRC_DIR,
            env=env,
        )

        os.unlink(temp_file)
        temp_file = None

        if result.returncode != 0:
            err = result.stderr or "Unknown error"
            raise HTTPException(status_code=500, detail=err)

        output_lines = result.stdout.strip().split("\n")
        if not output_lines:
            raise HTTPException(status_code=500, detail="No output from scorer")

        model_data = json.loads(output_lines[-1])
        return JSONResponse(model_data)

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Scoring timed out after 5 minutes")

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse output: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Health check ---
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "scorer_path": SCORER_PATH,
        "scorer_exists": os.path.exists(SCORER_PATH),
    }


# --- Run locally ---
if __name__ == "__main__":
    import uvicorn

    print("\n🚀 Starting FastAPI server at http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
