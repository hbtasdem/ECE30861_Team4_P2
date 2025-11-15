"""Model rating endpoint - OpenAPI v3.4.4 BASELINE spec.

FILE PURPOSE:
Provides the GET /artifact/model/{id}/rate endpoint to retrieve model ratings and evaluation scores from the registry. All ratings are stored in the registry database based on artifact metadata and evaluation results.

ENDPOINTS IMPLEMENTED (1/11 BASELINE):
1. GET /artifact/model/{id}/rate - Get model rating and metrics
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.crud.upload.auth import get_current_user
from src.database import get_db
from src.database_models import Artifact as ArtifactModel

# Use example python dict for database for now
from src.crud.rate.dict_artifacts_db import artifacts_db

router = APIRouter()


@router.get("/artifact/model/{artifact_id}/rate")
async def get_model_rating(
    artifact_id: str, x_authorization: str = Header(None), db: Session = Depends(get_db)
) -> JSONResponse:
    """Get ratings for this model artifact (BASELINE endpoint)."""
    if not artifact_id:
        raise HTTPException(
            status_code=400,
            detail="There is missing field(s) in the artifact_id or it is formed improperly, or is invalid.",
        )

    if not x_authorization:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    try:
        get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    artifact = artifacts_db.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")

    # The rating is already stored in the artifact
    rating: Dict[str, Any] | None = artifact.get("rating")
    if not rating:
        raise HTTPException(
            status_code=500,
            detail="The artifact rating system encountered an error while computing at least one metric.",
        )

    return JSONResponse(content=rating)
