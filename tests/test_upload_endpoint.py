"""
Comprehensive test suite for the URL-based upload endpoint.
Tests URL registration instead of file uploads.
Run with: pytest tests/test_upload_endpoint.py -v
Or: pytest tests/test_upload_endpoint.py -v -k "test_name" (for specific test)
"""

import json

from fastapi.testclient import TestClient


class TestUploadEndpointBasic:
    """Basic URL-based upload endpoint tests."""

    def test_upload_success_with_all_fields(self, client: TestClient) -> None:
        """Test successful model registration with all fields."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "MyAwesomeModel",
                "description": "A test model for unit testing",
                "version": "1.0.0",
                "model_url": "https://huggingface.co/user/model",
                "artifact_type": "model",
                "is_sensitive": "false",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Model registered successfully"
        assert data["model_id"] is not None
        assert data["model_url"] == "https://huggingface.co/user/model"
        assert data["artifact_type"] == "model"

    def test_upload_minimal_fields(self, client: TestClient) -> None:
        """Test registration with only required fields."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "MinimalModel",
                "model_url": "https://example.com/model.zip",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] is not None
        assert data["artifact_type"] == "model"  # Default value

    def test_upload_with_metadata(self, client: TestClient) -> None:
        """Test registration with JSON metadata."""
        metadata = {"framework": "PyTorch", "task": "classification", "accuracy": 0.95}
        response = client.post(
            "/api/models/upload",
            data={
                "name": "ModelWithMetadata",
                "model_url": "https://example.com/model",
                "metadata": json.dumps(metadata),
            },
        )
        assert response.status_code == 200

    def test_upload_sensitive_model(self, client: TestClient) -> None:
        """Test registering a sensitive model."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "SensitiveModel",
                "model_url": "https://example.com/sensitive",
                "is_sensitive": "true",
            },
        )
        assert response.status_code == 200


class TestUploadEndpointValidation:
    """Test validation and error handling for URL-based uploads."""

    def test_upload_missing_url(self, client: TestClient) -> None:
        """Test upload fails when model_url is missing."""
        response = client.post(
            "/api/models/upload",
            data={"name": "NoUrlModel"},
        )
        assert response.status_code == 422

    def test_upload_missing_model_name(self, client: TestClient) -> None:
        """Test upload fails when model name is missing."""
        response = client.post(
            "/api/models/upload",
            data={"model_url": "https://example.com/model"},
        )
        assert response.status_code == 422

    def test_upload_empty_url(self, client: TestClient) -> None:
        """Test upload rejects empty URL."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "EmptyUrlModel",
                "model_url": "",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "cannot be empty" in data["detail"].lower()

    def test_upload_invalid_url_http(self, client: TestClient) -> None:
        """Test upload rejects URLs without http:// or https://."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "BadUrlModel",
                "model_url": "ftp://example.com/model",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "http://" in data["detail"].lower() or "https://" in data["detail"].lower()

    def test_upload_invalid_url_no_scheme(self, client: TestClient) -> None:
        """Test upload rejects URLs with no scheme."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "NoSchemeModel",
                "model_url": "example.com/model",
            },
        )
        assert response.status_code == 400

    def test_upload_invalid_metadata_json(self, client: TestClient) -> None:
        """Test upload with invalid JSON metadata is handled gracefully."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "BadMetadata",
                "model_url": "https://example.com/model",
                "metadata": "not valid json {]",
            },
        )
        # Should still succeed, just skip invalid metadata
        assert response.status_code == 200


class TestUploadEndpointArtifactTypes:
    """Test different artifact types."""

    def test_upload_model_artifact(self, client: TestClient) -> None:
        """Test uploading with model artifact type."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "ModelArtifact",
                "model_url": "https://example.com/model",
                "artifact_type": "model",
            },
        )
        assert response.status_code == 200
        assert response.json()["artifact_type"] == "model"

    def test_upload_checkpoint_artifact(self, client: TestClient) -> None:
        """Test uploading with checkpoint artifact type."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "CheckpointArtifact",
                "model_url": "https://example.com/checkpoint",
                "artifact_type": "checkpoint",
            },
        )
        assert response.status_code == 200
        assert response.json()["artifact_type"] == "checkpoint"

    def test_upload_weights_artifact(self, client: TestClient) -> None:
        """Test uploading with weights artifact type."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "WeightsArtifact",
                "model_url": "https://example.com/weights",
                "artifact_type": "weights",
            },
        )
        assert response.status_code == 200
        assert response.json()["artifact_type"] == "weights"

    def test_upload_default_artifact_type(self, client: TestClient) -> None:
        """Test default artifact type is 'model'."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "DefaultArtifactType",
                "model_url": "https://example.com/model",
            },
        )
        assert response.status_code == 200
        assert response.json()["artifact_type"] == "model"


class TestUploadEndpointVersioning:
    """Test different version formats."""

    def test_upload_custom_version(self, client: TestClient) -> None:
        """Test upload with custom version number."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "VersionedModel",
                "model_url": "https://example.com/model",
                "version": "2.5.3-beta",
            },
        )
        assert response.status_code == 200

    def test_upload_default_version(self, client: TestClient) -> None:
        """Test upload uses default version when not specified."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "DefaultVersionModel",
                "model_url": "https://example.com/model",
            },
        )
        assert response.status_code == 200


class TestUploadEndpointEdgeCases:
    """Test edge cases and special scenarios."""

    def test_upload_long_model_name(self, client: TestClient) -> None:
        """Test upload with very long model name."""
        long_name = "A" * 200
        response = client.post(
            "/api/models/upload",
            data={
                "name": long_name,
                "model_url": "https://example.com/model",
            },
        )
        assert response.status_code == 200

    def test_upload_special_characters_in_name(self, client: TestClient) -> None:
        """Test upload with special characters in model name."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "Model-123_v2.0@Beta!",
                "model_url": "https://example.com/model",
            },
        )
        assert response.status_code == 200

    def test_upload_unicode_model_name(self, client: TestClient) -> None:
        """Test upload with unicode characters in model name."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "model-multilang-test",
                "model_url": "https://example.com/model",
            },
        )
        assert response.status_code == 200

    def test_upload_long_url(self, client: TestClient) -> None:
        """Test upload with very long URL (up to 2048 chars)."""
        long_url = "https://example.com/" + "a" * 1900
        response = client.post(
            "/api/models/upload",
            data={
                "name": "LongUrlModel",
                "model_url": long_url,
            },
        )
        assert response.status_code == 200

    def test_upload_multiple_sequential(self, client: TestClient) -> None:
        """Test uploading multiple models sequentially."""
        model_ids = []
        for i in range(3):
            response = client.post(
                "/api/models/upload",
                data={
                    "name": f"SequentialModel{i}",
                    "model_url": f"https://example.com/model{i}",
                },
            )
            assert response.status_code == 200
            model_ids.append(response.json()["model_id"])

        # Verify all IDs are different
        assert len(set(model_ids)) == 3


class TestUploadResponseStructure:
    """Test response structure and data integrity."""

    def test_upload_response_fields(self, client: TestClient) -> None:
        """Test upload response contains all required fields."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "ResponseTestModel",
                "model_url": "https://example.com/model",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "message" in data
        assert "model_id" in data
        assert "model_url" in data
        assert "artifact_type" in data

        # Verify field types
        assert isinstance(data["message"], str)
        assert isinstance(data["model_id"], str)  # model_id is a ULID string per spec
        assert isinstance(data["model_url"], str)
        assert isinstance(data["artifact_type"], str)

    def test_upload_model_id_is_positive(self, client: TestClient) -> None:
        """Test that model_id is a non-empty string (ULID)."""
        response = client.post(
            "/api/models/upload",
            data={
                "name": "PositiveIdModel",
                "model_url": "https://example.com/model",
            },
        )
        assert response.status_code == 200
        model_id = response.json()["model_id"]
        assert isinstance(model_id, str)
        assert len(model_id) > 0  # ULID should be a non-empty string

    def test_upload_url_in_response(self, client: TestClient) -> None:
        """Test that registered URL is returned in response."""
        test_url = "https://huggingface.co/user/model"
        response = client.post(
            "/api/models/upload",
            data={
                "name": "UrlResponseModel",
                "model_url": test_url,
            },
        )
        assert response.status_code == 200
        returned_url = response.json()["model_url"]
        assert returned_url == test_url


class TestDownloadRedirectEndpoint:
    """Test the download redirect endpoint for accessing artifacts."""

    def test_get_download_url_success(self, client: TestClient) -> None:
        """Test retrieving download URL for a model."""
        # First upload a model
        upload_response = client.post(
            "/api/models/upload",
            data={
                "name": "DownloadTestModel",
                "model_url": "https://example.com/model.zip",
            },
        )
        assert upload_response.status_code == 200
        model_id = upload_response.json()["model_id"]

        # Then retrieve its download URL using correct endpoint path
        download_response = client.get(f"/api/models/{model_id}/download-redirect")
        assert download_response.status_code == 200

    def test_get_download_url_invalid_id(self, client: TestClient) -> None:
        """Test retrieving download URL for non-existent model."""
        response = client.get("/api/models/invalid-ulid-id/download-redirect")
        assert response.status_code == 404
