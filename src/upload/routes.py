# routes.py
import json
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.orm import Session

from src.auth import get_current_user  # noqa: E402
from src.database import get_db  # noqa: E402
from src.upload.repositories.model_repository import ModelRepository  # noqa: E402
from src.upload.services.file_service import FileStorageService  # noqa: E402
from src.upload_schemas import ModelCreate, UploadResponse  # noqa: E402

router = APIRouter(prefix="/api/models", tags=["models"])
file_service = FileStorageService()


@router.post("/upload", response_model=UploadResponse)
async def upload_model(
    name: str = Form(..., description="Model name"),
    model_url: str = Form(..., description="URL to model artifact"),
    description: Optional[str] = Form(None),
    version: str = Form("1.0.0"),
    artifact_type: str = Form("model"),
    is_sensitive: bool = Form(False),
    metadata: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
                model_repo.add_model_metadata(db_model.id, metadata_dict)
            except json.JSONDecodeError:
                pass

        return UploadResponse(
            message="Model registered successfully",
            model_id=db_model.id,
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
):
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

    return {"download_url": model.model_url}
