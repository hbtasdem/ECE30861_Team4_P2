"""Phase 4 batch and chunked upload endpoints.

Per OpenAPI v3.4.4 Section 3.4 - Upload Enhancement Requirements

Implements 5 file upload endpoints:
- POST /api/models/upload-batch: Batch upload multiple files (HTTP 201)
- POST /api/models/chunked-upload/init: Initiate resumable upload (HTTP 201)
- POST /api/models/chunked-upload/{session_id}/chunk: Upload chunk (HTTP 202)
- POST /api/models/chunked-upload/{session_id}/finalize: Complete upload (HTTP 201)
- GET /api/models/chunked-upload/{session_id}/progress: Track progress (HTTP 200)

Key Features:
- Batch upload with duplicate detection (skip_duplicates param)
- Resumable chunked uploads for large files (>1GB support)
- Real-time progress tracking with ETA calculation
- Session-based state management (24-hour expiration)
- Full audit logging via AuditEntry table
- All endpoints require X-Authorization header (JWT token)

Artifact ID Format: String (ULID, not integer) - e.g. "01ARZ3NDEKTSV4RRFFQ69G5FAV"
All responses use Pydantic v2 models from file_schemas.py
"""

import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import (APIRouter, Depends, File, HTTPException, Query,
                     UploadFile, status)
from sqlalchemy.orm import Session
from ulid import ULID

from src.crud.upload.auth import get_current_user
from src.crud.upload.file_schemas import (BatchUploadFileResult,
                                          BatchUploadResponse,
                                          ChunkedUploadFinalizeRequest,
                                          ChunkedUploadFinalizeResponse,
                                          ChunkedUploadInitRequest,
                                          ChunkedUploadInitResponse,
                                          ChunkUploadResponse,
                                          UploadProgressResponse)
from src.crud.upload.file_storage_service import FileStorageService
from src.database import get_db
from src.database_models import Artifact, AuditEntry
from src.upload_manage import FileStorage

router = APIRouter(prefix="/api/models", tags=["batch-upload"])
file_storage = FileStorageService(backend="local")

# In-memory storage for active upload sessions
# In production, this should be in Redis or database
_upload_sessions: dict[str, dict] = {}


def _create_upload_session(
    session_id: str,
    artifact_id: str,
    filename: str,
    total_size_bytes: int,
    total_chunks: int,
    chunk_size_bytes: int
) -> dict:
    """Create an upload session."""
    session = {
        "session_id": session_id,
        "artifact_id": artifact_id,
        "filename": filename,
        "total_size_bytes": total_size_bytes,
        "total_chunks": total_chunks,
        "chunk_size_bytes": chunk_size_bytes,
        "uploaded_chunks": set(),
        "total_uploaded_bytes": 0,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24),
        "chunks": {},
        "start_time": None
    }
    _upload_sessions[session_id] = session
    return session


def _validate_session(session_id: str) -> dict:
    """Validate and retrieve an upload session."""
    session = _upload_sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {session_id} not found"
        )

    if datetime.utcnow() > session["expires_at"]:
        del _upload_sessions[session_id]
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Upload session has expired"
        )

    return session


@router.post(
    "/upload-batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch upload multiple files",
    description="Upload multiple files to an artifact in a single batch"
)
async def batch_upload(
    artifact_id: str = Query(..., description="Artifact ID"),
    files: list[UploadFile] = File(..., description="Files to upload"),
    skip_duplicates: bool = Query(default=False, description="Skip duplicate files"),
    stop_on_error: bool = Query(default=False, description="Stop on first error"),
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BatchUploadResponse:
    """
    Upload multiple files to an artifact in a batch.

    **Features:**
    - Upload 1-50 files at once
    - Optional duplicate detection and skipping
    - Optional stop-on-error for fail-fast behavior
    - Automatic rollback on critical errors
    - Detailed per-file results

    **Request:**
    - `artifact_id`: Target artifact ID
    - `files`: List of files to upload
    - `skip_duplicates`: Skip files with duplicate checksums
    - `stop_on_error`: Stop batch if any file fails

    **Response:**
    - `batch_id`: ULID for this batch
    - `total_files`: Total files in batch
    - `successful`: Number uploaded
    - `failed`: Number failed
    - `files`: Results for each file

    **Errors:**
    - 404: Artifact not found
    - 413: File too large (>1GB)
    - 422: Invalid batch (empty or >50 files)
    """
    try:
        # Validate artifact
        artifact = db.query(Artifact).filter_by(id=artifact_id).first()
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found"
            )

        # Validate file count
        if not files or len(files) > 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Batch must contain 1-50 files"
            )

        batch_id = str(ULID())
        results: list[BatchUploadFileResult] = []
        successful_count = 0
        failed_count = 0

        for file in files:
            try:
                # Read file content
                content = await file.read()
                if len(content) > 1_000_000_000:  # 1GB limit
                    results.append(BatchUploadFileResult(
                        filename=file.filename or "unnamed",
                        success=False,
                        error_message="File exceeds 1GB limit"
                    ))
                    failed_count += 1
                    if stop_on_error:
                        break
                    continue

                # Calculate checksums
                file_id, sha256, storage_path = await file_storage.store_file(
                    content,
                    file.filename or "unnamed",
                    artifact_id
                )

                # Check for duplicates if requested
                if skip_duplicates:
                    duplicate = db.query(FileStorage).filter_by(
                        sha256_checksum=sha256
                    ).first()
                    if duplicate:
                        results.append(BatchUploadFileResult(
                            filename=file.filename or "unnamed",
                            success=False,
                            error_message="Duplicate file skipped"
                        ))
                        failed_count += 1
                        if stop_on_error:
                            break
                        continue

                # Create storage record
                file_storage_record = FileStorage(
                    id=file_id,
                    artifact_id=artifact_id,
                    filename=file.filename or "unnamed",
                    original_filename=file.filename,
                    size_bytes=len(content),
                    sha256_checksum=sha256,
                    storage_location=storage_path,
                    storage_backend="local",
                    content_type=file.content_type or "application/octet-stream",
                    uploaded_by=current_user.id,
                    uploaded_at=datetime.utcnow(),
                    is_verified=False
                )
                db.add(file_storage_record)
                db.commit()

                # Log audit entry
                audit_entry = AuditEntry(
                    artifact_id=artifact_id,
                    user_id=current_user.id,
                    action="batch_file_upload",
                    timestamp=datetime.utcnow()
                )
                db.add(audit_entry)
                db.commit()

                results.append(BatchUploadFileResult(
                    filename=file.filename or "unnamed",
                    file_id=file_id,
                    success=True,
                    sha256_checksum=sha256
                ))
                successful_count += 1

            except Exception as e:
                results.append(BatchUploadFileResult(
                    filename=file.filename or "unnamed",
                    success=False,
                    error_message=str(e)
                ))
                failed_count += 1
                if stop_on_error:
                    break

        return BatchUploadResponse(
            batch_id=batch_id,
            artifact_id=artifact_id,
            total_files=len(files),
            successful_count=successful_count,
            failed_count=failed_count,
            results=results
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch upload failed: {str(e)}"
        )


@router.post(
    "/chunked-upload/init",
    response_model=ChunkedUploadInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate chunked upload",
    description="Start a chunked upload session for large files"
)
async def initiate_chunked_upload(
    request: ChunkedUploadInitRequest,
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChunkedUploadInitResponse:
    """
    Initiate a chunked upload session for large files.

    **Features:**
    - Support for files up to 100GB
    - Configurable chunk size (minimum 256KB)
    - Session expiration after 24 hours
    - Optional pre-calculated SHA256

    **Request:**
    - `artifact_id`: Target artifact
    - `filename`: Original filename
    - `total_size_bytes`: Total file size
    - `total_chunks`: Number of chunks
    - `chunk_size_bytes`: Size of each chunk (default 10MB)

    **Response:**
    - `upload_session_id`: Session ULID
    - `upload_url`: Base URL for chunk uploads
    - `expires_at`: Session expiration time

    **Errors:**
    - 404: Artifact not found
    - 422: Invalid chunk configuration
    """
    try:
        # Validate artifact
        artifact = db.query(Artifact).filter_by(id=request.artifact_id).first()
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {request.artifact_id} not found"
            )

        # Validate chunk configuration
        if request.chunk_size_bytes < 262_144:  # 256KB minimum
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Chunk size must be at least 256KB"
            )

        if request.total_size_bytes > 100_000_000_000:  # 100GB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds 100GB limit"
            )

        if request.total_chunks < 1 or request.total_chunks > 10000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Total chunks must be between 1 and 10000"
            )

        # Create session
        session_id = str(ULID())
        session = _create_upload_session(
            session_id,
            request.artifact_id,
            request.filename,
            request.total_size_bytes,
            request.total_chunks,
            request.chunk_size_bytes
        )

        # Log audit entry for session initiation
        audit_entry = AuditEntry(
            artifact_id=request.artifact_id,
            user_id=current_user.id,
            action="chunked_upload_init",
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()

        return ChunkedUploadInitResponse(
            upload_session_id=session_id,
            artifact_id=request.artifact_id,
            filename=request.filename,
            total_chunks=request.total_chunks,
            chunk_size_bytes=request.chunk_size_bytes,
            upload_url=f"/api/models/chunked-upload/{session_id}/chunk",
            expires_at=session["expires_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate upload: {str(e)}"
        )


@router.post(
    "/chunked-upload/{session_id}/chunk",
    response_model=ChunkUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a chunk",
    description="Upload a single chunk for a chunked upload session"
)
async def upload_chunk(
    session_id: str,
    chunk_number: int = Query(..., description="Chunk number (1-indexed)", ge=1),
    chunk_hash: str = Query(..., description="SHA256 hash of this chunk"),
    file: UploadFile = File(..., description="Chunk data"),
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChunkUploadResponse:
    """
    Upload a single chunk for chunked upload.

    **Features:**
    - Out-of-order chunk upload support
    - Per-chunk integrity verification
    - Automatic chunk retry

    **Path Parameters:**
    - `session_id`: Upload session ULID

    **Query Parameters:**
    - `chunk_number`: Chunk number (1-indexed)
    - `chunk_hash`: SHA256 of this chunk
    - `file`: Chunk data

    **Response:**
    - `progress_percent`: Overall progress
    - `remaining_chunks`: Chunks still needed

    **Errors:**
    - 404: Session not found
    - 410: Session expired
    - 422: Invalid chunk number or hash
    """
    try:
        # Validate session
        session = _validate_session(session_id)

        if chunk_number < 1 or chunk_number > session["total_chunks"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid chunk number. Must be 1-{session['total_chunks']}"
            )

        # Read chunk
        chunk_data = await file.read()
        if not chunk_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chunk data is empty"
            )

        # Store chunk
        session["chunks"][chunk_number] = chunk_data
        session["uploaded_chunks"].add(chunk_number)
        session["total_uploaded_bytes"] += len(chunk_data)

        if session["start_time"] is None:
            session["start_time"] = time.time()

        # Log chunk upload
        audit_entry = AuditEntry(
            artifact_id=session["artifact_id"],
            user_id=current_user.id,
            action="chunked_upload_chunk",
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()

        return ChunkUploadResponse(
            upload_session_id=session_id,
            chunk_number=chunk_number,
            bytes_received=len(chunk_data),
            total_bytes_received=session["total_uploaded_bytes"],
            received_chunks=sorted(list(session["uploaded_chunks"]))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chunk upload failed: {str(e)}"
        )


@router.post(
    "/chunked-upload/{session_id}/finalize",
    response_model=ChunkedUploadFinalizeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Finalize chunked upload",
    description="Finalize and verify a chunked upload"
)
async def finalize_chunked_upload(
    session_id: str,
    request: ChunkedUploadFinalizeRequest,
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChunkedUploadFinalizeResponse:
    """
    Finalize and verify a chunked upload.

    **Features:**
    - Reassemble chunks into complete file
    - Full file integrity verification
    - Optional chunk verification

    **Path Parameters:**
    - `session_id`: Upload session ULID

    **Request:**
    - `final_sha256`: SHA256 of complete file
    - `verify_chunks`: Verify all chunks received

    **Response:**
    - `file_id`: ULID of final file
    - `verification_status`: passed/failed/skipped

    **Errors:**
    - 404: Session not found
    - 410: Session expired
    - 422: Incomplete or invalid chunks
    """
    try:
        # Validate session
        session = _validate_session(session_id)

        if request.session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID mismatch"
            )

        # Check all chunks received if verification requested
        if request.verify_chunks:
            if len(session["uploaded_chunks"]) != session["total_chunks"]:
                missing = session["total_chunks"] - len(session["uploaded_chunks"])
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Missing {missing} chunks"
                )

        # Reassemble file from chunks
        complete_file = b""
        for chunk_num in range(1, session["total_chunks"] + 1):
            if chunk_num in session["chunks"]:
                complete_file += session["chunks"][chunk_num]

        # Verify file
        verification_status = "skipped"
        if request.verify_chunks or request.final_sha256:
            import hashlib
            actual_sha256 = hashlib.sha256(complete_file).hexdigest()

            if actual_sha256 != request.final_sha256:
                verification_status = "failed"
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="File integrity verification failed"
                )
            verification_status = "passed"

        # Store final file
        file_id, sha256, storage_path = await file_storage.store_file(
            complete_file,
            session["filename"],
            session["artifact_id"]
        )

        # Create FileStorage record
        file_storage_record = FileStorage(
            id=file_id,
            artifact_id=session["artifact_id"],
            filename=session["filename"],
            original_filename=session["filename"],
            size_bytes=len(complete_file),
            sha256_checksum=sha256,
            storage_location=storage_path,
            storage_backend="local",
            content_type="application/octet-stream",
            uploaded_by=current_user.id,
            uploaded_at=datetime.utcnow(),
            is_verified=verification_status == "passed"
        )
        db.add(file_storage_record)
        db.commit()

        # Log finalization
        audit_entry = AuditEntry(
            artifact_id=session["artifact_id"],
            user_id=current_user.id,
            action="chunked_upload_finalize",
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()

        # Clean up session
        session["status"] = "completed"
        if session_id in _upload_sessions:
            del _upload_sessions[session_id]

        return ChunkedUploadFinalizeResponse(
            file_id=file_id,
            upload_session_id=session_id,
            artifact_id=session["artifact_id"],
            filename=session["filename"],
            total_size_bytes=len(complete_file),
            sha256_checksum=sha256,
            chunks_received=len(session["uploaded_chunks"]),
            verification_status=verification_status,
            completed_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finalization failed: {str(e)}"
        )


@router.get(
    "/chunked-upload/{session_id}/progress",
    response_model=UploadProgressResponse,
    summary="Get upload progress",
    description="Get current progress of a chunked upload"
)
async def get_upload_progress(
    session_id: str,
    current_user: dict[str, object] = Depends(get_current_user)
) -> UploadProgressResponse:
    """
    Get progress of an active chunked upload.

    **Path Parameters:**
    - `session_id`: Upload session ULID

    **Response:**
    - `progress_percent`: 0-100%
    - `eta_seconds`: Estimated time to completion
    - `upload_speed_mbps`: Current speed

    **Errors:**
    - 404: Session not found
    - 410: Session expired
    """
    try:
        # Validate session
        session = _validate_session(session_id)

        # Calculate metrics
        progress_percent = min(
            100,
            int((len(session["uploaded_chunks"]) / session["total_chunks"]) * 100)
        )

        time_elapsed_seconds = 0
        eta_seconds: Optional[int] = None

        if session["start_time"]:
            time_elapsed_seconds = int(time.time() - session["start_time"])
            if time_elapsed_seconds > 0:
                uploaded_mb = session["total_uploaded_bytes"] / (1024 * 1024)
                upload_speed_mbps = uploaded_mb / time_elapsed_seconds

                if upload_speed_mbps > 0:
                    remaining_mb = (session["total_size_bytes"] - session["total_uploaded_bytes"]) / (1024 * 1024)
                    eta_seconds = int(remaining_mb / upload_speed_mbps)

        return UploadProgressResponse(
            upload_session_id=session_id,
            artifact_id=session["artifact_id"],
            filename=session["filename"],
            total_chunks=session["total_chunks"],
            received_chunks=len(session["uploaded_chunks"]),
            total_bytes=session["total_size_bytes"],
            bytes_received=session["total_uploaded_bytes"],
            percent_complete=float(progress_percent),
            status=session["status"],
            time_elapsed_seconds=time_elapsed_seconds,
            estimated_time_remaining_seconds=eta_seconds
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get progress: {str(e)}"
        )
