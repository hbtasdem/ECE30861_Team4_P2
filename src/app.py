# app.py

import os
import sys
from typing import Any

from fastapi import FastAPI

sys.path.insert(0, os.path.dirname(__file__))

from database import init_db  # noqa: E402
from rate.routes import router as rate_router  # noqa: E402
from upload.routes import router as upload_router  # noqa: E402

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


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}
# uvicorn src.app:app --host 127.0.0.1 --port 8000 --reload
# then in browser add /health to the end and you see... something!


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
