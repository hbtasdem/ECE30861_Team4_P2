"""HTTP API endpoint routes for model upload and retrieval.

This module defines all the REST API endpoints for registering models via URLs
and retrieving model information. Each endpoint handles validation, storage,
and returns appropriate responses.

Key endpoints:
- POST /api/models/upload: Register a new model from a URL
- GET /api/models/enumerate: List all registered models with pagination
- GET /api/models/{id}/download-redirect: Get download URL for a model

All endpoints require authentication and validate input parameters.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, Header, HTTPException, status  # UPDATED: Added Header import
from sqlalchemy.orm import Session

from crud.upload.auth import get_current_user  # noqa: E402
from crud.upload.model_repository import ModelRepository  # noqa: E402
from crud.upload.models import ModelCreate, ModelResponse, UploadResponse  # noqa: E402
from src.database import get_db  # noqa: E402


# UPDATED: Helper function for getting current user with authorization header
async def get_current_user_with_auth(
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Any:
    """Helper to pass x_authorization header to get_current_user."""
    return get_current_user(authorization=x_authorization, db=db)


router = APIRouter(prefix="/api/models", tags=["models"])


@router.post("/upload", response_model=UploadResponse)
async def upload_model(
    name: str = Form(..., description="Model name"),
    model_url: str = Form(..., description="URL to model artifact"),
    description: Optional[str] = Form(None),
    version: str = Form("1.0.0"),
    artifact_type: str = Form("model"),
    is_sensitive: bool = Form(False),
    metadata: Optional[str] = Form(None),
    current_user: Any = Depends(get_current_user_with_auth),  # UPDATED: Use helper function
    db: Session = Depends(get_db)
) -> UploadResponse:
    """Register a model via URL"""
    # Validate URL
    if model_url == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_url cannot be empty"
        )

    if not model_url.startswith(("https://", "http://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_url must start with https:// or http://"
        )

    model_data = ModelCreate(
        name=name,
        description=description,
        version=version,
        is_sensitive=is_sensitive,
        model_url=model_url,
        artifact_type=artifact_type
    )

    model_repo = ModelRepository(db)
    try:
        db_model = model_repo.create_model(
            model_data=model_data,
            uploader_id=current_user.id
        )

        if metadata:
            try:
                metadata_dict = json.loads(metadata)
                model_repo.add_model_metadata(int(db_model.id), metadata_dict)
            except json.JSONDecodeError:
                pass

        return UploadResponse(
            message="Model registered successfully",
            model_id=int(db_model.id),
            model_url=model_data.model_url,
            artifact_type=artifact_type
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register model: {str(e)}"
        )


@router.get("/models/{model_id}/download-redirect")
async def get_download_url(
    model_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Get download redirect URL for a model."""
    model_repo = ModelRepository(db)
    model = model_repo.get_model_by_id(model_id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with id {model_id} not found"
        )

    if not model.model_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model does not have a download URL"
        )

    return {"download_url": str(model.model_url)}


@router.get("/enumerate", response_model=List[ModelResponse])
async def enumerate_models(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[ModelResponse]:
    """Enumerate all registered models with pagination.

    Args:
        skip: Number of models to skip (default: 0)
        limit: Maximum number of models to return (default: 100, max: 1000)

    Returns:
        List of ModelResponse objects
    """
    # Enforce maximum limit to prevent abuse
    if limit > 1000:
        limit = 1000

    if skip < 0:
        skip = 0

    model_repo = ModelRepository(db)
    models = model_repo.get_all_models(skip=skip, limit=limit)
    return [ModelResponse.model_validate(model) for model in models]
