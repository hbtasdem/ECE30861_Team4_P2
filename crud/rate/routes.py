# /artifact/model/{id}/rate
# This is NOT CONNECTED TO A REAL DATABASE, only example hardcoded for now
# Example usage:
# In terminal: uvicorn crud.app:app --reload --host 127.0.0.1 --port 8000
# In browser go to: http://127.0.0.1:8000/artifact/model/1234567890/rate
# The example python dict has an example Artifact with ID 1234567890

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Use example python dict for database for now
from crud.rate.dict_artifacts_db import artifacts_db

router = APIRouter()


@router.get("/artifact/model/{artifact_id}/rate")
async def get_model_rating(artifact_id: str) -> JSONResponse:
    """
    Return the stored ModelRating for a given artifact ID.
    """
    if not artifact_id or not artifact_id.isdigit():
        raise HTTPException(
            status_code=400,
            detail="There is missing field(s) in the artifact_id or it is formed improperly, or is invalid."
        )
    # TODO add authentication check
    # if not valid authentication token
    #   raise HTTPException(status_code=403,
    #       detail="Authentication failed due to invalid or missing AuthenticationToken.")

    artifact = artifacts_db.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")

    # The rating is already stored in the artifact
    rating: Dict[str, Any] | None = artifact.get("rating")
    if not rating:
        raise HTTPException(
            status_code=500,
            detail="The artifact rating system encountered an error while computing at least one metric."
        )

    return JSONResponse(content=rating)
