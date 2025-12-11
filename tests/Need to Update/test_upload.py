# #!/usr/bin/env python3
# """
# Test suite for artifact upload endpoints (BASELINE).

# Tests model, dataset, and code uploads via URL to the registry.
# """

# import json
# import pytest
# from typing import Generator
# from fastapi.testclient import TestClient
# from sqlalchemy import create_engine
# from sqlalchemy.orm import Session, sessionmaker

# from src.crud.app import app
# from src.crud.upload.auth import create_access_token
# from src.database_models import Base, User
# from src.database import get_db


# @pytest.fixture
# def test_db() -> Generator[Session, None, None]:
#     """Create in-memory test database."""
#     engine = create_engine("sqlite:///:memory:")
#     Base.metadata.create_all(engine)
#     SessionLocal = sessionmaker(bind=engine)
#     db = SessionLocal()

#     yield db

#     db.close()


# @pytest.fixture
# def test_user(test_db: Session) -> User:
#     """Create test user in database."""
#     user = User(
#         id=1,
#         username="demo_user",
#         email="demo@example.com",
#         hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",
#         is_admin=False,
#     )
#     test_db.add(user)
#     test_db.commit()
#     return user


# @pytest.fixture
# def test_token(test_user: User) -> str:
#     """Generate valid JWT token for test user."""
#     return create_access_token({"sub": "1", "is_admin": False})


# @pytest.fixture
# def client(test_db: Session) -> TestClient:
#     """Create test client with database override."""
#     def override_get_db() -> Generator[Session, None, None]:
#         yield test_db

#     app.dependency_overrides[get_db] = override_get_db

#     yield TestClient(app)

#     app.dependency_overrides.clear()


# class TestModelUpload:
#     """Test cases for model uploads."""

#     def test_upload_bert_model_success(self, client: TestClient, test_token: str):
#         """Test uploading BERT model from HuggingFace."""
#         model_url = (
#             "https://huggingface.co/bert-base-uncased/resolve/main/pytorch_model.bin"
#         )

#         response = client.post(
#             "/artifact/model",
#             json={"url": model_url},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )

#         assert response.status_code == 201
#         result = response.json()
#         assert "metadata" in result
#         assert result["metadata"]["type"] == "model"
#         assert "id" in result["metadata"]
#         assert "name" in result["metadata"]

#     def test_upload_model_missing_url(self, client: TestClient, test_token: str):
#         """Test error handling when URL is missing."""
#         response = client.post(
#             "/artifact/model",
#             json={},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )

#         assert response.status_code != 201
#         assert "detail" in response.json() or "error" in response.json()

#     def test_upload_model_no_auth(self, client: TestClient):
#         """Test that upload fails without authentication."""
#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://example.com/model"},
#         )

#         assert response.status_code == 403
#         assert "detail" in response.json()


# class TestDatasetUpload:
#     """Test cases for dataset uploads."""

#     def test_upload_dataset_success(self, client: TestClient, test_token: str):
#         """Test uploading dataset from HuggingFace."""
#         dataset_url = (
#             "https://huggingface.co/datasets/wikitext/resolve/main/wikitext-103-v1.zip"
#         )

#         response = client.post(
#             "/artifact/dataset",
#             json={"url": dataset_url},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )

#         assert response.status_code == 201
#         result = response.json()
#         assert "metadata" in result
#         assert result["metadata"]["type"] == "dataset"
#         assert "id" in result["metadata"]


# class TestCodeUpload:
#     """Test cases for code uploads."""

#     def test_upload_code_from_github(self, client: TestClient, test_token: str):
#         """Test uploading code from GitHub."""
#         code_url = "https://github.com/huggingface/transformers/archive/main.zip"

#         response = client.post(
#             "/artifact/code",
#             json={"url": code_url},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )

#         assert response.status_code == 201
#         result = response.json()
#         assert "metadata" in result
#         assert result["metadata"]["type"] == "code"
#         assert "id" in result["metadata"]


# class TestArtifactQuery:
#     """Test cases for querying artifacts."""

#     def test_query_all_artifacts(self, client: TestClient, test_token: str):
#         """Test querying all uploaded artifacts."""
#         # First upload some artifacts
#         model_url = (
#             "https://huggingface.co/bert-base-uncased/resolve/main/pytorch_model.bin"
#         )
#         client.post(
#             "/artifact/model",
#             json={"url": model_url},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )

#         # Query all artifacts
#         response = client.post(
#             "/artifacts",
#             json=[{"name": "*", "types": ["model", "dataset", "code"]}],
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )

#         assert response.status_code == 200
#         artifacts = response.json()
#         assert isinstance(artifacts, list)
#         assert len(artifacts) > 0

#         # Verify artifact structure
#         for artifact in artifacts:
#             assert "type" in artifact
#             assert "name" in artifact
#             assert "id" in artifact


# class TestErrorHandling:
#     """Test cases for error handling."""

#     def test_invalid_artifact_type(self, client: TestClient, test_token: str):
#         """Test error handling for invalid artifact type."""
#         response = client.post(
#             "/artifact/invalid_type",
#             json={"url": "https://example.com/file"},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )

#         assert response.status_code == 400
#         assert "detail" in response.json()

#     def test_missing_authentication(self, client: TestClient):
#         """Test that requests without auth are rejected."""
#         response = client.post(
#             "/artifact/model",
#             json={"url": "https://example.com/model"},
#         )

#         assert response.status_code == 403


# class TestIntegration:
#     """Integration tests for complete workflows."""

#     def test_full_upload_workflow(self, client: TestClient, test_token: str):
#         """Test complete workflow: upload model, dataset, code, then query."""
#         # Upload model
#         model_response = client.post(
#             "/artifact/model",
#             json={"url": "https://huggingface.co/bert-base-uncased/resolve/main/pytorch_model.bin"},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )
#         assert model_response.status_code == 201
#         model_id = model_response.json()["metadata"]["id"]

#         # Upload dataset
#         dataset_response = client.post(
#             "/artifact/dataset",
#             json={"url": "https://huggingface.co/datasets/wikitext/resolve/main/wikitext-103-v1.zip"},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )
#         assert dataset_response.status_code == 201
#         dataset_id = dataset_response.json()["metadata"]["id"]

#         # Upload code
#         code_response = client.post(
#             "/artifact/code",
#             json={"url": "https://github.com/huggingface/transformers/archive/main.zip"},
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )
#         assert code_response.status_code == 201
#         code_id = code_response.json()["metadata"]["id"]

#         # Query all and verify all three are present
#         query_response = client.post(
#             "/artifacts",
#             json=[{"name": "*", "types": ["model", "dataset", "code"]}],
#             headers={"X-Authorization": f"bearer {test_token}"},
#         )
#         assert query_response.status_code == 200
#         artifacts = query_response.json()

#         artifact_ids = [a["id"] for a in artifacts]
#         assert model_id in artifact_ids
#         assert dataset_id in artifact_ids
#         assert code_id in artifact_ids
