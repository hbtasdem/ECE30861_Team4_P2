"""
Tests for sensitive model security features.
"""

import os
import zipfile
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from src.crud.app import app
from src.sensitive_models import make_sensitive_zip, sensitive_check

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
    """Test successfully uploading a JS monitoring program."""

    js_content = b"console.log('test');"

    files = {"program": ("monitor.js", js_content, "application/javascript")}

    response = client.post("/sensitive/javascript-program", files=files)

    assert response.status_code == 200
    assert response.json()["message"] == "JavaScript program uploaded successfully"
    assert response.json()["filename"] == "monitor.js"
    assert response.json()["size"] == len(js_content)

    # Verify the file was actually uploaded to mock S3
    obj = mock_s3.get_object(Bucket="phase2-s3-bucket", Key="monitoring-program.js")
    stored_content = obj['Body'].read()
    assert stored_content == js_content


# ==================================================
# TEST: Get JS Program Endpoint
# ==================================================

def test_get_js_program_success(mock_s3: MagicMock) -> None:
    """Test retrieving the JS monitoring program."""

    js_content = b"console.log('monitor');"

    # First upload a program
    mock_s3.put_object(
        Bucket="phase2-s3-bucket",
        Key="monitoring-program.js",
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
    """Test deleting the JS monitoring program."""
    # First upload a program
    js_content = b"console.log('test');"
    mock_s3.put_object(
        Bucket="phase2-s3-bucket",
        Key="monitoring-program.js",
        Body=js_content
    )
    response = client.delete("/sensitive/javascript-program")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify it was actually deleted
    with pytest.raises(Exception):  # Should raise NoSuchKey
        mock_s3.get_object(Bucket="phase2-s3-bucket", Key="monitoring-program.js")


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
# TEST: sensitive_check Function
# ==================================================

@patch('src.sensitive_models.make_sensitive_zip')
@patch('src.sensitive_models.subprocess.run')
def test_sensitive_check_no_js_program(mock_subprocess: MagicMock, mock_make_zip: MagicMock, mock_s3: MagicMock) -> None:
    """Test sensitive_check when no JS program is configured."""

    # No JS program in S3, should pass without running subprocess
    sensitive_check("test-model", "https://huggingface.co/model", "user123")

    # Should not create zip or run subprocess
    mock_make_zip.assert_not_called()
    mock_subprocess.assert_not_called()


@patch('src.sensitive_models.make_sensitive_zip')
@patch('src.sensitive_models.subprocess.run')
def test_sensitive_check_approved(mock_subprocess: MagicMock, mock_make_zip: MagicMock, mock_s3: MagicMock) -> None:
    """Test sensitive_check when JS program approves."""

    # Upload JS program to mock S3
    js_program = b"console.log('approved'); process.exit(0);"
    mock_s3.put_object(
        Bucket="phase2-s3-bucket",
        Key="monitoring-program.js",
        Body=js_program
    )

    # Mock zip creation
    mock_make_zip.return_value = "/tmp/test.zip"

    # Mock subprocess to return success
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "APPROVED"
    mock_subprocess.return_value = mock_result

    # Should not raise exception
    sensitive_check("test-model", "https://huggingface.co/model", "user123")

    # Verify subprocess was called with correct args
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]  # Get the list of arguments

    # Arguments are: ['node', js_file_path, model_name, uploader, uploader, zip_path]
    assert call_args[0] == 'node'
    assert call_args[2] == 'test-model'       # model_name
    assert call_args[3] == 'user123'          # uploader_username
    assert call_args[4] == 'user123'          # uploader_username (same for upload)
    assert call_args[5] == '/tmp/test.zip'    # zip_path


@patch('src.sensitive_models.make_sensitive_zip')
@patch('src.sensitive_models.subprocess.run')
def test_sensitive_check_rejected(mock_subprocess: MagicMock, mock_make_zip: MagicMock, mock_s3: MagicMock) -> None:
    """Test sensitive_check when JS program rejects."""

    from fastapi import HTTPException

    # Upload JS program to mock S3
    js_program = b"console.log('rejected'); process.exit(1);"
    mock_s3.put_object(
        Bucket="phase2-s3-bucket",
        Key="monitoring-program.js",
        Body=js_program
    )

    # Mock zip creation
    mock_make_zip.return_value = "/tmp/test.zip"

    # Mock subprocess to return failure
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = "REJECTED: Model contains malicious content"
    mock_subprocess.return_value = mock_result

    # Should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        sensitive_check("malicious-model", "https://huggingface.co/model", "user123")

    assert exc_info.value.status_code == 403
    assert "rejected by monitoring program" in exc_info.value.detail
    assert "malicious content" in exc_info.value.detail
