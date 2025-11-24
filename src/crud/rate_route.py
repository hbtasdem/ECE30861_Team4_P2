# /artifact/model/{artifact_id}/rate

import json
from typing import Any, Optional

import boto3
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

# from src.crud.upload.auth import get_current_user

router = APIRouter()


# -----------ModelRating schema-----------
# this this into schemas file in integration!
class rating_sizescore(BaseModel):  # type: ignore[misc]
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float


class ModelRating(BaseModel):  # type: ignore[misc]
    name: str
    category: str
    net_score: float
    net_score_latency: float
    ramp_up_time: float
    ramp_up_time_latency: float
    bus_factor: float
    bus_factor_latency: float
    performance_claims: float
    performance_claims_latency: float
    license: float
    license_latency: float
    dataset_and_code_score: float
    dataset_and_code_score_latency: float
    dataset_quality: float
    dataset_quality_latency: float
    code_quality: float
    code_quality_latency: float
    reproducibility: float
    reproducibility_latency: float
    reviewedness: float
    reviewedness_latency: float
    tree_score: float
    tree_score_latency: float
    size_score: rating_sizescore
    size_score_latency: float


# ---------------------------------------------


@router.get("/artifact/model/{artifact_id}/rate")
async def get_model_rating(
    artifact_id: str,
    x_authorization: Optional[str] = Header(None)
) -> Any:
    """
    Return the stored ModelRating for a given artifact ID.
    """
    if not artifact_id:
        raise HTTPException(
            status_code=400,
            detail="There is missing field(s) in the artifact_id or it is formed improperly, or is invalid.",
        )

    # Validate authentication token
    # if not x_authorization:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Authentication failed due to invalid or missing AuthenticationToken.",
    #     )

    # try:
    #     get_current_user(x_authorization, db=None)
    # except HTTPException:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Authentication failed due to invalid or missing AuthenticationToken.",
    #     )

    key = f"rating/{artifact_id}.rate.json"
    s3_client = boto3.client("s3")

    # get ModelRating from s3 bucket
    try:
        obj = s3_client.get_object(Bucket="phase2-s3-bucket", Key=key)
        model_rating_obj = obj["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")

    # check ModelRating is valid
    try:
        model_rating = json.loads(model_rating_obj)
        model_rating = ModelRating(**model_rating)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The artifact rating system encountered an error while computing at least one metric.",
        )

    return model_rating
