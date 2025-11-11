# routes.py
import json
from typing import Any

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

S3_BUCKET = "phase2-s3-bucket"  # replace with your bucket name
s3_client = boto3.client("s3")

router = APIRouter()


# Schemas
class ArtifactData(BaseModel):  # type: ignore[misc]
    url: str
    download_url: str = "example"


class ArtifactMetadata(BaseModel):  # type: ignore[misc]
    name: str = "example"
    id: str
    type: str


class Artifact(BaseModel):  # type: ignore[misc]
    metadata: ArtifactMetadata
    data: ArtifactData


# POST /artifact/{artifact_type}
@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def create_artifact(artifact_type: str, artifact: ArtifactData) -> Artifact:
    artifact_id = "12345"  # for demo, fixed ID
    metadata = ArtifactMetadata(id=artifact_id, type=artifact_type)
    full_artifact = Artifact(metadata=metadata, data=artifact)

    # Store artifact in S3
    key = f"{artifact_type}/{artifact_id}.json"
    s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=full_artifact.json())

    # Return artifact with only ID and type
    return full_artifact


# GET /artifacts/{artifact_type}/{id}
@router.get("/artifacts/{artifact_type}/{artifact_id}", response_model=Artifact)
def get_artifact(artifact_type: str, artifact_id: str) -> Any:
    key = f"{artifact_type}/{artifact_id}.json"
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        artifact_data = obj["Body"].read().decode("utf-8")
        return json.loads(artifact_data)
    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Artifact not found")
