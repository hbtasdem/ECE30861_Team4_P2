# routes.py
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from schemas import ModelCreate, UploadResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from upload.repositories.model_repository import ModelRepository
from upload.services.file_service import FileStorageService

router = APIRouter(prefix="/api/models", tags=["models"])
file_service = FileStorageService()


@router.post("/upload", response_model=UploadResponse)
async def upload_model(
    file: UploadFile = File(..., description="Model zip file"),
    name: str = Form(..., description="Model name"),
    description: Optional[str] = Form(None),
    version: str = Form("1.0.0"),
    is_sensitive: bool = Form(False),
    metadata: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a model zip file to the registry"""
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are allowed"
        )

    MAX_FILE_SIZE = 500 * 1024 * 1024

    model_data = ModelCreate(
        name=name,
        description=description,
        version=version,
        is_sensitive=is_sensitive
    )

    file_path, file_size = await file_service.save_upload_file(file)

    if file_size > MAX_FILE_SIZE:
        file_service.delete_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    model_repo = ModelRepository(db)
    try:
        db_model = model_repo.create_model(
            model_data=model_data,
            file_path=file_path,
            file_size=file_size,
            uploader_id=current_user.id
        )

        if metadata:
            try:
                metadata_dict = json.loads(metadata)
                model_repo.add_model_metadata(db_model.id, metadata_dict)
            except json.JSONDecodeError:
                pass

        return UploadResponse(
            message="Model uploaded successfully",
            model_id=db_model.id,
            file_path=db_model.file_path,
            file_size=db_model.file_size
        )

    except Exception as e:
        file_service.delete_file(file_path)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save model record: {str(e)}"
        )
