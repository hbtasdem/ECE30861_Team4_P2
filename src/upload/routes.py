# routes.py
"""Upload endpoint for registering model URLs in the registry."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.database import get_db
from src.models import User
from src.upload_schemas import ModelCreate, UploadResponse
from src.upload.repositories.model_repository import ModelRepository

router = APIRouter(prefix="/api/models", tags=["models"])


@router.post("/upload", response_model=UploadResponse)
def upload_model(
    name: str = Form(..., description="Model name"),
    model_url: str = Form(..., description="URL to model artifact"),
    description: Optional[str] = Form(None),
    version: str = Form("1.0.0"),
    artifact_type: str = Form("model", description="Type of artifact"),
    is_sensitive: bool = Form(False),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Register a model by its URL in the model registry.

    Args:
        name: Name of the model
        model_url: URL where the model artifact is located
        description: Optional description of the model
        version: Version string (default: 1.0.0)
        artifact_type: Type of artifact (model, checkpoint, weights, etc.)
        is_sensitive: Whether the model contains sensitive data
        metadata: Optional JSON metadata
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        UploadResponse with model_id, URL, and artifact type

    Raises:
        400: If URL is invalid or empty
        422: If required fields are missing
        500: If database save fails
    """
    # Validate URL format
    if not model_url or not model_url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model URL cannot be empty"
        )

    # Basic URL validation
    if not (model_url.startswith('http://') or model_url.startswith('https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model URL must start with http:// or https://"
        )

    # Create model data
    model_data = ModelCreate(
        name=name,
        description=description,
        version=version,
        is_sensitive=is_sensitive,
        model_url=model_url,
        artifact_type=artifact_type
    )

    # Save to database
    model_repo = ModelRepository(db)
    try:
        db_model = model_repo.create_model(
            model_data=model_data,
            uploader_id=current_user.id
        )

        # Add metadata if provided
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
                model_repo.add_model_metadata(db_model.id, metadata_dict)
            except json.JSONDecodeError:
                pass  # Silently ignore invalid JSON

        return UploadResponse(
            message="Model registered successfully",
            model_id=db_model.id,
            model_url=db_model.model_url,
            artifact_type=db_model.artifact_type
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register model: {str(e)}"
        )


@router.get("/models/{model_id}/download-redirect")
def get_model_download_url(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get the direct download URL for a model artifact.

    Args:
        model_id: ID of the model
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        Dictionary with the model URL for downloading

    Raises:
        404: If model not found
    """
    model_repo = ModelRepository(db)
    db_model = model_repo.get_model_by_id(model_id)

    if not db_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    return {
        "model_id": db_model.id,
        "name": db_model.name,
        "download_url": db_model.model_url,
        "artifact_type": db_model.artifact_type,
        "version": db_model.version
    }
