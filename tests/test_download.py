import os
from typing import Any, Generator, Iterator, Type
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from src.crud.upload.download_artifact import BUCKET_NAME, download_code, download_dataset, download_model


class FakeResponse:
    # Fake HTTPX response to stream bytes
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self._stream = iter([content])
        self.status_code = status_code

    def raise_for_status(self) -> None:
        pass

    def iter_bytes(self, chunk_size: int = 1024*1024) -> Iterator[bytes]:
        return self._stream

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb: Any) -> None:
        pass


@mock_aws
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

    # ----- Check index.html exists and has files-----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = response["Body"].read().decode()
    assert "<li><a href=" in index_content
    assert "config.json" in index_content
    assert "pytorch_model.bin" in index_content

    # Check returned URL matches S3 object
    assert index_url == f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html"


@mock_aws
@patch("src.crud.upload.download_artifact.HfApi")
@patch("src.crud.upload.download_artifact.httpx.stream")
@patch("src.crud.upload.download_artifact.get_hf_token")
def test_download_dataset_huggingface(mock_get_hf_token: MagicMock, mock_httpx_stream: MagicMock, mock_hfapi_class: MagicMock) -> None:
    # ----- Mock HF API -----
    mock_get_hf_token.return_value = "hf_FAKE_TOKEN"
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

    # ----- Check index.html exists and has files-----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = response["Body"].read().decode()
    assert "<li><a href=" in index_content
    assert "dataset_info.json" in index_content
    assert "train.jsonl" in index_content
    assert "README.md" in index_content

    # Check returned URL matches S3 object
    assert index_url == (f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html")


@pytest.fixture
def mock_kaggle_credentials() -> Generator[None, None, None]:
    """Set fake Kaggle credentials for tests that need them."""
    os.environ["KAGGLE_USERNAME"] = "test_user"
    os.environ["KAGGLE_KEY"] = "test_key"
    yield
    # Optionally clean up after test
    os.environ.pop("KAGGLE_USERNAME", None)
    os.environ.pop("KAGGLE_KEY", None)


@mock_aws
@patch("src.crud.upload.download_artifact.httpx.Client")
@patch("kaggle.api.kaggle_api_extended.KaggleApi")
@patch("src.crud.upload.download_artifact.shutil.disk_usage")
def test_download_dataset_kaggle(
        mock_disk_usage: MagicMock, mock_kaggle_class: MagicMock, mock_httpx_client_class: MagicMock, mock_kaggle_credentials: None
        ) -> None:
    # ----- Mock disk usage check -----
    mock_disk_usage.return_value = MagicMock(free=1024*1024*1024)  # 1GB free

    # ----- Mock Kaggle API -----
    mock_kaggle_api = MagicMock()
    mock_kaggle_api.get_config_value.side_effect = lambda key: {"username": "test_user", "key": "test_key"}[key]
    mock_kaggle_class.return_value = mock_kaggle_api

    # ----- Mock httpx Client and streaming -----
    mock_client = MagicMock()
    mock_httpx_client_class.return_value.__enter__.return_value = mock_client
    mock_stream_response = MagicMock()
    mock_stream_response.status_code = 200
    mock_stream_response.iter_bytes.return_value = iter([b"fake zip data chunk 1", b"fake zip data chunk 2"])
    mock_stream_response.raise_for_status = MagicMock()

    mock_client.stream.return_value.__enter__.return_value = mock_stream_response

    # ----- Mock S3 -----
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    artifact_id = "kaggle-artifact"
    dataset_url = "https://www.kaggle.com/datasets/username/dataset-name"

    # Run function
    index_url = download_dataset(dataset_url, artifact_id)

    # ----- Validate Kaggle API was called correctly -----
    mock_kaggle_api.authenticate.assert_called_once()
    mock_kaggle_api.get_config_value.assert_any_call("username")
    mock_kaggle_api.get_config_value.assert_any_call("key")

    # ----- Validate HTTP request was made -----
    mock_client.stream.assert_called_once()

    # ----- Validate zip file was uploaded to S3 -----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/dataset-name.zip")
    zip_content = response["Body"].read()
    assert b"fake zip data" in zip_content

    # ----- Validate index.html exists -----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = response["Body"].read().decode()

    # Ensure zip file link appears
    assert "<li><a href=" in index_content
    assert "dataset-name.zip" in index_content

    # Ensure returned URL matches the expected S3 index.html URL
    assert index_url == f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html"


@mock_aws
@patch("src.crud.upload.download_artifact.httpx.stream")
@patch("src.crud.upload.download_artifact.httpx.Client")
def test_download_dataset_github(mock_httpx_client_class: MagicMock, mock_httpx_stream: MagicMock) -> None:
    # ----- Mock httpx Client -----
    mock_client = MagicMock()
    mock_httpx_client_class.return_value.__enter__.return_value = mock_client

    # Mock the repo API response (get default branch)
    mock_repo_response = MagicMock()
    mock_repo_response.json.return_value = {"default_branch": "main"}
    mock_repo_response.raise_for_status = MagicMock()

    # Mock the tree API response (list files)
    mock_tree_response = MagicMock()
    mock_tree_response.json.return_value = {
        "tree": [
            {"path": "data/train.csv", "type": "blob"},
            {"path": "data/test.csv", "type": "blob"},
            {"path": "README.md", "type": "blob"},
            {"path": "data", "type": "tree"}  # directory, should be skipped
        ]
    }
    mock_tree_response.raise_for_status = MagicMock()

    # Set up get() to return appropriate responses
    mock_client.get.side_effect = [mock_repo_response, mock_tree_response]

    # Mock httpx.stream to return FakeResponse context managers
    mock_httpx_stream.side_effect = [FakeResponse(b"train data"), FakeResponse(b"test data"), FakeResponse(b"readme content")]

    # ----- Mock S3 -----
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    artifact_id = "github-artifact"
    dataset_url = "https://github.com/owner/repo"

    # Run function
    index_url = download_dataset(dataset_url, artifact_id)

    # ----- Validate API calls -----
    assert mock_client.get.call_count == 2

    # Check repo API call
    repo_call = mock_client.get.call_args_list[0]
    assert "api.github.com/repos/owner/repo" in repo_call[0][0]

    # Check tree API call
    tree_call = mock_client.get.call_args_list[1]
    assert "api.github.com/repos/owner/repo/git/trees/main" in tree_call[0][0]
    assert "recursive=1" in tree_call[0][0]

    # ----- Validate file streaming calls -----
    assert mock_httpx_stream.call_count == 3

    # Check that files were streamed from raw.githubusercontent.com
    stream_calls = [call[0][1] for call in mock_httpx_stream.call_args_list]
    assert any("data/train.csv" in call for call in stream_calls)
    assert any("data/test.csv" in call for call in stream_calls)
    assert any("README.md" in call for call in stream_calls)

    # ----- Validate files were uploaded to S3 -----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/data/train.csv")
    assert response["Body"].read() == b"train data"
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/data/test.csv")
    assert response["Body"].read() == b"test data"
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/README.md")
    assert response["Body"].read() == b"readme content"

    # ----- Validate index.html exists -----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = response["Body"].read().decode()

    # Ensure all file links appear
    assert "<li><a href=" in index_content
    assert "data/train.csv" in index_content
    assert "data/test.csv" in index_content
    assert "README.md" in index_content

    # Ensure returned URL matches the expected S3 index.html URL
    assert index_url == f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html"


@mock_aws
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
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, str]:
            return {"default_branch": "main"}

    # Fake response for repo tree
    class FakeTreeResponse:
        status_code = 200

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
