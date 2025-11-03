# schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = '1.0.0'
    is_sensitive: bool = False


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_sensitive: Optional[bool] = None


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    version: str
    file_path: str
    file_size: int
    uploader_id: int
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    message: str
    model_id: int
    file_path: str
    file_size: int
