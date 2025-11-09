"""Data validation schemas (Pydantic models) for model upload operations.

This module defines the structure and validation rules for data sent to and
returned from the model upload API endpoints. These schemas ensure that all
data conforms to the expected format before processing.

Key schemas:
- ModelCreate: Input data when registering a new model
- ModelResponse: Output data when retrieving model information
- UploadResponse: Confirmation returned after successful upload
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ModelCreate(BaseModel):
    """Schema for creating a new model."""

    name: str
    description: Optional[str] = None
    version: str = '1.0.0'
    is_sensitive: bool = False
    model_url: str  # URL to the model artifact
    artifact_type: str = 'model'  # Type: 'model', 'checkpoint', 'weights', etc.


class ModelUpdate(BaseModel):
    """Schema for updating an existing model."""

    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_sensitive: Optional[bool] = None
    model_url: Optional[str] = None
    artifact_type: Optional[str] = None


class ModelResponse(BaseModel):
    """Schema for returning model data in responses."""

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
    """Schema for upload endpoint response."""

    message: str
    model_id: int
    model_url: str
    artifact_type: str


# NEW: Authentication schemas per OpenAPI spec


class UserSchema(BaseModel):
    """User information schema per OpenAPI spec."""

    name: str  # NEW: Username or email
    is_admin: bool = False  # NEW: Admin flag


class UserAuthenticationInfo(BaseModel):
    """Authentication secret schema per OpenAPI spec."""

    password: str  # NEW: User password


class AuthRequest(BaseModel):
    """Authentication request per OpenAPI AuthenticationRequest schema."""

    user: UserSchema  # NEW: User credentials
    secret: UserAuthenticationInfo  # NEW: Authentication secret


class UserRegistrationRequest(AuthRequest):
    """User registration request extends auth request."""

    pass


class AuthResponse(BaseModel):
    """Authentication response with token per OpenAPI AuthenticationToken schema."""

    token: str  # NEW: Bearer token for authenticated requests
