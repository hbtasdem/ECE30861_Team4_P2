# /artifact/model/{artifact_id}/rate

import json
from typing import Any, Optional, Tuple

import boto3
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

# from src.crud.upload.auth import get_current_user
from src.main import calculate_all_scores

router = APIRouter()

BUCKET_NAME = "phase2-s3-bucket"
s3_client = boto3.client("s3")


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
    # Per OpenAPI spec: All endpoints require X-Authorization header
    if not x_authorization:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    # get ModelRating from s3 bucket
    key = f"rating/{artifact_id}.rate.json"
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
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


# ---------------------------------------------
# Rate functions called on upload to rate model
# ---------------------------------------------

def findCodeAndDataset(mode_url: str) -> Tuple[str, str]:
    """
    Use ai to find code and dataset associated with hf model

    Parameters
    ----------
    model_url: str given in upload endpoint by user

    Returns
    ----------
    (code_url: str, dataset_url: str)
    """
    return "", ""


def rateOnUpload(model_url: str, artifact_id: str) -> bool:
    """
    Calculate the rating for a model, store it, return if ingestible

    Parameters
    ----------
    model_url: str given in upload endpoint by user

    Returns
    ----------
    boolean: True if model, ingestible, False if not
    """
    # Find dataset and code url for model
    dataset_url, code_url = findCodeAndDataset(model_url)
    # calculate metrics
    rating = calculate_all_scores(code_url, dataset_url, model_url, set(), set())
    # check if ingestible comment out until rate works
    # for key, value in rating.items():
    #     # skip non-score items
    #     if (key == "name") or (key == "category") or key.endswith("latency"):
    #         continue
    #     # handle score dict
    #     if isinstance(value, dict):
    #         for val in value.values():
    #             if val < 0.5:
    #                 return False
    #     elif value < 0.5:
    #         return False

    # if ingestible: store metrics
    try:
        key = f"rating/{artifact_id}.rate.json"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=json.dumps(rating))
    except Exception as e:
        raise HTTPException(status_code=424, detail=f"Error rating model: {str(e)}")

    return True
