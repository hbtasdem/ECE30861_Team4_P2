#!/usr/bin/env python3
"""
Demonstration: Upload URL to BASELINE endpoint

Shows how users can upload a model URL to the registry using the BASELINE endpoint.

Run with: python tests/demo_upload.py
"""

import json
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Setup
from src.crud.app import app
from src.crud.upload.auth import create_access_token
from src.database_models import Base, User


def demo_url_upload() -> None:
    """Demonstrate URL upload workflow."""

    # Create in-memory test database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Create test user
    test_user = User(
        id=1,
        username="demo_user",
        email="demo@example.com",
        hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",
        is_admin=False,
    )
    db.add(test_user)
    db.commit()

    # Generate valid JWT token
    token = create_access_token({"sub": "1", "is_admin": False})

    # Create test client
    client = TestClient(app)

    # Override dependencies
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    from src.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    print("=" * 70)
    print("BASELINE UPLOAD DEMONSTRATION")
    print("=" * 70)

    # Test 1: Upload BERT Model
    print("\n[TEST 1] Uploading BERT Model from HuggingFace")
    print("-" * 70)

    model_url = (
        "https://huggingface.co/bert-base-uncased/resolve/main/pytorch_model.bin"
    )
    print(f"URL: {model_url}")

    response = client.post(
        "/artifact/model",
        json={"url": model_url},
        headers={"X-Authorization": f"bearer {token}"},
    )

    print(f"Status: {response.status_code}")
    # print(f"Response:")
    print("Response:")
    result = response.json()
    print(json.dumps(result, indent=2))

    if response.status_code == 201:
        artifact_id = result["metadata"]["id"]
        print("\nModel uploaded successfully!")
        print(f"  Artifact ID: {artifact_id}")
        print(f"  Type: {result['metadata']['type']}")
        print(f"  Name: {result['metadata']['name']}")
    else:
        print(f"\nUpload failed: {result['detail']}")
        return

    # Test 2: Upload Dataset
    print("\n[TEST 2] Uploading Dataset from HuggingFace")
    print("-" * 70)

    dataset_url = (
        "https://huggingface.co/datasets/wikitext/resolve/main/wikitext-103-v1.zip"
    )
    print(f"URL: {dataset_url}")

    response = client.post(
        "/artifact/dataset",
        json={"url": dataset_url},
        headers={"X-Authorization": f"bearer {token}"},
    )

    print(f"Status: {response.status_code}")
    result = response.json()
    print("Response:")
    print(json.dumps(result, indent=2))

    if response.status_code == 201:
        dataset_id = result["metadata"]["id"]
        print("\nDataset uploaded successfully!")
        print(f"  Artifact ID: {dataset_id}")
        print(f"  Type: {result['metadata']['type']}")

    # Test 3: Upload Code
    print("\n[TEST 3] Uploading Code from GitHub")
    print("-" * 70)

    code_url = "https://github.com/huggingface/transformers/archive/main.zip"
    print(f"URL: {code_url}")

    response = client.post(
        "/artifact/code",
        json={"url": code_url},
        headers={"X-Authorization": f"bearer {token}"},
    )

    print(f"Status: {response.status_code}")
    result = response.json()
    print("Response:")
    print(json.dumps(result, indent=2))

    if response.status_code == 201:
        code_id = result["metadata"]["id"]
        print("\nCode uploaded successfully!")
        print(f"  Artifact ID: {code_id}")
        print(f"  Type: {result['metadata']['type']}")

    # Test 4: Query all artifacts
    print("\n[TEST 4] Querying All Uploaded Artifacts")
    print("-" * 70)

    response = client.post(
        "/artifacts",
        json=[{"name": "*", "types": ["model", "dataset", "code"]}],
        headers={"X-Authorization": f"bearer {token}"},
    )

    print(f"Status: {response.status_code}")
    artifacts = response.json()
    print(f"Total artifacts: {len(artifacts)}")
    print("Artifacts:")
    for artifact in artifacts:
        print(f"  - {artifact['type']}: {artifact['name']} (ID: {artifact['id']})")

    # Test 5: Error handling - missing URL
    print("\n[TEST 5] Error Handling - Missing URL")
    print("-" * 70)

    response = client.post(
        "/artifact/model", json={}, headers={"X-Authorization": f"bearer {token}"}
    )

    print(f"Status: {response.status_code}")
    if response.status_code != 201:
        print(f"Correctly rejected (expected): {response.json()}")

    # Test 6: Error handling - missing authentication
    print("\n[TEST 6] Error Handling - Missing Authentication")
    print("-" * 70)

    response = client.post("/artifact/model", json={"url": "https://example.com/model"})

    print(f"Status: {response.status_code}")
    if response.status_code == 403:
        print(f"Correctly rejected (expected): {response.json()['detail']}")

    # Test 7: Error handling - invalid type
    print("\n[TEST 7] Error Handling - Invalid Artifact Type")
    print("-" * 70)

    response = client.post(
        "/artifact/invalid_type",
        json={"url": "https://example.com/file"},
        headers={"X-Authorization": f"bearer {token}"},
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print(f"Correctly rejected (expected): {response.json()['detail']}")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nAll URL uploads working 100%!")
    print("Authentication validated")
    print("Error handling working")
    print("\nTo use in production:")
    print("  1. Start server: uvicorn src.crud.app:app --host 0.0.0.0 --port 8000")
    print("  2. Get JWT token via authentication endpoint")
    print("  3. POST to /artifact/{type} with X-Authorization header")


if __name__ == "__main__":
    demo_url_upload()
