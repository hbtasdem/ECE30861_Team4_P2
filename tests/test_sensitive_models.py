"""
Tests for sensitive model security features.
"""

import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from src.crud.app import app
from src.sensitive_models import detect_malicious_patterns, log_sensitive_action, make_sensitive_zip, track_malicious

client = TestClient(app)


@pytest.fixture
def mock_s3() -> Generator[Any, None, None]:
    """Create a mock S3 environment."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-2")
        s3.create_bucket(
            Bucket="phase2-s3-bucket",
            CreateBucketConfiguration={"LocationConstraint": "us-east-2"}
        )
        yield s3


# ==================================================
# TEST: Upload JS Program Endpoint
# ==================================================

def test_upload_js_program_success(mock_s3: MagicMock) -> None:
    """Test successfully uploading a JS monitoring program.
    Tests @router.post("/sensitive/javascript-program")
    """

    js_content = b"console.log('test');"

    files = {"program": ("monitor.js", js_content, "application/javascript")}

    response = client.post("/sensitive/javascript-program", files=files)

    assert response.status_code == 200
    assert response.json()["message"] == "JavaScript program uploaded successfully"
    assert response.json()["filename"] == "monitor.js"
    assert response.json()["size"] == len(js_content)

    # Verify the file was actually uploaded to mock S3
    obj = mock_s3.get_object(Bucket="phase2-s3-bucket", Key="sensitive/monitoring-program.js")
    stored_content = obj['Body'].read()
    assert stored_content == js_content


# ==================================================
# TEST: Get JS Program Endpoint
# ==================================================

def test_get_js_program_success(mock_s3: MagicMock) -> None:
    """Test retrieving the JS monitoring program.
    Tests @router.get("/sensitive/javascript-program")
    """

    js_content = b"console.log('monitor');"

    # First upload a program
    mock_s3.put_object(
        Bucket="phase2-s3-bucket",
        Key="sensitive/monitoring-program.js",
        Body=js_content,
        ContentType="application/javascript"
    )
    response = client.get("/sensitive/javascript-program")
    assert response.status_code == 200
    assert response.json()["program"] == js_content.decode('utf-8')
    assert "last_modified" in response.json()


def test_get_js_program_not_found(mock_s3: MagicMock) -> None:
    """Test retrieving JS program when none exists."""
    response = client.get("/sensitive/javascript-program")
    assert response.status_code == 404
    assert "No JavaScript program has been uploaded" in response.json()["detail"]


# ==================================================
# TEST: Delete JS Program Endpoint
# ==================================================

def test_delete_js_program_success(mock_s3: MagicMock) -> None:
    """Test deleting the JS monitoring program.
    @router.delete("/sensitive/javascript-program")
    """
    # First upload a program
    js_content = b"console.log('test');"
    mock_s3.put_object(
        Bucket="phase2-s3-bucket",
        Key="sensitive/monitoring-program.js",
        Body=js_content
    )
    response = client.delete("/sensitive/javascript-program")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify it was actually deleted
    with pytest.raises(Exception):  # Should raise NoSuchKey
        mock_s3.get_object(Bucket="phase2-s3-bucket", Key="sensitive/monitoring-program.js")


# ==================================================
# TEST: make_sensitive_zip Function
# ==================================================

@patch('src.sensitive_models.httpx.get')
def test_make_sensitive_zip_success(mock_httpx_get: MagicMock) -> None:
    """Test creating a zip with README."""
    readme_content = b"# Test Model\n\nThis is a test model."
    # Mock httpx response
    mock_response = Mock()
    mock_response.content = readme_content
    mock_response.raise_for_status = Mock()
    mock_httpx_get.return_value = mock_response
    model_url = "https://huggingface.co/bert-base-uncased"
    zip_path = make_sensitive_zip("bert-base", model_url)

    try:
        # Verify zip was created
        assert zip_path.endswith('.zip')

        # Verify zip contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert 'README.md' in zf.namelist()
            assert zf.read('README.md') == readme_content

    finally:
        # Cleanup
        if os.path.exists(zip_path):
            os.unlink(zip_path)


@patch('src.sensitive_models.httpx.get')
def test_make_sensitive_zip_no_readme(mock_httpx_get: MagicMock) -> None:
    """Test creating a zip when README doesn't exist."""
    # Mock httpx to raise error (README not found)
    mock_httpx_get.side_effect = Exception("404 Not Found")

    model_url = "https://huggingface.co/some/model"
    zip_path = make_sensitive_zip("test-model", model_url)

    try:
        # Verify zip was created with minimal README
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert 'README.md' in zf.namelist()
            content = zf.read('README.md').decode('utf-8')
            assert "test-model" in content
            assert model_url in content

    finally:
        if os.path.exists(zip_path):
            os.unlink(zip_path)


# ==================================================
# TEST: check_sensitive_model Function
# ==================================================


def test_detect_safe_keyword_in_name():
    """Test that safe model names don't trigger false positives."""
    safe_names = [
        ("bert-base-uncased", "https://huggingface.co/bert-base-uncased"),
        ("gpt2", "https://huggingface.co/gpt2"),
        ("sentiment-analysis", "https://huggingface.co/user/sentiment-analysis"),
    ]
    for name, url in safe_names:
        is_malicious = detect_malicious_patterns(name, url, "test_id", False)
        assert not is_malicious


@patch('src.sensitive_models.httpx.get')
def test_detect_malicious_low_downloads(mock_get):
    """Test detection of models with very low downloads."""
    # Mock HuggingFace API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "author": "unknown-user",
        "downloads": 3,  # Very low
        "likes": 0,
        "tags": [],
        "createdAt": "2025-12-10T00:00:00Z"
    }
    mock_get.return_value = mock_response
    is_malicious = detect_malicious_patterns(
        "test-model", "https://huggingface.co/unknown-user/test-model", "test_id", False
    )
    assert is_malicious  # Should be flagged


@patch('src.sensitive_models.httpx.get')
def test_detect_malicious_newly_created_no_usage(mock_get):
    """Test detection of newly created models with no usage."""
    # Model created 2 days ago
    recent_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat() + "Z"
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "author": "new-user",
        "downloads": 2,
        "likes": 0,
        "tags": [],
        "createdAt": recent_date
    }
    mock_get.return_value = mock_response
    is_malicious = detect_malicious_patterns(
        "test-model", "https://huggingface.co/new-user/test-model", "test_id", False
    )
    assert is_malicious


def test_malicious_model_is_stored_and_returned(mock_s3):
    """
    Ensure a malicious model written to S3 is returned by the endpoint.
    """

    # Store a malicious model log in mock s3
    track_malicious(
        model_name="evil-model",
        model_url="https://huggingface.co/evil/model",
        artifact_id="artifact-123",
        reasons=["executes arbitrary code", "network exfiltration"],
    )

    # Act: call the endpoint
    response = client.get("/sensitive/malicious_models", headers={"X-Authorization": "test-token"})

    # Assert: endpoint succeeds
    assert response.status_code == 200

    data = response.json()
    assert "malicious_models" in data
    assert len(data["malicious_models"]) == 1

    entry = data["malicious_models"][0]

    assert entry["artifact_id"] == "artifact-123"
    assert entry["model_name"] == "evil-model"
    assert entry["model_url"] == "https://huggingface.co/evil/model"
    assert entry["reasons"] == [
        "executes arbitrary code",
        "network exfiltration",
    ]
    assert "timestamp" in entry


def test_log_sensitive_action_appends(mock_s3):
    """Test multiple actions append as JSONL."""

    log_sensitive_action("alice", "upload", "artifact-001")
    log_sensitive_action("bob", "download", "artifact-001")

    obj = mock_s3.get_object(
        Bucket="phase2-s3-bucket",
        Key="sensitive/logtrail.jsonl",
    )

    lines = obj["Body"].read().decode("utf-8").strip().split("\n")
    assert len(lines) == 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])

    assert first["username"] == "alice"
    assert second["username"] == "bob"
    assert second["action"] == "download"
