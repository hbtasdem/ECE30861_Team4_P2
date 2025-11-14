"""File validation endpoints for Phase 4.

Implements:
- POST /api/models/validate: Validate file
- GET /api/models/validate/{file_id}: Get validation results
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from crud.upload.auth import get_current_user
from crud.upload.file_schemas import (
    FileValidationRequest,
    FileValidationResponse,
)
from crud.upload.file_validator import FileValidator
from src.database import get_db
from src.upload_manage import FileStorage

router = APIRouter(prefix="/api/models", tags=["validation"])
validator = FileValidator()

# Cache for validation results
_validation_cache: dict[str, FileValidationResponse] = {}


@router.post(
    "/validate",
    response_model=FileValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a file",
    description="Run comprehensive validation on an uploaded file"
)
async def validate_file(
    file_id: str = Query(..., description="File ID to validate"),
    scan_malware: bool = Query(default=True, description="Enable malware scanning"),
    strict_mime_type: bool = Query(default=False, description="Strict MIME type checking"),
    artifact_type: str = Query(default="default", description="Artifact type (model, dataset, code)"),
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileValidationResponse:
    """
    Validate a file with comprehensive checks.

    **Validations Performed:**
    - Filename safety (path traversal, special characters)
    - File size limits by artifact type
    - MIME type verification
    - Metadata extraction
    - Optional malware scanning

    **Query Parameters:**
    - `file_id`: File to validate
    - `scan_malware`: Enable malware scan (default: true)
    - `strict_mime_type`: Enforce allowed MIME types (default: false)
    - `artifact_type`: model/dataset/code (default: default)

    **Response:**
    - `overall_status`: valid/invalid/warnings
    - `validations`: List of validation results
    - `all_passed`: Boolean success indicator

    **Errors:**
    - 404: File not found
    - 422: File failed validation
    """
    try:
        # Check cache first
        if file_id in _validation_cache:
            return _validation_cache[file_id]

        # Retrieve file
        file_record = db.query(FileStorage).filter_by(id=file_id).first()
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {file_id} not found"
            )

        # Read file content from storage
        from crud.upload.file_storage_service import FileStorageService
        storage_service = FileStorageService(backend="local")
        file_content = await storage_service.retrieve_file(file_record.storage_location)

        if file_content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File content not found in storage"
            )

        # Perform validation
        validation_result = await validator.validate_file(
            file_id,
            file_content,
            file_record.filename,
            file_record.content_type,
            artifact_type,
            {
                "scan_malware": scan_malware,
                "strict_mime_type": strict_mime_type,
                "malware_scan_enabled": scan_malware,
            }
        )

        # Cache result
        _validation_cache[file_id] = validation_result

        # Mark file as verified if all passed
        if validation_result.all_passed:
            file_record.is_verified = True
            db.commit()

        return validation_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get(
    "/validate/{file_id}",
    response_model=FileValidationResponse,
    summary="Get validation results",
    description="Retrieve cached validation results for a file"
)
async def get_validation_results(
    file_id: str,
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FileValidationResponse:
    """
    Get cached validation results for a file.

    **Path Parameters:**
    - `file_id`: File ID

    **Response:**
    - Returns previously cached validation results
    - Checks file exists in database

    **Errors:**
    - 404: File or validation results not found
    """
    try:
        # Verify file exists
        file_record = db.query(FileStorage).filter_by(id=file_id).first()
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {file_id} not found"
            )

        # Check cache
        if file_id not in _validation_cache:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation results not found. Run validation first."
            )

        return _validation_cache[file_id]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve validation results: {str(e)}"
        )


@router.post(
    "/validate/clear-cache",
    status_code=status.HTTP_200_OK,
    summary="Clear validation cache",
    description="Clear cached validation results (admin only)"
)
async def clear_validation_cache(
    current_user: dict[str, object] = Depends(get_current_user)
) -> dict[str, str]:
    """
    Clear the validation cache.

    **Response:**
    - `message`: Confirmation message
    - `cleared_count`: Number of cached validations cleared

    **Errors:**
    - 403: User lacks admin permissions
    """
    try:
        # Check admin permission (simplified)
        if not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )

        cleared_count = len(_validation_cache)
        _validation_cache.clear()

        return {
            "message": "Validation cache cleared",
            "cleared_count": str(cleared_count)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )
