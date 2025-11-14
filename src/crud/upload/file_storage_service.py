"""File storage service for Phase 3 file upload and management.

Per OpenAPI v3.4.4 Section 3.4 - Phase 3 File Management

FILE PURPOSE:
Abstracts file storage backend operations (local filesystem and S3).
Provides unified interface for storing, retrieving, and verifying files.
Handles checksum calculation, integrity verification, and download URL generation.

SUPPORTED BACKENDS:
1. Local Filesystem (default)
   - Stores files in directory structure: ./models/{artifact_id}/{file_id}{ext}
   - Efficient for development and small deployments
   - Requires filesystem permissions and disk space

2. Amazon S3
   - Stores files with S3 keys: artifacts/{artifact_id}/{file_id}{ext}
   - Scalable for large deployments
   - Requires boto3 library and AWS credentials
   - Uses presigned URLs for secure downloads

CORE METHODS:

1. calculate_checksums(file_bytes: bytes) → Tuple[str, str]
   Purpose: Compute SHA256 and MD5 hashes for integrity verification
   Returns: (sha256_hex, md5_hex)
   Used: Before storing file, during verification, in responses

2. store_file(file_bytes, filename, artifact_id) → Tuple[str, str, str]
   Purpose: Persist file to backend storage
   Returns: (file_id: ULID, sha256: hex, storage_path: str)
   Features:
   - Generates unique ULID for file
   - Preserves original file extension
   - Organizes by artifact ID
   - Calculates checksums automatically
   HTTP Context: Called by POST /api/models/upload-file (201)

3. retrieve_file(storage_path: str) → Optional[bytes]
   Purpose: Load file from backend storage
   Returns: File content as bytes or None if not found
   Used: Download operations, verification checks
   HTTP Context: Called by GET /api/models/{id}/download

4. delete_file(storage_path: str) → bool
   Purpose: Remove file from backend storage
   Returns: True if deleted, False on error
   Used: Artifact deletion, cleanup operations
   Spec Note: Deletion endpoints in Phase 5

5. verify_checksum(storage_path: str, expected_sha256: str) → bool
   Purpose: Verify file integrity using SHA256
   Returns: True if checksum matches, False otherwise
   Used: POST /api/models/validate endpoint
   Security: Detects corruption or tampering

6. get_download_url(storage_path: str) → str
   Purpose: Generate URL for file retrieval
   Returns: HTTP URL or S3 presigned URL
   Formats:
   - Local: /api/models/download/{storage_path}
   - S3: https://bucket.s3.amazonaws.com/key?credentials...
   Used: In FileUploadResponse for download_url field

CHECKSUM FORMATS:
- SHA256: 64 hex characters (256 bits / 4 bits per char)
- MD5: 32 hex characters (128 bits / 4 bits per char)
- Examples:
  - SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  - MD5: d41d8cd98f00b204e9800998ecf8427e

FILE ID FORMAT:
- ULID (Universally Unique Lexicographically Sortable Identifier)
- 26 characters, base32 encoded
- Example: 01ARZ3NDEKTSV4RRFFQ69G5FAV
- Sortable by creation time (first 10 chars = timestamp)

DATABASE INTEGRATION:
- FileStorage table stores: id, artifact_id, filename, size_bytes, sha256_checksum, storage_location
- All file operations create/update FileStorage records
- Audit trail tracks all access via AuditEntry table

ERROR HANDLING:
- FileNotFoundError: 404 in responses
- S3 errors: Logged and converted to 500
- Checksum mismatches: 422 Unprocessable Entity

Spec Sections Referenced:
- Section 3.4: File upload and management requirements
- Section 3.3.2: FileStorage table schema
- Section 3.1: Authentication for all operations
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from ulid import ULID


class FileStorageService:
    """Service for managing model file uploads and storage."""

    def __init__(self, backend: str = "local", local_path: str = "./models", s3_bucket: Optional[str] = None):
        """
        Initialize file storage service.

        Args:
            backend: Storage backend ("local" or "s3")
            local_path: Path for local file storage
            s3_bucket: S3 bucket name (required if backend="s3")
        """
        self.backend = backend
        self.local_path = Path(local_path)
        self.s3_bucket = s3_bucket

        if backend == "local":
            self.local_path.mkdir(parents=True, exist_ok=True)

    async def calculate_checksums(self, file_bytes: bytes) -> Tuple[str, str]:
        """
        Calculate SHA256 and MD5 checksums for file.

        Args:
            file_bytes: File content as bytes

        Returns:
            Tuple of (sha256, md5) checksums as hex strings
        """
        sha256_hash = hashlib.sha256()
        md5_hash = hashlib.md5()

        sha256_hash.update(file_bytes)
        md5_hash.update(file_bytes)

        return sha256_hash.hexdigest(), md5_hash.hexdigest()

    async def store_file(
        self,
        file_bytes: bytes,
        filename: str,
        artifact_id: str
    ) -> Tuple[str, str, str]:
        """
        Store file in backend storage.

        Args:
            file_bytes: File content as bytes
            filename: Original filename
            artifact_id: Associated artifact ID

        Returns:
            Tuple of (file_id, checksum_sha256, storage_path)
        """
        file_id = str(ULID())
        sha256, md5 = await self.calculate_checksums(file_bytes)

        if self.backend == "local":
            storage_path = await self._store_local(file_bytes, file_id, artifact_id, filename)
        elif self.backend == "s3":
            storage_path = await self._store_s3(file_bytes, file_id, artifact_id, filename, sha256)
        else:
            raise ValueError(f"Unknown storage backend: {self.backend}")

        return file_id, sha256, storage_path

    async def _store_local(self, file_bytes: bytes, file_id: str, artifact_id: str, filename: str) -> str:
        """Store file locally."""
        # Create artifact-specific directory
        artifact_dir = self.local_path / artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # Store with ULID as name, keeping original extension
        ext = Path(filename).suffix
        file_path = artifact_dir / f"{file_id}{ext}"

        # Write file
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return str(file_path)

    async def _store_s3(self, file_bytes: bytes, file_id: str, artifact_id: str, filename: str, checksum: str) -> str:
        """Store file in S3."""
        # Construct S3 key
        ext = Path(filename).suffix
        s3_key = f"artifacts/{artifact_id}/{file_id}{ext}"

        try:
            import boto3
            s3_client = boto3.client("s3")
            s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=file_bytes,
                Metadata={
                    "sha256": checksum,
                    "original_name": filename,
                    "uploaded_at": datetime.utcnow().isoformat()
                }
            )
            return s3_key
        except ImportError:
            raise RuntimeError("boto3 not installed. Cannot use S3 backend.")
        except Exception as e:
            raise RuntimeError(f"Failed to store file in S3: {str(e)}")

    async def retrieve_file(self, storage_path: str) -> Optional[bytes]:
        """
        Retrieve file from storage.

        Args:
            storage_path: Path/key where file is stored

        Returns:
            File content as bytes, or None if not found
        """
        if self.backend == "local":
            return await self._retrieve_local(storage_path)
        elif self.backend == "s3":
            return await self._retrieve_s3(storage_path)
        else:
            raise ValueError(f"Unknown storage backend: {self.backend}")

    async def _retrieve_local(self, storage_path: str) -> Optional[bytes]:
        """Retrieve file from local storage."""
        file_path = Path(storage_path)
        if file_path.exists():
            with open(file_path, "rb") as f:
                return f.read()
        return None

    async def _retrieve_s3(self, storage_path: str) -> Optional[bytes]:
        """Retrieve file from S3."""
        try:
            import boto3

            s3_client = boto3.client("s3")
            response = s3_client.get_object(Bucket=self.s3_bucket, Key=storage_path)
            return response["Body"].read()  # type: ignore
        except ImportError:
            raise RuntimeError("boto3 not installed. Cannot use S3 backend.")
        except Exception as e:
            print(f"Failed to retrieve file from S3: {str(e)}")
            return None

    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            storage_path: Path/key where file is stored

        Returns:
            True if successful, False otherwise
        """
        if self.backend == "local":
            return await self._delete_local(storage_path)
        elif self.backend == "s3":
            return await self._delete_s3(storage_path)
        return False

    async def _delete_local(self, storage_path: str) -> bool:
        """Delete local file."""
        try:
            file_path = Path(storage_path)
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            print(f"Failed to delete local file: {str(e)}")
        return False

    async def _delete_s3(self, storage_path: str) -> bool:
        """Delete S3 object."""
        try:
            import boto3
            s3_client = boto3.client("s3")
            s3_client.delete_object(Bucket=self.s3_bucket, Key=storage_path)
            return True
        except Exception as e:
            print(f"Failed to delete S3 object: {str(e)}")
            return False

    async def verify_checksum(self, storage_path: str, expected_sha256: str) -> bool:
        """
        Verify file integrity using checksum.

        Args:
            storage_path: Path/key where file is stored
            expected_sha256: Expected SHA256 checksum

        Returns:
            True if checksum matches, False otherwise
        """
        file_bytes = await self.retrieve_file(storage_path)
        if file_bytes is None:
            return False

        actual_sha256, _ = await self.calculate_checksums(file_bytes)
        return actual_sha256 == expected_sha256

    def get_download_url(self, storage_path: str, expiration_hours: int = 24) -> str:
        """
        Get URL for downloading file.

        Args:
            storage_path: Path/key where file is stored
            expiration_hours: URL expiration time (for S3)

        Returns:
            Download URL
        """
        if self.backend == "local":
            # For local files, return HTTP path relative to storage root
            return f"/api/models/download/{storage_path}"
        elif self.backend == "s3":
            # Generate presigned S3 URL
            try:
                import boto3
                s3_client = boto3.client("s3")
                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.s3_bucket, "Key": storage_path},
                    ExpiresIn=expiration_hours * 3600
                )
                return url  # type: ignore
            except Exception as e:
                print(f"Failed to generate S3 URL: {str(e)}")
                return ""
        return ""
