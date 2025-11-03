"""
Comprehensive test suite for the upload endpoint.
Run with: pytest tests/test_upload_endpoint.py -v
Or: pytest tests/test_upload_endpoint.py -v -k "test_name" (for specific test)
"""

import io
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import app
from src.auth import clear_test_user, set_test_user
from src.database import get_db
from src.models import Base, Model, ModelMetadata, User


# Setup test database
@pytest.fixture
def test_db() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Create test user
    test_user = User(id=1, username="testuser", email="test@example.com", is_admin=False)
    db.add(test_user)
    db.commit()

    yield db
    db.close()


test_user = User(id=1, username="testuser", email="test@example.com", is_admin=False)


@pytest.fixture
def client(test_db: Session) -> TestClient:
    """Create a test client with test database and mocked auth."""
    # Set test user using the auth module's function
    set_test_user(test_user)

    def override_get_db() -> Generator[Session, None, None]:
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    yield client
    
    # Clean up
    clear_test_user()
    app.dependency_overrides.clear()


@pytest.fixture
def sample_zip_file() -> io.BytesIO:
    """Create a minimal valid ZIP file for testing."""
    # This is a valid ZIP file header (minimal ZIP)
    zip_content = (
        b"PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00test.txt"
        b"test content"
    )
    return io.BytesIO(zip_content)


class TestUploadEndpointBasic:
    """Basic upload endpoint tests."""

    def test_upload_success(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test successful model upload with all required fields."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={
                "name": "MyAwesomeModel",
                "description": "A test model for unit testing",
                "version": "1.0.0",
                "is_sensitive": False,
            },
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Model uploaded successfully"
        assert data["model_id"] is not None
        assert data["file_size"] > 0
        assert "model" in data["file_path"]

    def test_upload_minimal_fields(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload with only required fields."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={"name": "MinimalModel"},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] is not None

    def test_upload_with_metadata(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload with JSON metadata."""
        sample_zip_file.seek(0)
        metadata = {"framework": "PyTorch", "task": "classification", "accuracy": 0.95}
        response = client.post(
            "/api/models/upload",
            data={
                "name": "ModelWithMetadata",
                "metadata": json.dumps(metadata),
            },
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200

    def test_upload_sensitive_model(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test uploading a sensitive model."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={
                "name": "SensitiveModel",
                "is_sensitive": True,
            },
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200


class TestUploadEndpointValidation:
    """Test validation and error handling."""

    def test_upload_missing_file(self, client: TestClient) -> None:
        """Test upload fails when file is missing."""
        response = client.post(
            "/api/models/upload",
            data={"name": "NoFileModel"},
        )
        assert response.status_code == 422

    def test_upload_missing_model_name(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload fails when model name is missing."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 422

    def test_upload_non_zip_file(self, client: TestClient) -> None:
        """Test upload rejects non-ZIP files."""
        response = client.post(
            "/api/models/upload",
            data={"name": "BadFileType"},
            files={"file": ("model.txt", io.BytesIO(b"not a zip"), "text/plain")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Only .zip files are allowed" in data["detail"]

    def test_upload_invalid_metadata_json(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload with invalid JSON metadata is handled gracefully."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={
                "name": "BadMetadata",
                "metadata": "not valid json {]",
            },
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        # Should still succeed, just skip invalid metadata
        assert response.status_code == 200

    def test_upload_empty_zip_file(self, client: TestClient) -> None:
        """Test upload with empty ZIP file."""
        empty_zip = io.BytesIO(
            b"PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        response = client.post(
            "/api/models/upload",
            data={"name": "EmptyZipModel"},
            files={"file": ("empty.zip", empty_zip, "application/zip")},
        )
        assert response.status_code == 200


class TestUploadEndpointVersioning:
    """Test different version formats."""

    def test_upload_custom_version(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload with custom version number."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={
                "name": "VersionedModel",
                "version": "2.5.3-beta",
            },
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200

    def test_upload_default_version(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload uses default version when not specified."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={"name": "DefaultVersionModel"},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200
        # Could also verify it defaults to 1.0.0 in database


class TestUploadEndpointEdgeCases:
    """Test edge cases and special scenarios."""

    def test_upload_long_model_name(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload with very long model name."""
        sample_zip_file.seek(0)
        long_name = "A" * 200  # Very long name
        response = client.post(
            "/api/models/upload",
            data={"name": long_name},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200

    def test_upload_special_characters_in_name(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload with special characters in model name."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={"name": "Model-123_v2.0@Beta!"},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200

    def test_upload_unicode_model_name(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload with unicode characters in model name."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={"name": "模型_Model_モデル"},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200

    def test_upload_multiple_sequential(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test uploading multiple models sequentially."""
        model_ids = []
        for i in range(3):
            sample_zip_file.seek(0)
            response = client.post(
                "/api/models/upload",
                data={"name": f"SequentialModel{i}"},
                files={"file": ("model.zip", sample_zip_file, "application/zip")},
            )
            assert response.status_code == 200
            model_ids.append(response.json()["model_id"])

        # Verify all IDs are different
        assert len(set(model_ids)) == 3


class TestUploadResponseStructure:
    """Test response structure and data integrity."""

    def test_upload_response_fields(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test upload response contains all required fields."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={"name": "ResponseTestModel"},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "message" in data
        assert "model_id" in data
        assert "file_path" in data
        assert "file_size" in data

        # Verify field types
        assert isinstance(data["message"], str)
        assert isinstance(data["model_id"], int)
        assert isinstance(data["file_path"], str)
        assert isinstance(data["file_size"], int)

    def test_upload_model_id_is_positive(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test that model_id is a positive integer."""
        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={"name": "PositiveIdModel"},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200
        model_id = response.json()["model_id"]
        assert model_id > 0

    def test_upload_file_size_accuracy(self, client: TestClient, sample_zip_file: io.BytesIO) -> None:
        """Test that reported file_size matches actual file size."""
        sample_zip_file.seek(0)
        file_content = sample_zip_file.read()
        actual_size = len(file_content)

        sample_zip_file.seek(0)
        response = client.post(
            "/api/models/upload",
            data={"name": "FileSizeTestModel"},
            files={"file": ("model.zip", sample_zip_file, "application/zip")},
        )
        assert response.status_code == 200
        reported_size = response.json()["file_size"]
        assert reported_size == actual_size


# ============================================================================
# Test Runner Configuration
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║        Upload Endpoint Test Suite - Quick Reference          ║
    ╚══════════════════════════════════════════════════════════════╝

    Run all tests:
        pytest tests/test_upload_endpoint.py -v

    Run specific test class:
        pytest tests/test_upload_endpoint.py::TestUploadEndpointBasic -v

    Run specific test:
        pytest tests/test_upload_endpoint.py::TestUploadEndpointBasic::test_upload_success -v

    Run with coverage:
        pytest tests/test_upload_endpoint.py --cov=src.upload --cov-report=html

    Run in quiet mode (only show failures):
        pytest tests/test_upload_endpoint.py -q

    Run with verbose output and print statements:
        pytest tests/test_upload_endpoint.py -v -s

    Test Categories:
    ├── TestUploadEndpointBasic      - Happy path scenarios
    ├── TestUploadEndpointValidation - Error handling & validation
    ├── TestUploadEndpointVersioning - Version format handling
    ├── TestUploadEndpointEdgeCases  - Special cases & boundaries
    └── TestUploadResponseStructure  - Response validation

    """)
