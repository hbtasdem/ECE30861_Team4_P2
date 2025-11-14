"""SQLAlchemy ORM models for Phase 3+ file upload and management.

Per OpenAPI v3.4.4 Sections 3.3 - 3.4 - Extended File Management Schema

FILE PURPOSE:
Defines database models for file storage, versioning, downloads, and upload sessions.
Extends Phase 2 artifact management with file-level operations.
Integrates with FileStorageService for actual file backend operations.

SCHEMA OVERVIEW:

┌──────────────┐         ┌────────────────┐
│  Artifact    │───1:N───│  FileStorage   │───1:N───┬──────────────────┐
│              │         │                │         │  DownloadEvent   │
└──────────────┘         ├────────────────┤         └──────────────────┘
                         │ id (ULID)      │
                         │ sha256_checksum│
                         │ content (file) │
                         │ size_bytes     │
                         └────────────────┘

MODELS DEFINED:

1. FileStorage TABLE
   Purpose: Track uploaded files with metadata and integrity checksums

   Columns:
   - id (String ULID, PK): Unique file identifier (26 chars)
     * Per spec: Phase 3 file upload requirements
     * Format: Same as artifact IDs (sortable, globally unique)

   - artifact_id (String ULID, FK): Reference to parent artifact
     * Per spec: Files belong to artifacts
     * Index: Fast lookup by artifact_id

   - uploaded_by (String ULID, FK): User who uploaded file
     * Per spec: Audit trail requirement
     * Used for: Access control and attribution

   - filename (String): Display name of file
   - original_filename (String): Original filename from upload

   - size_bytes (Integer): File size in bytes
     * Indexed: Fast filtering by size ranges
     * Used: Bandwidth tracking, quota enforcement

   - content_type (String): MIME type (e.g., "application/octet-stream")

   - sha256_checksum (String 64 chars): SHA256 hash of content
     * Per spec: Integrity verification requirement
     * Indexed (UNIQUE=False): Detect duplicates
     * Used by: Deduplication, integrity verification

   - md5_checksum (String 32 chars): MD5 hash (secondary checksum)
     * Legacy hash for compatibility

   - storage_location (String): Path/key in storage backend
     * Format: "{artifact_id}/{file_id}{ext}" for local
     * Format: "artifacts/{artifact_id}/{file_id}{ext}" for S3

   - storage_backend (String): Which backend stores file
     * Values: "local", "s3"
     * Used: Route retrieve_file() to correct backend

   - is_verified (Boolean): Whether file integrity verified
     * Per spec: Track verification status
     * Used: Skip re-verification of known-good files

   - verified_at (DateTime): Last verification timestamp

   - description (Text): Optional file description
   - tags (String): Comma-separated or JSON tags

   - uploaded_at (DateTime): Upload timestamp
     * Indexed: Fast sorting and filtering

   - updated_at (DateTime): Last modification timestamp

   Relationships:
   - artifact (N:1): Many-to-one with Artifact table
   - uploader (N:1): Many-to-one with User table
   - versions (1:N): One-to-many with ModelVersion table
   - download_events (1:N): One-to-many with DownloadEvent table

   Indexes:
   - idx_file_sha256_artifact: (sha256_checksum, artifact_id) for dedup detection
   - idx_file_uploaded: (uploaded_at, artifact_id) for time-based queries

   Spec Reference:
   - Section 3.4: File upload requirements
   - Section 3.3.3: FileStorage table schema

   HTTP Endpoints Using This:
   - POST /api/models/upload-file (201)
   - GET /api/models/{id}/download (200 + streaming)
   - POST /api/models/check-duplicate (200)
   - POST /api/models/validate (200)


2. ModelVersion TABLE
   Purpose: Track version history for files associated with an artifact

   Columns:
   - id (String ULID, PK): Unique version identifier

   - artifact_id (String ULID, FK): Parent artifact
   - file_id (String ULID, FK): Associated file
   - created_by (String ULID, FK): User who created version

   - version_number (Integer): Version sequence number (1, 2, 3, ...)
     * Indexed with artifact_id: Fast "get version N" queries

   - filename (String): Filename for this version
   - size_bytes (Integer): File size
   - sha256_checksum (String): Content hash for diff detection

   - changelog (Text): Human-readable version notes
     * Per spec: Track what changed between versions

   - notes (Text): Additional version metadata

   - created_at (DateTime): Version creation timestamp
   - deprecated_at (DateTime): When version was superseded

   Indexes:
   - idx_version_artifact_number: (artifact_id, version_number) for queries

   Spec Reference:
   - Section 3.4: File versioning support
   - Future endpoint: GET /api/models/{id}/versions

   Use Cases:
   - GET /api/models/{id}/versions: List all versions
   - Rollback: Revert to previous version
   - Changelog: Show what changed between versions
   - Dedup: Detect if new upload is same as old version


3. DownloadEvent TABLE
   Purpose: Audit trail for all file downloads

   Columns:
   - id (String ULID, PK): Unique download event ID

   - file_id (String ULID, FK): File being downloaded
   - artifact_id (String ULID, FK): Parent artifact
   - downloaded_by (String ULID, FK): User who downloaded

   - bytes_downloaded (Integer): Actual bytes transferred
   - download_speed_mbps (Float): Calculated transfer speed
   - status (String): "success", "failed", "partial", "resumed"

   - user_agent (String): Client user agent string
   - client_ip (String): Client IP address (IPv4 or IPv6)

   - downloaded_at (DateTime): When download occurred

   Indexes:
   - idx_download_file_time: (file_id, downloaded_at)
   - idx_download_artifact_time: (artifact_id, downloaded_at)

   Spec Reference:
   - Section 3.4: Download tracking and statistics
   - Future endpoint: GET /api/artifacts/{id}/download-stats

   Use Cases:
   - Analytics: Track file popularity
   - Audit: Compliance and security tracking
   - Billing: Track bandwidth usage
   - Throttling: Detect abusive downloading


4. UploadSession TABLE
   Purpose: Track multipart/chunked upload sessions for resumable uploads

   Columns:
   - id (String ULID, PK): Session ID for tracking

   - artifact_id (String ULID, FK): Target artifact
   - uploaded_by (String ULID, FK): User uploading

   - filename (String): File being uploaded
   - total_size_bytes (Integer): Expected file size
   - uploaded_bytes (Integer): Bytes uploaded so far
   - progress_percent (Integer): 0-100 progress

   - status (String): "pending", "in_progress", "completed", "failed"
   - error_message (Text): Error details if failed

   - parts_completed (Integer): Number of chunks uploaded
   - total_parts (Integer): Expected chunk count

   - created_at (DateTime): Session start time
   - expires_at (DateTime): When session expires (24h default)
   - completed_at (DateTime): When upload finished

   Indexes:
   - idx_upload_status_artifact: (status, artifact_id)
   - idx_upload_expires: (expires_at) for cleanup queries

   Spec Reference:
   - Section 3.4: Chunked/resumable upload requirements
   - Endpoints:
     * POST /api/models/chunked-upload/init (201)
     * POST /api/models/chunked-upload/{id}/chunk (202)
     * GET /api/models/chunked-upload/{id}/progress (200)

   Behavior:
   - Session expires after 24 hours of inactivity
   - Can upload chunks out of order
   - Progress tracked in real-time
   - Download ETA calculated from speed

   Use Cases:
   - Large file uploads (>1GB)
   - Resumable downloads (connection interrupted)
   - Progress tracking (UX feedback)
   - Network optimization (adjust chunk size)


DATABASE RELATIONSHIPS:

User (1) ──────(N)─── FileStorage
  └─ uploads multiple files

Artifact (1) ──────(N)─── FileStorage
  └─ contains multiple file versions

FileStorage (1) ──────(N)─── DownloadEvent
  └─ tracks download history

FileStorage (1) ──────(N)─── ModelVersion
  └─ maintains version chain

Artifact (1) ──────(N)─── ModelVersion
  └─ version history for artifact

Artifact (1) ──────(N)─── UploadSession
  └─ active uploads in progress


LIFECYCLE EXAMPLES:

Example 1: Single File Upload
  1. User calls POST /api/models/upload-file
  2. FileStorageService.store_file() creates file
  3. FileStorage record inserted with sha256, size, etc.
  4. DownloadEvent created with "uploaded" action
  5. GET /api/models/{id}/download retrieves via DownloadEvent tracking

Example 2: Chunked Upload (Large File)
  1. User calls POST /api/models/chunked-upload/init
  2. UploadSession created (expires 24h)
  3. User calls POST .../chunk for each chunk (202 Accepted)
  4. Progress tracked: UploadSession.progress_percent
  5. User calls POST .../finalize to assemble
  6. FileStorage record created from assembled chunks
  7. UploadSession.status = "completed"
  8. UploadSession expires and cleaned up

Example 3: File Versioning
  1. V1 uploaded → FileStorage.id=file_v1, ModelVersion.version_number=1
  2. V2 uploaded → FileStorage.id=file_v2, ModelVersion.version_number=2
  3. GET /api/models/{id}/versions shows both
  4. Can download specific version via version_number


FOREIGN KEY CASCADES:
- User deletion: Cascades to FileStorage (orphan files)
- Artifact deletion: Cascades to FileStorage, ModelVersion
- FileStorage deletion: Cascades to DownloadEvent, ModelVersion

CASCADE POLICY:
- cascade='all, delete-orphan': For audit trails
- No cascade: For immutable history (DownloadEvent)


SPEC SECTIONS REFERENCED:
- Section 3.4: File upload and management
- Section 3.3.2: FileStorage table schema
- Section 3.3.3: ModelVersion table schema
- Section 3.3.4: DownloadEvent table schema
- Section 3.1: Authentication for all operations
"""

from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text)
from sqlalchemy.orm import relationship

from src.database_models import Base


class FileStorage(Base):
    """Track uploaded files with metadata and integrity checksums."""

    __tablename__ = "file_storage"

    # Primary key
    id = Column(String(26), primary_key=True, index=True)  # ULID

    # Foreign keys
    artifact_id = Column(String(26), ForeignKey("artifacts.id"), nullable=False, index=True)
    uploaded_by = Column(String(26), ForeignKey("users.id"), nullable=False, index=True)

    # File metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=False, index=True)
    content_type = Column(String(100), default="application/octet-stream")

    # Checksums
    sha256_checksum = Column(String(64), nullable=False, unique=False, index=True)
    md5_checksum = Column(String(32), nullable=True)

    # Storage details
    storage_location = Column(String(512), nullable=False)
    storage_backend = Column(String(20), default="local")  # "local" or "s3"

    # Verification
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated or JSON

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (one-way to avoid circular imports with database_models)
    artifact = relationship("Artifact")  # No back_populates to avoid circular ref
    uploader = relationship("User")  # No back_populates - User doesn't reference FileStorage
    versions = relationship("ModelVersion", back_populates="file_storage")
    download_events = relationship("DownloadEvent", back_populates="file")

    # Indexes
    __table_args__ = (
        Index("idx_file_sha256_artifact", "sha256_checksum", "artifact_id"),
        Index("idx_file_uploaded", "uploaded_at", "artifact_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<FileStorage {self.id}: {self.filename} ({self.size_bytes} bytes)>"


class ModelVersion(Base):
    """Track version history for files associated with an artifact."""

    __tablename__ = "model_version"

    # Primary key
    id = Column(String(26), primary_key=True, index=True)  # ULID

    # Foreign keys
    artifact_id = Column(String(26), ForeignKey("artifacts.id"), nullable=False, index=True)
    file_id = Column(String(26), ForeignKey("file_storage.id"), nullable=False, index=True)
    created_by = Column(String(26), ForeignKey("users.id"), nullable=False)

    # Version tracking
    version_number = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256_checksum = Column(String(64), nullable=False)

    # Changelog and metadata
    changelog = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    deprecated_at = Column(DateTime, nullable=True)

    # Relationships
    artifact = relationship("Artifact")  # No back_populates to avoid circular ref
    file_storage = relationship("FileStorage", back_populates="versions")
    creator = relationship("User")  # No back_populates - User doesn't reference ModelVersion

    # Indexes
    __table_args__ = (
        Index("idx_version_artifact_number", "artifact_id", "version_number"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ModelVersion {self.artifact_id} v{self.version_number}>"


class DownloadEvent(Base):
    """Audit trail for all file downloads."""

    __tablename__ = "download_event"

    # Primary key
    id = Column(String(26), primary_key=True, index=True)  # ULID

    # Foreign keys
    file_id = Column(String(26), ForeignKey("file_storage.id"), nullable=False, index=True)
    artifact_id = Column(String(26), ForeignKey("artifacts.id"), nullable=False, index=True)
    downloaded_by = Column(String(26), ForeignKey("users.id"), nullable=False, index=True)

    # Download details
    bytes_downloaded = Column(Integer, nullable=False)
    download_speed_mbps = Column(Float, nullable=True)
    status = Column(String(20), default="success")  # "success", "failed", "partial"

    # Client info
    user_agent = Column(String(500), nullable=True)
    client_ip = Column(String(45), nullable=True)  # IPv4 or IPv6

    # Timestamps
    downloaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    file = relationship("FileStorage", back_populates="download_events")
    artifact = relationship("Artifact")  # No back_populates - Artifact doesn't reference this
    downloader = relationship("User")  # No back_populates - User doesn't reference this

    # Indexes
    __table_args__ = (
        Index("idx_download_file_time", "file_id", "downloaded_at"),
        Index("idx_download_artifact_time", "artifact_id", "downloaded_at"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<DownloadEvent {self.id}: {self.bytes_downloaded} bytes>"


class UploadSession(Base):
    """Track multipart upload sessions for resumable uploads."""

    __tablename__ = "upload_session"

    # Primary key
    id = Column(String(26), primary_key=True, index=True)  # ULID

    # Foreign keys
    artifact_id = Column(String(26), ForeignKey("artifacts.id"), nullable=False, index=True)
    uploaded_by = Column(String(26), ForeignKey("users.id"), nullable=False)

    # Upload details
    filename = Column(String(255), nullable=False)
    total_size_bytes = Column(Integer, nullable=False)
    uploaded_bytes = Column(Integer, default=0)
    progress_percent = Column(Integer, default=0, index=True)

    # Session status
    status = Column(String(20), default="pending")  # "pending", "in_progress", "completed", "failed"
    error_message = Column(Text, nullable=True)

    # Multipart details
    parts_completed = Column(Integer, default=0)
    total_parts = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)  # Session auto-expires after 24h
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    artifact = relationship("Artifact")
    uploader = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_upload_status_artifact", "status", "artifact_id"),
        Index("idx_upload_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<UploadSession {self.id}: {self.progress_percent}% complete>"
