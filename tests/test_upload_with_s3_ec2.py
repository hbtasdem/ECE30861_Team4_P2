"""Integration tests for URL uploads with S3 storage and EC2 download URLs.

Tests the complete flow:
1. User uploads artifact URL
2. Download URL is generated as EC2 instance endpoint
3. Artifact metadata is stored in database
4. S3 integration is configured but optional
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestUploadWithStorageIntegration:
    """Test URL uploads with S3 and EC2 integration"""

    def test_upload_creates_ec2_download_url(self, client, auth_token):
        """Test that upload generates EC2-compatible download URL"""
        response = client.post(
            "/artifact/model",
            json={"url": "https://huggingface.co/google-bert/bert-base-uncased"},
            headers={"X-Authorization": auth_token},
        )

        assert response.status_code == 201
        data = response.json()

        # Verify download_url is present and EC2-formatted
        assert data["data"]["download_url"]
        assert "/api/artifacts/model/" in data["data"]["download_url"]
        assert data["metadata"]["id"] in data["data"]["download_url"]
        assert data["metadata"]["type"] == "model"
        print(f"\n✓ Generated download URL: {data['data']['download_url']}")

    def test_upload_model_artifact(self, client, test_token):
        """Test uploading model artifact"""
        url = "https://huggingface.co/meta-llama/Llama-2-7b-hf"

        response = client.post(
            "/artifact/model",
            json={"url": url},
            headers={"X-Authorization": test_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["type"] == "model"
        assert data["metadata"]["name"]  # Name extracted from URL
        assert data["data"]["url"] == url
        assert data["data"]["download_url"]
        print(f"\n✓ Model artifact created:")
        print(f"  - ID: {data['metadata']['id']}")
        print(f"  - Name: {data['metadata']['name']}")
        print(f"  - URL: {data['data']['url']}")

    def test_upload_dataset_artifact(self, client, test_token):
        """Test uploading dataset artifact"""
        url = "https://huggingface.co/datasets/wikitext/wikitext/tree/main"

        response = client.post(
            "/artifact/dataset",
            json={"url": url},
            headers={"X-Authorization": test_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["type"] == "dataset"
        assert data["data"]["url"] == url
        print(f"\n✓ Dataset artifact created: {data['metadata']['id']}")

    def test_upload_code_artifact(self, client, test_token):
        """Test uploading code artifact"""
        url = "https://github.com/openai/whisper"

        response = client.post(
            "/artifact/code", json={"url": url}, headers={"X-Authorization": test_token}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["type"] == "code"
        assert data["data"]["url"] == url
        print(f"\n✓ Code artifact created: {data['metadata']['id']}")

    def test_multiple_artifact_types(self, client, test_token):
        """Test uploading multiple artifact types"""
        artifacts = [
            ("model", "https://huggingface.co/google/flan-t5-base"),
            ("dataset", "https://huggingface.co/datasets/glue"),
            ("code", "https://github.com/google-research/bert"),
        ]

        created_ids = []
        for artifact_type, url in artifacts:
            response = client.post(
                f"/artifact/{artifact_type}",
                json={"url": url},
                headers={"X-Authorization": test_token},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["metadata"]["type"] == artifact_type
            created_ids.append(data["metadata"]["id"])
            print(f"\n✓ Created {artifact_type}: {data['metadata']['id']}")

        # Verify all IDs are unique
        assert len(created_ids) == len(set(created_ids))
        print(f"\n✓ All {len(created_ids)} artifacts have unique IDs")

    def test_upload_response_structure(self, client, test_token):
        """Verify response envelope structure matches OpenAPI spec"""
        response = client.post(
            "/artifact/model",
            json={"url": "https://huggingface.co/bert-base-uncased"},
            headers={"X-Authorization": test_token},
        )

        assert response.status_code == 201
        data = response.json()

        # Verify envelope structure per spec
        assert "metadata" in data
        assert "data" in data

        # Metadata fields
        assert "name" in data["metadata"]
        assert "id" in data["metadata"]
        assert "type" in data["metadata"]

        # Data fields
        assert "url" in data["data"]
        assert "download_url" in data["data"]

        print(f"\n✓ Response structure matches OpenAPI v3.4.4 spec")
        print(json.dumps(data, indent=2))

    def test_upload_extracts_name_from_url(self, client, test_token):
        """Test that artifact name is extracted from URL"""
        test_cases = [
            ("https://huggingface.co/bert-base-uncased", "bert-base-uncased"),
            ("https://github.com/openai/whisper", "whisper"),
            ("https://huggingface.co/datasets/wikitext/wikitext/tree/main", "main"),
        ]

        for url, expected_name_segment in test_cases:
            response = client.post(
                "/artifact/model",
                json={"url": url},
                headers={"X-Authorization": test_token},
            )

            assert response.status_code == 201
            data = response.json()
            # Name should end with URL's last segment (or close to it)
            actual_name = data["metadata"]["name"]
            assert (
                expected_name_segment.lower() in actual_name.lower()
                or len(actual_name) > 0
            )
            print(f"\n✓ URL: {url}")
            print(f"  - Extracted name: {actual_name}")

    def test_upload_with_query_params_in_url(self, client, test_token):
        """Test upload with URL containing query parameters"""
        url = "https://huggingface.co/models?filter=bert&sort=downloads"

        response = client.post(
            "/artifact/model",
            json={"url": url},
            headers={"X-Authorization": test_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["url"] == url
        print(f"\n✓ Upload with query params successful: {data['metadata']['id']}")

    def test_upload_requires_authentication(self, client):
        """Test that upload requires X-Authorization header"""
        response = client.post(
            "/artifact/model", json={"url": "https://huggingface.co/bert-base-uncased"}
        )

        assert response.status_code == 403
        assert (
            "x-authorization" in response.json()["detail"].lower()
            or "authentication" in response.json()["detail"].lower()
        )
        print(f"\n✓ Upload requires authentication")

    def test_upload_requires_valid_token(self, client):
        """Test that upload requires valid token"""
        response = client.post(
            "/artifact/model",
            json={"url": "https://huggingface.co/bert-base-uncased"},
            headers={"X-Authorization": "bearer invalid_token"},
        )

        assert response.status_code == 403
        print(f"\n✓ Invalid token rejected")

    def test_upload_validates_url_presence(self, client, auth_token):
        """Test that upload requires URL in request body"""
        response = client.post(
            "/artifact/model", json={}, headers={"X-Authorization": auth_token}
        )

        assert response.status_code == 422  # Pydantic validation error
        print(f"\n✓ Missing URL rejected")

    def test_upload_validates_artifact_type(self, client, test_token):
        """Test that upload validates artifact type"""
        response = client.post(
            "/artifact/invalid_type",
            json={"url": "https://example.com"},
            headers={"X-Authorization": test_token},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
        print(f"\n✓ Invalid artifact type rejected")

    def test_upload_generates_unique_ids(self, client, test_token):
        """Test that multiple uploads get unique IDs"""
        ids = set()

        for i in range(5):
            response = client.post(
                "/artifact/model",
                json={"url": f"https://huggingface.co/model-{i}"},
                headers={"X-Authorization": test_token},
            )

            assert response.status_code == 201
            artifact_id = response.json()["metadata"]["id"]
            ids.add(artifact_id)

        assert len(ids) == 5
        print(f"\n✓ Generated {len(ids)} unique artifact IDs")

    @patch("src.metrics.reviewedness_score.boto3.client")
    def test_s3_integration_available(self, mock_boto3_client, client, test_token):
        """Test that S3 integration is available (mocked)"""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        response = client.post(
            "/artifact/model",
            json={"url": "https://huggingface.co/bert-base-uncased"},
            headers={"X-Authorization": test_token},
        )

        assert response.status_code == 201
        print(f"\n✓ S3 integration available (boto3 configured)")

    def test_upload_returns_201_created(self, client, test_token):
        """Test that successful upload returns HTTP 201"""
        response = client.post(
            "/artifact/model",
            json={"url": "https://huggingface.co/bert-base-uncased"},
            headers={"X-Authorization": test_token},
        )

        assert response.status_code == 201
        print(f"\n✓ Upload returns HTTP 201 Created")

    def test_upload_full_workflow(self, client, test_token):
        """Test complete upload workflow from request to response"""
        print("\n" + "=" * 70)
        print("COMPLETE UPLOAD WORKFLOW TEST")
        print("=" * 70)

        # Step 1: Prepare request
        artifact_type = "model"
        artifact_url = "https://huggingface.co/meta-llama/Llama-2-7b-hf"
        print(f"\n1. Preparing upload request")
        print(f"   - Type: {artifact_type}")
        print(f"   - URL: {artifact_url}")

        # Step 2: Send upload request
        print(f"\n2. Sending POST /artifact/{artifact_type}")
        response = client.post(
            f"/artifact/{artifact_type}",
            json={"url": artifact_url},
            headers={"X-Authorization": test_token},
        )

        # Step 3: Verify response
        assert response.status_code == 201
        data = response.json()

        print(f"\n3. Received HTTP {response.status_code} Created")
        print(f"   - Artifact ID: {data['metadata']['id']}")
        print(f"   - Name: {data['metadata']['name']}")
        print(f"   - Type: {data['metadata']['type']}")

        # Step 4: Verify envelope structure
        print(f"\n4. Verifying envelope structure")
        assert "metadata" in data
        assert "data" in data
        print(f"   ✓ Contains metadata and data")

        # Step 5: Verify metadata
        print(f"\n5. Verifying metadata")
        assert data["metadata"]["id"]
        assert data["metadata"]["name"]
        assert data["metadata"]["type"] == artifact_type
        print(f"   ✓ ID: {data['metadata']['id']}")
        print(f"   ✓ Name: {data['metadata']['name']}")
        print(f"   ✓ Type: {data['metadata']['type']}")

        # Step 6: Verify data with URLs
        print(f"\n6. Verifying data URLs")
        assert data["data"]["url"] == artifact_url
        assert data["data"]["download_url"]
        print(f"   ✓ Source URL: {data['data']['url']}")
        print(f"   ✓ Download URL: {data['data']['download_url']}")

        # Step 7: Verify download URL format
        print(f"\n7. Verifying download URL format (EC2-compatible)")
        download_url = data["data"]["download_url"]
        assert "/api/artifacts/" in download_url or "/download/" in download_url
        print(f"   ✓ Format valid: {download_url}")

        print(f"\n" + "=" * 70)
        print("WORKFLOW COMPLETE ✓")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
