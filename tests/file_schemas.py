"""Pydantic schemas for Phase 3+ file upload and management endpoints.

Per OpenAPI v3.4.4 Sections 3.3 - 3.4 - Request/Response Models

FILE PURPOSE:
Defines Pydantic v2 models for file upload, download, validation, and batch operations.
Handles request validation and response serialization for all Phase 3+ file endpoints.
Provides type hints for IDE autocomplete and runtime validation.

SCHEMA GROUPS:

1. SINGLE FILE UPLOAD (Phase 3)
   - FileUploadResponse: Single file upload response (201)
   - FileDownloadMetadata: Download file metadata

2. DUPLICATE DETECTION (Phase 3)
   - DuplicateCheckRequest: Check if file exists by SHA256
   - DuplicateCheckResponse: Duplicate detection result

3. FILE VERIFICATION (Phase 3)
   - FileVerificationRequest: Request integrity verification
   - FileVerificationResponse: Verification result (200)

4. VERSIONING (Phase 3)
   - ModelVersionResponse: Single version details
   - ModelVersionListResponse: List all versions (200)

5. FILE SEARCH (Phase 3)
   - BatchSearchRequest: Search query parameters
   - FileSearchResult: Single search result
   - BatchSearchResponse: Search results batch (200)

6. BATCH UPLOAD (Phase 4)
   - BatchUploadItem: Single file in batch
   - BatchUploadRequest: Batch upload request
   - BatchUploadFileResult: Result for one file
   - BatchUploadResponse: Batch upload response (201)

7. CHUNKED UPLOAD (Phase 4)
   - ChunkedUploadInitRequest: Start resumable upload (201)
   - ChunkedUploadInitResponse: Session details
   - ChunkUploadRequest: Upload single chunk (202)
   - ChunkUploadResponse: Chunk received confirmation
   - ChunkedUploadFinalizeRequest: Finalize chunks (201)
   - ChunkedUploadFinalizeResponse: Upload complete
   - UploadProgressResponse: Real-time progress (200)

8. FILE VALIDATION (Phase 4)
   - FileValidationRequest: Validate file (200)
   - FileValidationResult: Single validation result
   - FileValidationResponse: All validation results

HTTP STATUS CODES:
- 201 Created: File upload successful (upload-file, upload-batch, finalize)
- 202 Accepted: Chunk accepted, upload continues (chunk upload)
- 200 OK: Query operations (duplicate check, progress, validation)
- 404 Not Found: File or artifact not found
- 413 Payload Too Large: File exceeds size limit (>1GB)
- 422 Unprocessable Entity: Validation error (invalid chunk config)

FIELD CONSTRAINTS:
- file_id: ULID (26 alphanumeric chars)
- artifact_id: ULID (26 alphanumeric chars)
- sha256_checksum: 64 hex characters (256-bit)
- md5_checksum: 32 hex characters (128-bit)
- size_bytes: Integer >= 0
- progress_percent: Integer 0-100
- chunk_number: Integer >= 1
- total_chunks: Integer >= 1, <= 10000

AUTHENTICATION:
- X-Authorization header with bearer token required
- Token from PUT /authenticate endpoint
- Verified by get_current_user() dependency

REQUEST EXAMPLES:

FileUploadRequest:
  POST /api/models/upload-file
  Query: artifact_id=01K9ZBPC...
  Body: multipart/form-data file

BatchUploadRequest:
  POST /api/models/upload-batch
  {
    "artifact_id": "01K9ZBPC...",
    "files": [
      {"filename": "model.pth", "description": "v1"},
      {"filename": "config.json", "description": "config"}
    ],
    "skip_duplicates": true,
    "stop_on_error": false
  }

ChunkedUploadInitRequest:
  POST /api/models/chunked-upload/init
  {
    "artifact_id": "01K9ZBPC...",
    "filename": "large_model.pth",
    "total_size_bytes": 1000000000,
    "total_chunks": 100,
    "chunk_size_bytes": 10485760
  }

RESPONSE EXAMPLES:

FileUploadResponse (201):
  {
    "file_id": "01K9ZBPC...",
    "artifact_id": "01K9ZBPC...",
    "filename": "model.pth",
    "size_bytes": 524288000,
    "sha256_checksum": "e3b0c44...",
    "md5_checksum": "d41d8cd...",
    "download_url": "/api/models/download/01K9ZBPC...",
    "uploaded_at": "2024-01-15T10:30:00Z",
    "version": 1
  }

DuplicateCheckResponse (200):
  {
    "is_duplicate": true,
    "existing_file_id": "01K9ZBPC...",
    "message": "Duplicate found: existing_file.pth"
  }

UploadProgressResponse (200):
  {
    "upload_session_id": "01K9ZBPC...",
    "artifact_id": "01K9ZBPC...",
    "filename": "model.pth",
    "progress_percent": 75,
    "received_chunks": 75,
    "total_chunks": 100,
    "eta_seconds": 120,
    "upload_speed_mbps": 50.5
  }

VALIDATION RULES:
- All fields marked with ... are required
- Fields marked Optional[...] are nullable
- ULIDs must match pattern: ^[A-Z0-9]{26}$
- Filenames cannot contain: / \\ : * ? \" < > |
- Checksums must be lowercase hex
- Sizes must be >= 1 byte
- Percentages must be 0-100
- Timestamps must be ISO-8601

ERROR RESPONSES:
- 400: Invalid request format (missing or malformed fields)
- 404: Resource not found (artifact_id, file_id)
- 413: File too large (size > 1GB)
- 422: Validation error (invalid chunk config, batch size >50)
- 500: Server error (database, storage backend, checksum)

SPEC SECTIONS REFERENCED:
- Section 3.4: File upload and management request/response models
- Section 3.3.2: FileStorage data model
- Section 3.1: Authentication requirements
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """File metadata."""

    filename: str = Field(..., description="Original filename")
    size_bytes: int = Field(..., description="File size in bytes", ge=0)
    mime_type: str = Field(
        ..., description="MIME type (e.g., 'application/octet-stream')"
    )
    uploaded_by: str = Field(..., description="User ID who uploaded the file")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class FileUploadRequest(BaseModel):
    """Request model for uploading a file to an artifact."""

    artifact_id: str = Field(..., description="ULID of the artifact")
    description: Optional[str] = Field(None, description="Optional file description")
    tags: Optional[list[str]] = Field(
        None, description="Optional file tags for categorization"
    )
    metadata_json: Optional[dict[str, str]] = Field(
        None, description="Optional custom metadata"
    )


class FileUploadResponse(BaseModel):
    """Response model for successful file upload."""

    file_id: str = Field(..., description="ULID of the uploaded file")
    artifact_id: str = Field(..., description="Associated artifact ID")
    filename: str = Field(..., description="Original filename")
    size_bytes: int = Field(..., description="File size in bytes")
    sha256_checksum: str = Field(..., description="SHA256 checksum")
    md5_checksum: str = Field(..., description="MD5 checksum")
    storage_path: str = Field(..., description="Internal storage path/key")
    download_url: str = Field(..., description="URL for downloading file")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    version: int = Field(default=1, description="File version number")

    model_config = {
        "json_schema_extra": {
            "example": {
                "file_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "artifact_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "filename": "model.pth",
                "size_bytes": 524288000,
                "sha256_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "md5_checksum": "d41d8cd98f00b204e9800998ecf8427e",
                "storage_path": "artifacts/artifact_id/file_id.pth",
                "download_url": "/api/models/download/file_id",
                "uploaded_at": "2024-01-15T10:30:00Z",
                "version": 1,
            }
        }
    }


class BatchFileUploadRequest(BaseModel):
    """Request model for batch file upload."""

    artifact_id: str = Field(..., description="ULID of the artifact")
    files: list[FileUploadRequest] = Field(
        ..., min_length=1, description="List of files to upload"
    )


class BatchFileUploadResponse(BaseModel):
    """Response model for batch file upload."""

    total_files: int = Field(..., description="Total files in batch")
    successful: int = Field(..., description="Number of successful uploads")
    failed: int = Field(..., description="Number of failed uploads")
    files: list[FileUploadResponse] = Field(
        ..., description="Successfully uploaded files"
    )
    errors: Optional[list[dict[str, str]]] = Field(
        None, description="Errors for failed uploads"
    )


class FileVerificationRequest(BaseModel):
    """Request model for file integrity verification."""

    file_id: str = Field(..., description="ULID of the file to verify")
    expected_sha256: Optional[str] = Field(None, description="Expected SHA256 checksum")


class FileVerificationResponse(BaseModel):
    """Response model for file verification."""

    file_id: str = Field(..., description="ULID of the verified file")
    is_valid: bool = Field(..., description="Whether file passed integrity check")
    sha256_checksum: str = Field(..., description="Actual SHA256 checksum")
    message: str = Field(..., description="Verification result message")


class DuplicateCheckRequest(BaseModel):
    """Request model for checking file duplicates."""

    sha256_checksum: str = Field(..., description="SHA256 checksum to check")
    artifact_id: Optional[str] = Field(
        None, description="Exclude this artifact from results"
    )


class DuplicateCheckResponse(BaseModel):
    """Response model for duplicate check."""

    is_duplicate: bool = Field(..., description="Whether duplicate exists")
    duplicate_file_id: Optional[str] = Field(
        None, description="ULID of duplicate file if found"
    )
    duplicate_artifact_id: Optional[str] = Field(
        None, description="Artifact ID of duplicate if found"
    )
    original_filename: Optional[str] = Field(
        None, description="Original filename of duplicate"
    )
    uploaded_at: Optional[datetime] = Field(
        None, description="Upload date of duplicate"
    )


class FileDownloadRequest(BaseModel):
    """Request model for file download."""

    file_id: str = Field(..., description="ULID of the file to download")


class FileDownloadMetadata(BaseModel):
    """Metadata for file downloads."""

    file_id: str = Field(..., description="ULID of the file")
    filename: str = Field(..., description="Original filename")
    size_bytes: int = Field(..., description="File size in bytes")
    sha256_checksum: str = Field(..., description="SHA256 checksum")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    content_type: str = Field(..., description="MIME type")


class ModelVersionResponse(BaseModel):
    """Response model for model version information."""

    version_id: str = Field(..., description="ULID of the version")
    artifact_id: str = Field(..., description="Associated artifact ID")
    version_number: int = Field(..., description="Version number")
    file_id: str = Field(..., description="Associated file ID")
    filename: str = Field(..., description="Filename of version")
    size_bytes: int = Field(..., description="File size in bytes")
    sha256_checksum: str = Field(..., description="SHA256 checksum")
    changelog: Optional[str] = Field(None, description="Version changelog/notes")
    created_at: datetime = Field(..., description="Version creation timestamp")
    created_by: str = Field(..., description="User ID who created version")


class ModelVersionListResponse(BaseModel):
    """Response model for listing model versions."""

    artifact_id: str = Field(..., description="Artifact ID")
    total_versions: int = Field(..., description="Total number of versions")
    versions: list[ModelVersionResponse] = Field(..., description="List of versions")
    current_version: int = Field(..., description="Current/active version number")


class UploadSessionResponse(BaseModel):
    """Response model for upload session information."""

    session_id: str = Field(..., description="ULID of upload session")
    artifact_id: str = Field(..., description="Associated artifact ID")
    filename: str = Field(..., description="Filename being uploaded")
    total_size_bytes: int = Field(..., description="Total file size")
    uploaded_bytes: int = Field(..., description="Bytes uploaded so far")
    progress_percent: int = Field(
        ..., description="Upload progress percentage", ge=0, le=100
    )
    status: str = Field(
        ..., description="Upload status (pending, in_progress, completed, failed)"
    )
    created_at: datetime = Field(..., description="Session start timestamp")
    expires_at: datetime = Field(..., description="Session expiration timestamp")


class BatchSearchRequest(BaseModel):
    """Request model for searching file metadata."""

    artifact_id: Optional[str] = Field(None, description="Filter by artifact ID")
    filename_pattern: Optional[str] = Field(None, description="Search filename pattern")
    uploaded_by: Optional[str] = Field(None, description="Filter by uploader")
    min_size_bytes: Optional[int] = Field(None, description="Minimum file size")
    max_size_bytes: Optional[int] = Field(None, description="Maximum file size")
    tags: Optional[list[str]] = Field(None, description="Filter by tags")
    skip: int = Field(default=0, description="Pagination offset", ge=0)
    limit: int = Field(default=20, description="Pagination limit", ge=1, le=100)


class FileSearchResult(BaseModel):
    """Individual result from file search."""

    file_id: str = Field(..., description="ULID of the file")
    artifact_id: str = Field(..., description="Associated artifact ID")
    filename: str = Field(..., description="Filename")
    size_bytes: int = Field(..., description="File size in bytes")
    sha256_checksum: str = Field(..., description="SHA256 checksum")
    uploaded_by: str = Field(..., description="User ID who uploaded")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    tags: Optional[list[str]] = Field(None, description="Associated tags")


class BatchSearchResponse(BaseModel):
    """Response model for file search results."""

    total_results: int = Field(..., description="Total matching files")
    returned_results: int = Field(..., description="Files in this response")
    skip: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Pagination limit")
    files: list[FileSearchResult] = Field(..., description="Search results")


class FileDeleteRequest(BaseModel):
    """Request model for file deletion."""

    file_id: str = Field(..., description="ULID of the file to delete")
    reason: Optional[str] = Field(None, description="Reason for deletion")


class FileDeleteResponse(BaseModel):
    """Response model for file deletion."""

    file_id: str = Field(..., description="ULID of deleted file")
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Deletion result message")
    deleted_at: datetime = Field(..., description="Deletion timestamp")


# ============================================================================
# PHASE 4: UPLOAD ENHANCEMENTS - BATCH & CHUNKED UPLOAD
# ============================================================================


class BatchUploadItem(BaseModel):
    """Single file item for batch upload."""

    filename: str = Field(..., description="Original filename")
    size_bytes: int = Field(..., description="File size in bytes")
    description: Optional[str] = Field(None, description="Optional file description")
    tags: Optional[list[str]] = Field(None, description="Optional tags")
    metadata: Optional[dict[str, str]] = Field(
        None, description="Optional custom metadata"
    )


class BatchUploadRequest(BaseModel):
    """Request model for batch file upload."""

    artifact_id: str = Field(..., description="ULID of the artifact")
    files: list[BatchUploadItem] = Field(
        ..., min_length=1, max_length=50, description="List of files to upload (1-50)"
    )
    skip_duplicates: bool = Field(
        default=False, description="Skip files with duplicate checksums"
    )
    stop_on_error: bool = Field(
        default=False, description="Stop batch if any file fails"
    )


class BatchUploadFileResult(BaseModel):
    """Result for individual file in batch upload."""

    filename: str = Field(..., description="Filename")
    file_id: Optional[str] = Field(None, description="ULID if successful")
    success: bool = Field(..., description="Whether upload succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")
    size_bytes: Optional[int] = Field(None, description="File size")
    sha256_checksum: Optional[str] = Field(None, description="SHA256 if successful")


class BatchUploadResponse(BaseModel):
    """Response model for batch upload."""

    batch_id: str = Field(..., description="ULID of batch upload session")
    artifact_id: str = Field(..., description="Associated artifact ID")
    total_files: int = Field(..., description="Total files in batch")
    successful: int = Field(..., description="Number of successful uploads")
    failed: int = Field(..., description="Number of failed uploads")
    skipped: int = Field(default=0, description="Number of skipped uploads")
    files: list[BatchUploadFileResult] = Field(..., description="Results for each file")
    completed_at: datetime = Field(..., description="Batch completion timestamp")
    processing_time_ms: int = Field(
        ..., description="Total processing time in milliseconds"
    )


class ChunkedUploadInitRequest(BaseModel):
    """Request to initiate a chunked upload."""

    artifact_id: str = Field(..., description="ULID of the artifact")
    filename: str = Field(..., description="Original filename")
    total_size_bytes: int = Field(..., description="Total file size", ge=1)
    chunk_size_bytes: int = Field(
        default=10_485_760, description="Chunk size in bytes (default 10MB)", ge=262_144
    )
    total_chunks: int = Field(..., description="Total number of chunks")
    sha256_checksum: Optional[str] = Field(
        None, description="Optional pre-calculated SHA256"
    )
    description: Optional[str] = Field(None, description="Optional file description")


class ChunkedUploadInitResponse(BaseModel):
    """Response from initiating chunked upload."""

    upload_session_id: str = Field(..., description="ULID for this upload session")
    artifact_id: str = Field(..., description="Associated artifact ID")
    filename: str = Field(..., description="Filename")
    total_chunks: int = Field(..., description="Total chunks expected")
    chunk_size_bytes: int = Field(..., description="Chunk size in bytes")
    upload_url: str = Field(..., description="Base URL for uploading chunks")
    expires_at: datetime = Field(..., description="Session expiration time")


class ChunkUploadRequest(BaseModel):
    """Request to upload a single chunk."""

    upload_session_id: str = Field(..., description="ULID of upload session")
    chunk_number: int = Field(..., description="Chunk number (1-indexed)", ge=1)
    chunk_hash: str = Field(..., description="SHA256 hash of this chunk for integrity")


class ChunkUploadResponse(BaseModel):
    """Response from uploading a chunk."""

    upload_session_id: str = Field(..., description="ULID of upload session")
    chunk_number: int = Field(..., description="Chunk number received")
    received_bytes: int = Field(..., description="Bytes received for this chunk")
    total_received_bytes: int = Field(..., description="Total bytes received so far")
    progress_percent: int = Field(
        ..., description="Overall progress percentage", ge=0, le=100
    )
    remaining_chunks: int = Field(..., description="Chunks still needed")


class ChunkedUploadFinalizeRequest(BaseModel):
    """Request to finalize a chunked upload."""

    upload_session_id: str = Field(..., description="ULID of upload session")
    final_sha256: str = Field(..., description="SHA256 of complete file")
    verify_chunks: bool = Field(default=True, description="Verify all chunks received")


class ChunkedUploadFinalizeResponse(BaseModel):
    """Response from finalizing chunked upload."""

    file_id: str = Field(..., description="ULID of the final file")
    upload_session_id: str = Field(..., description="ULID of upload session")
    artifact_id: str = Field(..., description="Associated artifact ID")
    filename: str = Field(..., description="Filename")
    total_size_bytes: int = Field(..., description="Total file size")
    sha256_checksum: str = Field(..., description="SHA256 of complete file")
    chunks_received: int = Field(..., description="Number of chunks received")
    verification_status: str = Field(
        ..., description="Verification status (passed, failed, skipped)"
    )
    completed_at: datetime = Field(..., description="Completion timestamp")


class FileValidationRequest(BaseModel):
    """Request for file validation."""

    file_id: str = Field(..., description="ULID of file to validate")
    validation_type: str = Field(
        ..., description="Type: mime_type, size, malware, metadata"
    )
    options: Optional[dict[str, object]] = Field(
        None, description="Validation-specific options"
    )


class FileValidationResult(BaseModel):
    """Result from file validation."""

    file_id: str = Field(..., description="ULID of file")
    validation_type: str = Field(..., description="Type of validation performed")
    is_valid: bool = Field(..., description="Whether validation passed")
    message: str = Field(..., description="Validation message")
    details: Optional[dict[str, object]] = Field(
        None, description="Additional validation details"
    )
    checked_at: datetime = Field(..., description="Validation timestamp")


class FileValidationResponse(BaseModel):
    """Response from file validation."""

    file_id: str = Field(..., description="ULID of file")
    overall_status: str = Field(..., description="Overall: valid, invalid, warnings")
    validations: list[FileValidationResult] = Field(
        ..., description="Results for each validation"
    )
    all_passed: bool = Field(..., description="Whether all validations passed")


class UploadProgressRequest(BaseModel):
    """Request for upload progress."""

    upload_session_id: str = Field(..., description="ULID of upload session")


class UploadProgressResponse(BaseModel):
    """Response with upload progress."""

    upload_session_id: str = Field(..., description="ULID of upload session")
    artifact_id: str = Field(..., description="Associated artifact ID")
    filename: str = Field(..., description="Filename being uploaded")
    total_size_bytes: int = Field(..., description="Total file size")
    uploaded_bytes: int = Field(..., description="Bytes uploaded so far")
    progress_percent: int = Field(..., description="Progress percentage", ge=0, le=100)
    status: str = Field(
        ..., description="Status: pending, in_progress, completed, failed, paused"
    )
    eta_seconds: Optional[int] = Field(
        None, description="Estimated time remaining in seconds"
    )
    upload_speed_mbps: float = Field(..., description="Current upload speed in MB/s")
    last_updated: datetime = Field(..., description="Last progress update timestamp")
