# /artifact/model/{id}/rate

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
    artifact_id: str, x_authorization: Optional[str] = Header(None)
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


# -------- Manual test before integration ------------
# @router.post("/artifact/model/{artifact_id}/rate/upload")
# async def upload_model_rating(
#     artifact_id: str, rating: Dict[str, Any] = Body(...)
# ) -> Dict[str, str]:
#     """
#     Upload a ModelRating JSON to S3 under rating/{artifact_id}.rate.json
#     """
#     s3_client = boto3.client("s3")
#     try:
#         key = f"rating/{artifact_id}.rate.json"
#         s3_client.put_object(
#             Bucket="phase2-s3-bucket", Key=key, Body=json.dumps(rating)
#         )
#         return {"message": f"ModelRating uploaded successfully for {artifact_id}"}
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Error uploading ModelRating: {str(e)}"
#         )


"""
Commands to test
curl -X POST "http://3.140.239.181:8000/artifact/model/01/rate/upload" \
-H "Content-Type: application/json" \
-d '{
  "name": "bert-base-uncased",
  "category": "model",
  "net_score": 0.95,
  "net_score_latency": 0.02,
  "ramp_up_time": 0.8,
  "ramp_up_time_latency": 0.01,
  "bus_factor": 0.9,
  "bus_factor_latency": 0.01,
  "performance_claims": 0.92,
  "performance_claims_latency": 0.02,
  "license": 1.0,
  "license_latency": 0.01,
  "dataset_and_code_score": 0.88,
  "dataset_and_code_score_latency": 0.01,
  "dataset_quality": 0.9,
  "dataset_quality_latency": 0.01,
  "code_quality": 0.93,
  "code_quality_latency": 0.01,
  "reproducibility": 0.94,
  "reproducibility_latency": 0.01,
  "reviewedness": 0.85,
  "reviewedness_latency": 0.01,
  "tree_score": 0.9,
  "tree_score_latency": 0.01,
  "size_score": {
    "raspberry_pi": 0.8,
    "jetson_nano": 0.85,
    "desktop_pc": 0.9,
    "aws_server": 0.95
  },
  "size_score_latency": 0.01
}'


curl -X GET "http://3.140.239.181:8000/artifact/model/01/rate"
"""
