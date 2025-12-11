from typing import Any, Iterator, Type
from unittest.mock import MagicMock, patch

import boto3

try:
    from moto import mock_aws
    HAS_MOTO = True
except ImportError:
    HAS_MOTO = False
    mock_aws = None  # type: ignore

import pytest

from src.crud.upload.download_artifact import (BUCKET_NAME, download_code,
                                               download_dataset,
                                               download_model)


class FakeResponse:
    # Fake HTTPX response to stream bytes
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self._stream = iter([content])
        self.status_code = status_code

    def raise_for_status(self) -> None:
        pass

    def iter_bytes(self, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        return self._stream

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb: Any) -> None:
        pass


@pytest.mark.skipif(not HAS_MOTO, reason="moto not available")
@patch("src.crud.upload.download_artifact.HfApi")
@patch("src.crud.upload.download_artifact.httpx.stream")
def test_download_model(mock_httpx_stream: MagicMock, mock_hfapi_class: MagicMock) -> None:
    # ----- Mock HF API -----
    mock_hfapi = MagicMock()
    mock_hfapi.list_repo_files.return_value = ["config.json", "pytorch_model.bin"]
    mock_hfapi_class.return_value = mock_hfapi

    # ----- Mock httpx.stream -----
    mock_httpx_stream.side_effect = lambda *args, **kwargs: FakeResponse(b"fake content")

    # ----- Mock S3 -----
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    artifact_id = "test-artifact"
    model_url = "https://huggingface.co/test-model"

    # Run function
    index_url = download_model(model_url, artifact_id)

    # ----- Check index.html exists -----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = response["Body"].read().decode()
    assert "<li><a href=" in index_content
    assert "config.json" in index_content
    assert "pytorch_model.bin" in index_content

    # Check returned URL matches S3 object
    assert index_url == f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html"


@pytest.mark.skipif(not HAS_MOTO, reason="moto not available")
@patch("src.crud.upload.download_artifact.HfApi")
@patch("src.crud.upload.download_artifact.httpx.stream")
def test_download_dataset(mock_httpx_stream: MagicMock, mock_hfapi_class: MagicMock) -> None:
    # ----- Mock HF API -----
    mock_hfapi = MagicMock()
    mock_hfapi.list_repo_files.return_value = ["dataset_info.json", "train.jsonl", "README.md"]
    mock_hfapi_class.return_value = mock_hfapi

    # ----- Mock httpx.stream -----
    mock_httpx_stream.side_effect = lambda *args, **kwargs: FakeResponse(b"fake dataset bytes")

    # ----- Mock S3 -----
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    artifact_id = "dataset-artifact"
    dataset_url = "https://huggingface.co/datasets/bookcorpus/bookcorpus"

    # Run function
    index_url = download_dataset(dataset_url, artifact_id)

    # ----- Validate index.html exists -----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = response["Body"].read().decode()

    # Ensure expected file links appear
    assert "<li><a href=" in index_content
    assert "dataset_info.json" in index_content
    assert "train.jsonl" in index_content
    assert "README.md" in index_content

    # Ensure returned URL matches the expected S3 index.html URL
    assert index_url == (f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html")


@pytest.mark.skipif(not HAS_MOTO, reason="moto not available")
@patch("src.crud.upload.download_artifact.httpx.stream")
@patch("src.crud.upload.download_artifact.httpx.Client")
def test_download_code(mock_httpx_client: MagicMock, mock_httpx_stream: MagicMock) -> None:
    # -------- Mock GitHub API Responses --------
    mock_client_instance = MagicMock()

    # Make the Client class return the mock instance when used as a context manager
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
    mock_httpx_client.return_value.__exit__.return_value = None

    # Fake response for repo info (default branch)
    class FakeRepoResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, str]:
            return {"default_branch": "main"}

    # Fake response for repo tree
    class FakeTreeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {"tree": [{"path": "README.md", "type": "blob"}, {"path": "src/bert.py", "type": "blob"}]}

    # client.get() returns default branch first, then tree second
    mock_client_instance.get.side_effect = [FakeRepoResponse(), FakeTreeResponse()]

    # -------- Mock streaming downloaded files --------
    # Return fake bytes for any raw.githubusercontent file download
    mock_httpx_stream.side_effect = lambda *args, **kwargs: FakeResponse(b"fake bytes", status_code=200)

    # -------- Create S3 Bucket --------
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    artifact_id = "code-artifact"
    repo_url = "https://github.com/google-research/bert"

    # -------- Run the function --------
    index_url = download_code(repo_url, artifact_id)

    # -------- Validate index.html content --------
    result = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = result["Body"].read().decode()

    # EXPECTED: <li> entries present
    assert "<li><a href=" in index_content
    assert "README.md" in index_content
    assert "src/bert.py" in index_content

    # Returned URL correct
    assert index_url == f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html"
