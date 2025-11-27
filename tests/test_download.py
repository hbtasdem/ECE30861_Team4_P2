from typing import Any, Iterator, Type
from unittest.mock import MagicMock, patch

import boto3
from moto import mock_aws

from src.crud.upload.download_artifact import BUCKET_NAME, download_model


class FakeResponse:
    # Fake HTTPX response to stream bytes
    def __init__(self, content: bytes) -> None:
        self._stream = iter([content])

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

    # ----- Check index.html exists -----
    response = s3.get_object(Bucket=BUCKET_NAME, Key=f"downloads/{artifact_id}/index.html")
    index_content = response["Body"].read().decode()
    assert "<li><a href=" in index_content
    assert "config.json" in index_content
    assert "pytorch_model.bin" in index_content

    # Check returned URL matches S3 object
    assert index_url == f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/index.html"
