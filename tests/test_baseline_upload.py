"""Test BASELINE upload endpoint - POST /artifact/{artifact_type}

Tests for OpenAPI v3.4.4 BASELINE artifact registration from URLs.
Run with: pytest tests/test_baseline_upload.py -v
"""

import pytest
from fastapi.testclient import TestClient


class TestBaselineUpload:
    """Test BASELINE artifact upload via POST /artifact/{artifact_type}"""

    def test_upload_model_success(self, client: TestClient, auth_token: str) -> None:
        """Test successful model artifact upload."""
        response = client.post(
            "/artifact/model",
            json={
                "url": "https://huggingface.co/bert-base-uncased/resolve/main/model.safetensors"
            },
            headers={"X-Authorization": auth_token},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["type"] == "model"
        assert data["metadata"]["id"] is not None
        assert (
            data["data"]["url"]
            == "https://huggingface.co/bert-base-uncased/resolve/main/model.safetensors"
        )
        assert "download_url" in data["data"]

    def test_upload_dataset_success(self, client: TestClient, auth_token: str) -> None:
        """Test successful dataset artifact upload."""
        response = client.post(
            "/artifact/dataset",
            json={
                "url": "https://huggingface.co/datasets/wikitext/resolve/main/wikitext-103-v1.zip"
            },
            headers={"X-Authorization": auth_token},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["type"] == "dataset"
        assert (
            data["data"]["url"]
            == "https://huggingface.co/datasets/wikitext/resolve/main/wikitext-103-v1.zip"
        )

    def test_upload_code_success(self, client: TestClient, auth_token: str) -> None:
        """Test successful code artifact upload."""
        response = client.post(
            "/artifact/code",
            json={
                "url": "https://github.com/huggingface/transformers/archive/main.zip"
            },
            headers={"X-Authorization": auth_token},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["type"] == "code"

    def test_upload_missing_auth(self, client: TestClient) -> None:
        """Test upload fails without authentication."""
        response = client.post(
            "/artifact/model", json={"url": "https://huggingface.co/bert-base-uncased"}
        )
        assert response.status_code == 403
        assert "X-Authorization" in response.json()["detail"]

    def test_upload_invalid_auth(self, client: TestClient) -> None:
        """Test upload fails with invalid token."""
        response = client.post(
            "/artifact/model",
            json={"url": "https://huggingface.co/bert-base-uncased"},
            headers={"X-Authorization": "bearer invalid_token"},
        )
        assert response.status_code == 403
        assert "Authentication failed" in response.json()["detail"]

    def test_upload_missing_url(self, client: TestClient, auth_token: str) -> None:
        """Test upload fails without URL."""
        response = client.post(
            "/artifact/model", json={}, headers={"X-Authorization": auth_token}
        )
        assert response.status_code == 422  # Validation error

    def test_upload_invalid_type(self, client: TestClient, auth_token: str) -> None:
        """Test upload fails with invalid artifact type."""
        response = client.post(
            "/artifact/invalid_type",
            json={"url": "https://example.com/model"},
            headers={"X-Authorization": auth_token},
        )
        assert response.status_code == 400
        assert "Invalid artifact type" in response.json()["detail"]

    def test_upload_response_structure(
        self, client: TestClient, auth_token: str
    ) -> None:
        """Test upload response has correct envelope structure."""
        response = client.post(
            "/artifact/model",
            json={"url": "https://example.com/model.pth"},
            headers={"X-Authorization": auth_token},
        )
        assert response.status_code == 201
        data = response.json()

        # Check envelope structure per spec
        assert "metadata" in data
        assert "data" in data

        # Check metadata fields
        assert "id" in data["metadata"]
        assert "name" in data["metadata"]
        assert "type" in data["metadata"]

        # Check data fields
        assert "url" in data["data"]
        assert "download_url" in data["data"]

    def test_upload_name_extraction(self, client: TestClient, auth_token: str) -> None:
        """Test artifact name is extracted from URL."""
        response = client.post(
            "/artifact/model",
            json={
                "url": "https://huggingface.co/bert-base-uncased/resolve/main/pytorch_model.bin"
            },
            headers={"X-Authorization": auth_token},
        )
        assert response.status_code == 201
        data = response.json()
        # Name should be extracted as last part of URL
        assert data["metadata"]["name"] == "pytorch_model.bin"

    def test_upload_multiple_artifacts(
        self, client: TestClient, auth_token: str
    ) -> None:
        """Test uploading multiple artifacts creates unique IDs."""
        response1 = client.post(
            "/artifact/model",
            json={"url": "https://example.com/model1.pth"},
            headers={"X-Authorization": auth_token},
        )
        assert response1.status_code == 201
        id1 = response1.json()["metadata"]["id"]

        response2 = client.post(
            "/artifact/model",
            json={"url": "https://example.com/model2.pth"},
            headers={"X-Authorization": auth_token},
        )
        assert response2.status_code == 201
        id2 = response2.json()["metadata"]["id"]

        # IDs should be different
        assert id1 != id2

    def test_upload_same_name_different_ids(
        self, client: TestClient, auth_token: str
    ) -> None:
        """Test artifacts with same name can have different IDs (per spec)."""
        url = "https://example.com/model.pth"

        response1 = client.post(
            "/artifact/model",
            json={"url": url},
            headers={"X-Authorization": auth_token},
        )
        assert response1.status_code == 201
        id1 = response1.json()["metadata"]["id"]

        response2 = client.post(
            "/artifact/model",
            json={"url": url},
            headers={"X-Authorization": auth_token},
        )
        assert response2.status_code == 201
        id2 = response2.json()["metadata"]["id"]

        # Names are same but IDs are unique per spec
        assert (
            response1.json()["metadata"]["name"] == response2.json()["metadata"]["name"]
        )
        assert id1 != id2
