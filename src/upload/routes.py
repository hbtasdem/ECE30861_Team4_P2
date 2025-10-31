# routes.py# routes.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Formfrom fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from sqlalchemy.orm import Sessionfrom sqlalchemy.orm import Session

from typing import Optionalfrom typing import Optional

import jsonimport json



from database import get_dbfrom database import get_db

from upload.services.file_service import FileStorageServicefrom upload.services.file_service import FileStorageService

from upload.repositories.model_repository import ModelRepositoryfrom upload.repositories.model_repository import ModelRepository

from schemas import ModelCreate, UploadResponsefrom schemas import ModelCreate, UploadResponse

from auth import get_current_userfrom auth import get_current_user



router = APIRouter(prefix="/api/models", tags=["models"])router = APIRouter(prefix="/api/models", tags=["models"])



file_service = FileStorageService()file_service = FileStorageService()



@router.post("/upload", response_model=UploadResponse)

async def upload_model(@router.post("/upload", response_model=UploadResponse)

    file: UploadFile = File(..., description="Model zip file"),async def upload_model(

    name: str = Form(..., description="Model name"),    file: UploadFile = File(..., description="Model zip file"),

    description: Optional[str] = Form(None),    name: str = Form(..., description="Model name"),

    version: str = Form("1.0.0"),    description: Optional[str] = Form(None),

    is_sensitive: bool = Form(False),    version: str = Form("1.0.0"),

    metadata: Optional[str] = Form(None),  # JSON string of additional metadata    is_sensitive: bool = Form(False),

    current_user = Depends(get_current_user),    metadata: Optional[str] = Form(None),  # JSON string of additional metadata

    db: Session = Depends(get_db)    current_user=Depends(get_current_user),

):    db: Session = Depends(get_db),

    """):

    Upload a model zip file to the registry    """

    """    Upload a model zip file to the registry

    # Validate file type    """

    if not file.filename or not file.filename.lower().endswith('.zip'):    # Validate file type

        raise HTTPException(    if not file.filename or not file.filename.lower().endswith(".zip"):

            status_code=status.HTTP_400_BAD_REQUEST,        raise HTTPException(

            detail="Only .zip files are allowed"            status_code=status.HTTP_400_BAD_REQUEST,

        )            detail="Only .zip files are allowed",

            )

    # Validate file size (e.g., 500MB limit)

    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB    # Validate file size (e.g., 500MB limit)

        MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

    # Create model data

    model_data = ModelCreate(    # Create model data

        name=name,    model_data = ModelCreate(

        description=description,        name=name, description=description, version=version, is_sensitive=is_sensitive

        version=version,    )

        is_sensitive=is_sensitive

    )    # Save file to storage

        file_path, file_size = await file_service.save_upload_file(file)

    # Save file to storage

    file_path, file_size = await file_service.save_upload_file(file)    if file_size > MAX_FILE_SIZE:

            file_service.delete_file(file_path)

    if file_size > MAX_FILE_SIZE:        raise HTTPException(

        file_service.delete_file(file_path)            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,

        raise HTTPException(            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",

            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,        )

            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"

        )    # Create database record

        model_repo = ModelRepository(db)

    # Create database record    try:

    model_repo = ModelRepository(db)        db_model = model_repo.create_model(

    try:            model_data=model_data,

        db_model = model_repo.create_model(            file_path=file_path,

            model_data=model_data,            file_size=file_size,

            file_path=file_path,            uploader_id=current_user.id,

            file_size=file_size,        )

            uploader_id=current_user.id

        )        # Add metadata if provided

                if metadata:

        # Add metadata if provided            try:

        if metadata:                metadata_dict = json.loads(metadata)

            try:                model_repo.add_model_metadata(db_model.id, metadata_dict)

                metadata_dict = json.loads(metadata)            except json.JSONDecodeError:

                model_repo.add_model_metadata(db_model.id, metadata_dict)                # Continue without metadata if JSON is invalid

            except json.JSONDecodeError:                pass

                # Continue without metadata if JSON is invalid

                pass        return UploadResponse(

                    message="Model uploaded successfully",

        return UploadResponse(            model_id=db_model.id,

            message="Model uploaded successfully",            file_path=db_model.file_path,

            model_id=db_model.id,            file_size=db_model.file_size,

            file_path=db_model.file_path,        )

            file_size=db_model.file_size

        )    except Exception as e:

                # Clean up file if database operation fails

    except Exception as e:        file_service.delete_file(file_path)

        # Clean up file if database operation fails        import traceback

        file_service.delete_file(file_path)

        import traceback        traceback.print_exc()

        traceback.print_exc()        raise HTTPException(

        raise HTTPException(            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,            detail=f"Failed to save model record: {str(e)}",

            detail=f"Failed to save model record: {str(e)}"        )

        )
