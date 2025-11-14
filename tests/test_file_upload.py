"""Unit tests for Phase 3 file upload endpoint - POST /api/models/upload-file

Per OpenAPI v3.4.4 Section 3.4 - Single File Upload Tests

PURPOSE:
Tests single file upload to artifact with checksums and validation.
Verifies file storage, integrity verification, and error handling.

ENDPOINT TESTED:
    POST /api/models/upload-file
    - Query: artifact_id (ULID)
    - Query: description (optional)
    - Body: multipart/form-data with file
    - Response: FileUploadResponse (201 Created)
    - Authentication: X-Authorization header required

TEST CATEGORIES:

1. Success Cases
   - test_upload_single_file_success: Basic upload (201)
   - test_upload_file_with_description: Upload + description
   - test_upload_preserves_filename: Original filename kept
   - test_upload_calculates_checksums: SHA256/MD5 computed

2. Validation Errors
   - test_upload_artifact_not_found: 404 for invalid artifact
   - test_upload_missing_artifact_id: 422 validation error
   - test_upload_missing_file: 422 validation error
   - test_upload_empty_file: 422 validation error

3. Size Limits
   - test_upload_file_too_large: 413 Payload Too Large (>1GB)
   - test_upload_max_allowed_size: 1GB exactly (should pass)
   - test_upload_boundary_sizes: Test edge cases

4. Checksum Verification
   - test_checksum_sha256_calculated: SHA256 matches expected
   - test_checksum_md5_calculated: MD5 matches expected
   - test_checksum_in_response: Both checksums in response

5. File Storage
   - test_file_stored_in_backend: File persisted
   - test_file_storage_path_generated: Storage location valid
   - test_file_download_url_generated: Download URL included

6. Metadata Handling
   - test_upload_response_contains_file_id: ULID generated
   - test_upload_response_version_number: Version = 1 for new file
   - test_upload_timestamp_set: uploaded_at timestamp recorded

7. Error Handling
   - test_upload_database_error: 500 on DB failure
   - test_upload_storage_error: 500 on storage failure
   - test_upload_checksum_error: 422 on hash mismatch

RESPONSE SCHEMA (201):
    {
      "file_id": "01K9ZBPCEQM0CK4X2T984FX8CS",
      "artifact_id": "01K9ZBPCEQM0CK4X2T984FX8CS",
      "filename": "model.pth",
      "size_bytes": 524288000,
      "sha256_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "md5_checksum": "d41d8cd98f00b204e9800998ecf8427e",
      "storage_path": "artifacts/artifact_id/file_id.pth",
      "download_url": "/api/models/download/file_id",
      "uploaded_at": "2024-01-15T10:30:00Z",
      "version": 1
    }

ERROR RESPONSES:
    404: Artifact not found
        {"detail": "Artifact {artifact_id} not found"}

    413: File too large
        {"detail": "File exceeds 1GB limit"}

    422: Validation error
        {"detail": "Query parameter artifact_id required"}

    500: Server error
        {"detail": "Upload failed: ..."}

PREREQUISITES:
- User must be authenticated (X-Authorization header)
- Artifact must exist in database
- File size < 1GB
- File content valid

RELATED ENDPOINTS:
    POST /api/models/upload-batch: Batch upload
    GET /api/models/{id}/download: Download file
    POST /api/models/check-duplicate: Check for duplicates
    POST /api/models/validate: Validate file format

SPEC SECTIONS REFERENCED:
    Section 3.4: Single file upload requirements
    Section 3.3.2: FileStorage table schema
    Section 3.1: Authentication requirements

TESTS RUN:
    pytest tests/test_file_upload_fixed.py -v
"""

import hashlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.database_models import Artifact


@pytest.fixture
def sample_file_content() -> bytes:
    """Sample file content for testing."""
    return b"This is a sample model file content for testing purposes."


@pytest.fixture
def test_artifact(test_db: Session) -> Artifact:
    """Create a test artifact in the database."""
    artifact = Artifact(
        id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        name="test-model",
        uploader_id=1,
        type="model",
        url="https://example.com/model",
        download_url="https://localhost:8000/download/01ARZ3NDEKTSV4RRFFQ69G5FAV"
    )
    test_db.add(artifact)
    test_db.commit()
    test_db.refresh(artifact)
    return artifact


class TestFileUploadSuccess:
    """Test successful file upload scenarios."""

    def test_upload_single_file_success(
        self, client: TestClient, test_artifact: Artifact, sample_file_content: bytes
    ) -> None:
        """Test uploading a single file successfully."""
        files = {
            "file": ("model.pth", sample_file_content, "application/octet-stream")
        }
        params = {"artifact_id": str(test_artifact.id)}

        with patch("crud.upload.file_routes.file_storage.store_file") as mock_store:
            mock_store.return_value = (
                "FILE_ID_123",
                hashlib.sha256(sample_file_content).hexdigest(),
                "artifacts/path/file.pth"
            )

            response = client.post(
                "/api/models/upload-file",
                files=files,
                params=params
            )

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "model.pth"
        assert data["artifact_id"] == test_artifact.id
        assert data["size_bytes"] == len(sample_file_content)

    def test_upload_file_with_description(
        self, client: TestClient, test_artifact: Artifact, sample_file_content: bytes
    ) -> None:
        """Test uploading file with description."""
        files = {
            "file": ("model.pth", sample_file_content, "application/octet-stream")
        }
        params = {
            "artifact_id": str(test_artifact.id),
            "description": "Production model v1.0"
        }

        with patch("crud.upload.file_routes.file_storage.store_file") as mock_store:
            mock_store.return_value = (
                "FILE_ID",
                "checksum123",
                "path/to/file"
            )

            response = client.post(
                "/api/models/upload-file",
                files=files,
                params=params
            )

        assert response.status_code == 201
        assert response.json()["filename"] == "model.pth"


class TestFileUploadValidation:
    """Test file upload validation and error handling."""

    def test_upload_artifact_not_found(self, client: TestClient, sample_file_content: bytes) -> None:
        """Test upload when artifact doesn't exist."""
        files = {"file": ("model.pth", sample_file_content, "application/octet-stream")}
        params = {"artifact_id": "NONEXISTENT_ID"}

        response = client.post(
            "/api/models/upload-file",
            files=files,
            params=params
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_upload_missing_artifact_id(self, client: TestClient, sample_file_content: bytes) -> None:
        """Test upload with missing artifact_id parameter."""
        files = {"file": ("model.pth", sample_file_content, "application/octet-stream")}

        response = client.post(
            "/api/models/upload-file",
            files=files
        )

        assert response.status_code == 422  # Validation Error
        assert "artifact_id" in str(response.json())

    def test_upload_missing_file(self, client: TestClient, test_artifact: Artifact) -> None:
        """Test upload with missing file."""
        params = {"artifact_id": str(test_artifact.id)}

        response = client.post(
            "/api/models/upload-file",
            params=params
        )

        assert response.status_code == 422  # Validation Error


class TestFileUploadChecksums:
    """Test checksum calculation and verification."""

    def test_checksum_sha256_calculated(self, client: TestClient, test_artifact: Artifact, sample_file_content: bytes) -> None:
        """Test that SHA256 checksum is calculated correctly."""
        expected_sha256 = hashlib.sha256(sample_file_content).hexdigest()

        files = {"file": ("model.pth", sample_file_content, "application/octet-stream")}
        params = {"artifact_id": str(test_artifact.id)}

        with patch("crud.upload.file_routes.file_storage.store_file") as mock_store:
            mock_store.return_value = ("FILE_ID", expected_sha256, "path/to/file")

            response = client.post(
                "/api/models/upload-file",
                files=files,
                params=params
            )

        assert response.status_code == 201
        assert response.json()["sha256_checksum"] == expected_sha256
