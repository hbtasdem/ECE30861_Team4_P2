# routes.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import json

from database import get_db
from upload.services.file_service import FileStorageService
from upload.repositories.model_repository import ModelRepository
from api_schemas import ModelCreate, UploadResponse
from auth import get_current_user


router = APIRouter(prefix="/api/models", tags=["models"])

file_service = FileStorageService()


@router.post("/upload", response_model=UploadResponse)
async def upload_model(
    file: UploadFile = File(..., description="Model zip file"),
    name: str = Form(..., description="Model name"),
    description: Optional[str] = Form(None),
    version: str = Form("1.0.0"),
    is_sensitive: bool = Form(False),
    metadata: Optional[str] = Form(None),  # JSON string of additional metadata
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a model zip file to the registry
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are allowed",
        )

    # Validate file size (e.g., 500MB limit)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

    # Create model data
    model_data = ModelCreate(
        name=name, description=description, version=version, is_sensitive=is_sensitive
    )

    # Save file to storage
    file_path, file_size = await file_service.save_upload_file(file)

    if file_size > MAX_FILE_SIZE:
        file_service.delete_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    # Create database record
    model_repo = ModelRepository(db)
    try:
        db_model = model_repo.create_model(
            model_data=model_data,
            file_path=file_path,
            file_size=file_size,
            uploader_id=current_user.id,
        )

        # Add metadata if provided
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
                model_repo.add_model_metadata(db_model.id, metadata_dict)
            except json.JSONDecodeError:
                # Continue without metadata if JSON is invalid
                pass

        return UploadResponse(
            message="Model uploaded successfully",
            model_id=db_model.id,
            file_path=db_model.file_path,
            file_size=db_model.file_size,
        )

    except Exception as e:
        # Clean up file if database operation fails
        file_service.delete_file(file_path)
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save model record: {str(e)}",
        )
