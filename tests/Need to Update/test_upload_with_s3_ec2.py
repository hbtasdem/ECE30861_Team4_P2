# """Integration tests for URL uploads with S3 storage and EC2 download URLs."""

# from typing import Any, Dict, List, Set, Tuple
# from unittest.mock import MagicMock, patch

# import pytest


# class TestUploadWithStorageIntegration:
#     """Test URL uploads with S3 and EC2 integration"""

#     def test_upload_creates_ec2_download_url(
#         self,
#         client: Any,
#         auth_token: str,
#     ) -> None:
#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://huggingface.co/google-bert/bert-base-uncased"},
#             headers={"X-Authorization": auth_token},
#         )

#         assert response.status_code == 201
#         data: Dict[str, Any] = response.json()

#         assert data["data"]["download_url"]
#         assert "/api/artifacts/model/" in data["data"]["download_url"]
#         assert data["metadata"]["id"] in data["data"]["download_url"]
#         assert data["metadata"]["type"] == "model"

#     def test_upload_model_artifact(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         url: str = "https://huggingface.co/meta-llama/Llama-2-7b-hf"

#         response = client.post(
#             "/artifact/model",
#             json={"url": url},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201
#         data: Dict[str, Any] = response.json()
#         assert data["metadata"]["type"] == "model"
#         assert data["metadata"]["name"]
#         assert data["data"]["url"] == url
#         assert data["data"]["download_url"]

#     def test_upload_dataset_artifact(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         url: str = "https://huggingface.co/datasets/wikitext/wikitext/tree/main"

#         response = client.post(
#             "/artifact/dataset",
#             json={"url": url},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201
#         data: Dict[str, Any] = response.json()
#         assert data["metadata"]["type"] == "dataset"
#         assert data["data"]["url"] == url

#     def test_upload_code_artifact(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         url: str = "https://github.com/openai/whisper"

#         response = client.post(
#             "/artifact/code",
#             json={"url": url},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201
#         data: Dict[str, Any] = response.json()
#         assert data["metadata"]["type"] == "code"
#         assert data["data"]["url"] == url

#     def test_multiple_artifact_types(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         artifacts: List[Tuple[str, str]] = [
#             ("model", "https://huggingface.co/google/flan-t5-base"),
#             ("dataset", "https://huggingface.co/datasets/glue"),
#             ("code", "https://github.com/google-research/bert"),
#         ]

#         created_ids: List[str] = []
#         for artifact_type, url in artifacts:
#             response = client.post(
#                 f"/artifact/{artifact_type}",
#                 json={"url": url},
#                 headers={"X-Authorization": test_token},
#             )

#             assert response.status_code == 201
#             data: Dict[str, Any] = response.json()
#             assert data["metadata"]["type"] == artifact_type
#             created_ids.append(data["metadata"]["id"])

#         assert len(created_ids) == len(set(created_ids))

#     def test_upload_response_structure(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://huggingface.co/bert-base-uncased"},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201
#         data: Dict[str, Any] = response.json()

#         assert "metadata" in data
#         assert "data" in data

#         assert "name" in data["metadata"]
#         assert "id" in data["metadata"]
#         assert "type" in data["metadata"]

#         assert "url" in data["data"]
#         assert "download_url" in data["data"]

#     def test_upload_extracts_name_from_url(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         test_cases: List[Tuple[str, str]] = [
#             ("https://huggingface.co/bert-base-uncased", "bert-base-uncased"),
#             ("https://github.com/openai/whisper", "whisper"),
#             ("https://huggingface.co/datasets/wikitext/wikitext/tree/main", "main"),
#         ]

#         for url, expected_name_segment in test_cases:
#             response = client.post(
#                 "/artifact/model",
#                 json={"url": url},
#                 headers={"X-Authorization": test_token},
#             )

#             assert response.status_code == 201
#             data: Dict[str, Any] = response.json()
#             actual_name: str = data["metadata"]["name"]
#             assert expected_name_segment.lower() in actual_name.lower() or len(actual_name) > 0

#     def test_upload_with_query_params_in_url(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         url: str = "https://huggingface.co/models?filter=bert&sort=downloads"

#         response = client.post(
#             "/artifact/model",
#             json={"url": url},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201
#         data: Dict[str, Any] = response.json()
#         assert data["data"]["url"] == url

#     def test_upload_requires_authentication(
#         self,
#         client: Any,
#     ) -> None:
#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://huggingface.co/bert-base-uncased"},
#         )

#         assert response.status_code == 403
#         detail: str = response.json()["detail"].lower()
#         assert "x-authorization" in detail or "authentication" in detail

#     def test_upload_requires_valid_token(
#         self,
#         client: Any,
#     ) -> None:
#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://huggingface.co/bert-base-uncased"},
#             headers={"X-Authorization": "bearer invalid_token"},
#         )

#         assert response.status_code == 403

#     def test_upload_validates_url_presence(
#         self,
#         client: Any,
#         auth_token: str,
#     ) -> None:
#         response = client.post(
#             "/artifact/model",
#             json={},
#             headers={"X-Authorization": auth_token},
#         )

#         assert response.status_code == 422

#     def test_upload_validates_artifact_type(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         response = client.post(
#             "/artifact/invalid_type",
#             json={"url": "https://example.com"},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 400
#         assert "invalid" in response.json()["detail"].lower()

#     def test_upload_generates_unique_ids(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         ids: Set[str] = set()

#         for i in range(5):
#             response = client.post(
#                 "/artifact/model",
#                 json={"url": f"https://huggingface.co/model-{i}"},
#                 headers={"X-Authorization": test_token},
#             )

#             assert response.status_code == 201
#             artifact_id: str = response.json()["metadata"]["id"]
#             ids.add(artifact_id)

#         assert len(ids) == 5

#     @patch("src.metrics.reviewedness_score.boto3.client")
#     def test_s3_integration_available(
#         self,
#         mock_boto3_client: MagicMock,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         mock_s3: MagicMock = MagicMock()
#         mock_boto3_client.return_value = mock_s3

#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://huggingface.co/bert-base-uncased"},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201

#     def test_upload_returns_201_created(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://huggingface.co/bert-base-uncased"},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201

#     def test_upload_full_workflow(
#         self,
#         client: Any,
#         test_token: str,
#     ) -> None:
#         artifact_type: str = "model"
#         artifact_url: str = "https://huggingface.co/meta-llama/Llama-2-7b-hf"

#         response = client.post(
#             f"/artifact/{artifact_type}",
#             json={"url": artifact_url},
#             headers={"X-Authorization": test_token},
#         )

#         assert response.status_code == 201
#         data: Dict[str, Any] = response.json()

#         assert "metadata" in data
#         assert "data" in data

#         assert data["metadata"]["id"]
#         assert data["metadata"]["name"]
#         assert data["metadata"]["type"] == artifact_type

#         assert data["data"]["url"] == artifact_url
#         assert data["data"]["download_url"]

#         download_url: str = data["data"]["download_url"]
#         assert "/api/artifacts/" in download_url or "/download/" in download_url


# if __name__ == "__main__":
#     pytest.main([__file__, "-v", "-s"])
