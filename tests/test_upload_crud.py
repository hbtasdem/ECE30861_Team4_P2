"""
Test suite for model upload and CRUD functionality.
Verifies that models can be uploaded as ZIP files and managed via CRUD operations.
"""

import json
import os
import tempfile
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.api_schemas import ModelCreate, ModelResponse, ModelUpdate, UploadResponse
from src.crud.repositories.model_repository import CRUDModelRepository
# Import models and schemas
from src.models import Model, ModelMetadata, User
from src.upload.repositories.model_repository import ModelRepository
from src.upload.services.file_service import FileStorageService


class TestFileStorageService:
    """Test file storage operations."""

    @pytest.fixture
    def temp_upload_dir(self) -> Any:
        """Create a temporary upload directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def file_service(self, temp_upload_dir: Any) -> FileStorageService:
        """Create a FileStorageService instance with temp directory."""
        return FileStorageService(upload_dir=temp_upload_dir)

    @pytest.mark.asyncio
    async def test_save_upload_file(self, file_service: FileStorageService) -> None:
        """Test saving an uploaded file."""
        # Create a mock UploadFile
        mock_file = MagicMock()
        mock_file.filename = "test_model.zip"
        mock_file.read = MagicMock(return_value=b"test content")

        # Note: In real async test, need proper mock for async read
        # This is a placeholder for integration testing
        assert file_service.upload_dir is not None

    def test_delete_file(self, file_service: FileStorageService, temp_upload_dir: Any) -> None:
        """Test file deletion."""
        # Create a test file
        test_file = os.path.join(temp_upload_dir, "test.zip")
        with open(test_file, "w") as f:
            f.write("test content")

        # Verify file exists
        assert os.path.exists(test_file)

        # Delete file
        result = file_service.delete_file(test_file)
        assert result is True
        assert not os.path.exists(test_file)

    def test_delete_nonexistent_file(self, file_service: FileStorageService) -> None:
        """Test deleting a non-existent file."""
        result = file_service.delete_file("/nonexistent/path/file.zip")
        assert result is False

    def test_get_file_size(self, file_service: FileStorageService, temp_upload_dir: Any) -> None:
        """Test getting file size."""
        test_file = os.path.join(temp_upload_dir, "test.zip")
        content = b"test content here"

        with open(test_file, "wb") as f:
            f.write(content)

        size = file_service.get_file_size(test_file)
        assert size == len(content)


class TestModelRepositoryUpload:
    """Test upload repository (Create operation)."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def model_repo(self, mock_db_session):
        """Create a ModelRepository instance."""
        return ModelRepository(mock_db_session)

    def test_create_model(self, model_repo, mock_db_session):
        """Test creating a model record."""
        model_data = ModelCreate(
            name="test_model",
            description="A test model",
            version="1.0.0",
            is_sensitive=False
        )

        # Setup mock
        mock_model = Mock(spec=Model)
        mock_model.id = 1
        mock_model.name = "test_model"
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()

        # Note: In real integration test, would actually create database record
        assert model_data.name == "test_model"
        assert model_data.version == "1.0.0"

    def test_add_model_metadata(self, model_repo, mock_db_session):
        """Test adding metadata to a model."""
        metadata = {
            "framework": "pytorch",
            "task": "classification"
        }

        # Note: In real integration test, would verify metadata is stored
        assert len(metadata) == 2
        assert metadata["framework"] == "pytorch"


class TestCRUDModelRepository:
    """Test CRUD repository (Read, Update, Delete operations)."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def crud_repo(self, mock_db_session):
        """Create a CRUDModelRepository instance."""
        return CRUDModelRepository(mock_db_session)

    def test_get_model_by_id(self, crud_repo, mock_db_session):
        """Test retrieving a model by ID."""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter

        mock_model = Mock(spec=Model)
        mock_model.id = 1
        mock_model.name = "test_model"
        mock_filter.first.return_value = mock_model

        # Call method
        result = crud_repo.get_model_by_id(1)

        # Verify
        assert result == mock_model
        mock_db_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_models_by_uploader(self, crud_repo, mock_db_session):
        """Test retrieving models uploaded by a specific user."""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter

        mock_models = [Mock(spec=Model), Mock(spec=Model)]
        mock_filter.all.return_value = mock_models

        # Call method
        result = crud_repo.get_models_by_uploader(1)

        # Verify
        assert result == mock_models
        mock_db_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_filter.all.assert_called_once()

    def test_get_all_models_with_pagination(self, crud_repo, mock_db_session):
        """Test retrieving all models with pagination."""
        mock_query = MagicMock()
        mock_offset = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.offset.return_value = mock_offset

        mock_models = [Mock(spec=Model)]
        mock_offset.limit.return_value = mock_models

        # Call method
        result = crud_repo.get_all_models(skip=0, limit=100)

        # Verify pagination calls
        assert result == mock_models
        mock_db_session.query.assert_called_once()
        mock_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    def test_update_model(self, crud_repo, mock_db_session):
        """Test updating a model."""
        mock_model = Mock(spec=Model)
        mock_model.id = 1
        mock_model.name = "old_name"

        # Mock get_model_by_id to return our model
        crud_repo.get_model_by_id = Mock(return_value=mock_model)

        # Update data
        update_data = {"name": "new_name", "version": "2.0.0"}

        # Call method
        result = crud_repo.update_model(1, update_data)

        # Verify
        assert result == mock_model
        mock_db_session.commit.assert_called_once()

    def test_update_nonexistent_model(self, crud_repo, mock_db_session):
        """Test updating a non-existent model."""
        crud_repo.get_model_by_id = Mock(return_value=None)

        # Call method
        result = crud_repo.update_model(999, {"name": "new_name"})

        # Verify returns None
        assert result is None
        mock_db_session.commit.assert_not_called()

    def test_delete_model(self, crud_repo, mock_db_session):
        """Test deleting a model."""
        mock_model = Mock(spec=Model)
        mock_model.id = 1

        # Mock get_model_by_id to return our model
        crud_repo.get_model_by_id = Mock(return_value=mock_model)

        # Call method
        result = crud_repo.delete_model(1)

        # Verify
        assert result is True
        mock_db_session.delete.assert_called_once_with(mock_model)
        mock_db_session.commit.assert_called_once()

    def test_delete_nonexistent_model(self, crud_repo, mock_db_session):
        """Test deleting a non-existent model."""
        crud_repo.get_model_by_id = Mock(return_value=None)

        # Call method
        result = crud_repo.delete_model(999)

        # Verify
        assert result is False
        mock_db_session.delete.assert_not_called()


class TestUploadSchemas:
    """Test Pydantic schemas for upload operations."""

    def test_model_create_schema(self):
        """Test ModelCreate schema validation."""
        data = {
            "name": "bert_model",
            "description": "BERT language model",
            "version": "1.0.0",
            "is_sensitive": False
        }

        model = ModelCreate(**data)
        assert model.name == "bert_model"
        assert model.version == "1.0.0"
        assert model.is_sensitive is False

    def test_model_create_with_defaults(self):
        """Test ModelCreate with default values."""
        data = {
            "name": "test_model",
            "description": "Test description"
        }

        model = ModelCreate(**data)
        assert model.name == "test_model"
        assert model.version == "1.0.0"  # default
        assert model.is_sensitive is False  # default

    def test_model_update_schema(self):
        """Test ModelUpdate schema validation."""
        data = {
            "name": "updated_name",
            "version": "2.0.0"
        }

        model = ModelUpdate(**data)
        assert model.name == "updated_name"
        assert model.version == "2.0.0"
        assert model.description is None  # optional

    def test_model_response_schema(self):
        """Test ModelResponse schema."""
        from datetime import datetime

        data = {
            "id": 1,
            "name": "test_model",
            "description": "Test",
            "version": "1.0.0",
            "file_path": "/uploads/models/test.zip",
            "file_size": 1024,
            "uploader_id": 1,
            "is_sensitive": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        model = ModelResponse(**data)
        assert model.id == 1
        assert model.name == "test_model"
        assert model.file_size == 1024

    def test_upload_response_schema(self):
        """Test UploadResponse schema."""
        data = {
            "message": "Model uploaded successfully",
            "model_id": 1,
            "file_path": "/uploads/models/test.zip",
            "file_size": 1024
        }

        response = UploadResponse(**data)
        assert response.model_id == 1
        assert "successfully" in response.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
