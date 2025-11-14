"""Phase 4 file upload and management schemas.

Per OpenAPI v3.4.4 - File Upload & Management Endpoints
Implements Pydantic v2 models for:
- POST /api/models/upload-file: Single file upload (201 Created)
- POST /api/models/upload-batch: Batch file upload (201 Created)
- POST /api/models/chunked-upload/init: Initiate chunked (201 Created)
- POST /api/models/chunked-upload/{id}/chunk: Upload chunk (202 Accepted)
- POST /api/models/chunked-upload/{id}/finalize: Finalize upload (201 Created)
- GET /api/models/chunked-upload/{id}/progress: Get progress (200 OK)
- POST /api/models/check-duplicate: Duplicate detection (200 OK)
- POST /api/models/validate: File validation (200 OK)

Artifact IDs are strings (ULIDs), not integers.
All file operations require X-Authorization header (JWT token).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ============================================================================
# FILE UPLOAD SCHEMAS
# ============================================================================


class FileUploadResponse(BaseModel):
    """Response model for single file upload."""

    file_id: str = Field(..., description="ULID of uploaded file")
    artifact_id: str = Field(..., description="ULID of artifact")
    filename: str = Field(..., description="Name of uploaded file")
    size_bytes: int = Field(..., description="Size in bytes")
    sha256_checksum: str = Field(..., description="SHA256 hash")
    md5_checksum: str = Field(..., description="MD5 hash")
    storage_path: str = Field(..., description="Path in storage backend")
    download_url: str = Field(..., description="URL to download file")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")
    version: int = Field(1, description="File version number")


# ============================================================================
# DUPLICATE CHECK SCHEMAS
# ============================================================================

class DuplicateCheckRequest(BaseModel):
    """Request model for checking if file already exists."""

    artifact_id: str = Field(..., description="Artifact ID")
    filename: Optional[str] = Field(None, description="Filename to check")
    sha256_checksum: Optional[str] = Field(None, description="SHA256 to check")


class DuplicateCheckResponse(BaseModel):
    """Response model for duplicate check."""

    is_duplicate: bool = Field(..., description="Whether file is duplicate")
    existing_file_id: Optional[str] = Field(None, description="ID if duplicate found")
    message: str = Field(..., description="Status message")


# ============================================================================
# FILE VERIFICATION SCHEMAS
# ============================================================================

class FileVerificationRequest(BaseModel):
    """Request model for file verification."""

    file_id: str = Field(..., description="File ID to verify")
    sha256_checksum: Optional[str] = Field(None, description="Expected SHA256")


class FileVerificationResponse(BaseModel):
    """Response model for file verification."""

    file_id: str = Field(..., description="File ID")
    is_verified: bool = Field(..., description="Verification result")
    message: str = Field(..., description="Verification message")


# ============================================================================
# MODEL VERSION SCHEMAS
# ============================================================================

class ModelVersionResponse(BaseModel):
    """Response model for a single model version."""

    version: int = Field(..., description="Version number")
    file_id: str = Field(..., description="File ID for this version")
    created_at: datetime = Field(..., description="Creation timestamp")
    filename: str = Field(..., description="Filename")
    sha256_checksum: str = Field(..., description="SHA256 hash")


class ModelVersionListResponse(BaseModel):
    """Response model for listing model versions."""

    artifact_id: str = Field(..., description="Artifact ID")
    versions: List[ModelVersionResponse] = Field(..., description="List of versions")
    total_versions: int = Field(..., description="Total number of versions")


# ============================================================================
# FILE SEARCH SCHEMAS
# ============================================================================

class FileSearchResult(BaseModel):
    """Single search result for a file."""

    file_id: str = Field(..., description="File ID")
    artifact_id: str = Field(..., description="Artifact ID")
    filename: str = Field(..., description="Filename")
    size_bytes: int = Field(..., description="File size")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    sha256_checksum: str = Field(..., description="SHA256 hash")


class BatchSearchRequest(BaseModel):
    """Request model for batch search."""

    artifact_id: Optional[str] = Field(None, description="Filter by artifact ID")
    filename_pattern: Optional[str] = Field(None, description="Filename pattern to search")
    min_size_bytes: Optional[int] = Field(None, description="Minimum file size")
    max_size_bytes: Optional[int] = Field(None, description="Maximum file size")
    limit: int = Field(100, description="Max results to return")
    offset: int = Field(0, description="Result offset for pagination")


class BatchSearchResponse(BaseModel):
    """Response model for batch search."""

    results: List[FileSearchResult] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total matching files")
    limit: int = Field(..., description="Result limit")
    offset: int = Field(..., description="Result offset")


# ============================================================================
# BATCH UPLOAD SCHEMAS
# ============================================================================

class BatchUploadItem(BaseModel):
    """Single item in a batch upload request."""

    filename: str = Field(..., description="Filename")
    file_content: str = Field(..., description="Base64 encoded file content")
    description: Optional[str] = Field(None, description="File description")


class BatchUploadRequest(BaseModel):
    """Request model for batch file upload."""

    artifact_id: str = Field(..., description="Target artifact ID")
    files: List[BatchUploadItem] = Field(..., description="Files to upload")
    skip_duplicates: bool = Field(True, description="Skip duplicate files")
    stop_on_error: bool = Field(False, description="Stop on first error")


class BatchUploadFileResult(BaseModel):
    """Result for a single file in batch upload."""

    filename: str = Field(..., description="Filename")
    success: bool = Field(..., description="Upload success")
    file_id: Optional[str] = Field(None, description="Uploaded file ID")
    error_message: Optional[str] = Field(None, description="Error if failed")
    sha256_checksum: Optional[str] = Field(None, description="SHA256 if successful")


class BatchUploadResponse(BaseModel):
    """Response model for batch upload."""

    batch_id: str = Field(..., description="Batch upload ID")
    artifact_id: str = Field(..., description="Artifact ID")
    results: List[BatchUploadFileResult] = Field(..., description="Results for each file")
    successful_count: int = Field(..., description="Number of successful uploads")
    failed_count: int = Field(..., description="Number of failed uploads")
    total_files: int = Field(..., description="Total files processed")


# ============================================================================
# CHUNKED UPLOAD SCHEMAS
# ============================================================================

class ChunkedUploadInitRequest(BaseModel):
    """Request model to initiate chunked upload."""

    artifact_id: str = Field(..., description="Target artifact ID")
    filename: str = Field(..., description="Original filename")
    total_size_bytes: int = Field(..., description="Total file size in bytes")
    total_chunks: int = Field(..., description="Number of chunks")
    chunk_size_bytes: int = Field(10_000_000, description="Chunk size in bytes (default 10MB)")
    pre_calculated_sha256: Optional[str] = Field(None, description="Pre-calculated SHA256 for verification")


class ChunkedUploadInitResponse(BaseModel):
    """Response model for chunked upload initiation."""

    upload_session_id: str = Field(..., description="Session ID for uploads")
    artifact_id: str = Field(..., description="Artifact ID")
    filename: str = Field(..., description="Filename")
    total_chunks: int = Field(..., description="Total chunks expected")
    chunk_size_bytes: int = Field(..., description="Chunk size in bytes")
    upload_url: str = Field(..., description="URL template for chunk uploads")
    expires_at: datetime = Field(..., description="Session expiration time")


class ChunkUploadRequest(BaseModel):
    """Request model for uploading a single chunk."""

    chunk_number: int = Field(..., description="Chunk number (0-indexed)")
    chunk_content: str = Field(..., description="Base64 encoded chunk content")
    chunk_sha256: Optional[str] = Field(None, description="SHA256 of chunk for verification")


class ChunkUploadResponse(BaseModel):
    """Response model for chunk upload."""

    upload_session_id: str = Field(..., description="Session ID")
    chunk_number: int = Field(..., description="Chunk number received")
    bytes_received: int = Field(..., description="Bytes received for this chunk")
    total_bytes_received: int = Field(..., description="Total bytes received so far")
    received_chunks: List[int] = Field(..., description="List of received chunk numbers")


class ChunkedUploadFinalizeRequest(BaseModel):
    """Request model to finalize chunked upload."""

    upload_session_id: str = Field(..., description="Session ID")
    final_sha256: Optional[str] = Field(None, description="Final SHA256 of complete file")


class ChunkedUploadFinalizeResponse(BaseModel):
    """Response model for finalized chunked upload."""

    file_id: str = Field(..., description="Uploaded file ID")
    artifact_id: str = Field(..., description="Artifact ID")
    filename: str = Field(..., description="Filename")
    total_size_bytes: int = Field(..., description="Total file size")
    sha256_checksum: str = Field(..., description="Final SHA256 hash")
    upload_session_id: str = Field(..., description="Session ID (for audit)")
    completed_at: datetime = Field(..., description="Completion timestamp")


class UploadProgressResponse(BaseModel):
    """Response model for upload progress."""

    upload_session_id: str = Field(..., description="Session ID")
    artifact_id: str = Field(..., description="Artifact ID")
    filename: str = Field(..., description="Filename")
    total_chunks: int = Field(..., description="Total chunks")
    received_chunks: int = Field(..., description="Chunks received so far")
    total_bytes: int = Field(..., description="Total bytes to upload")
    bytes_received: int = Field(..., description="Bytes received so far")
    percent_complete: float = Field(..., description="Percentage complete (0-100)")
    status: str = Field(..., description="Status: 'in_progress', 'stalled', 'complete'")
    time_elapsed_seconds: int = Field(..., description="Seconds elapsed")
    estimated_time_remaining_seconds: Optional[int] = Field(None, description="Estimated seconds remaining")
