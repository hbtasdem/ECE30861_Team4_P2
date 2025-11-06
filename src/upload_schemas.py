# upload_schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class ModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = '1.0.0'
    is_sensitive: bool = False
    model_url: str  # URL to the model artifact
    artifact_type: str = 'model'  # Type: 'model', 'checkpoint', 'weights', etc.


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_sensitive: Optional[bool] = None
    model_url: Optional[str] = None
    artifact_type: Optional[str] = None


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    version: str
    model_url: str
    artifact_type: str
    uploader_id: int
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    message: str
    model_id: int
    model_url: str
    artifact_type: str
