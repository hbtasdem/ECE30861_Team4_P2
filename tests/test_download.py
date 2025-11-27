# tests/test_download.py
import io
from typing import Any, Type
from unittest.mock import MagicMock, patch

import boto3
from moto import mock_aws

from src.crud.upload.download_artifact import BUCKET_NAME, download_model


@mock_aws
@patch("src.crud.upload.download_artifact.HfApi")
@patch("httpx.stream")
def test_stream_model_to_s3(mock_httpx_stream: MagicMock, mock_hfapi_class: MagicMock) -> None:
    # ----- Mock Hugging Face API -----
    mock_hfapi = MagicMock()
    mock_hfapi.list_repo_files.return_value = ["config.json", "pytorch_model.bin"]
    mock_hfapi_class.return_value = mock_hfapi

    # ----- Mock httpx.stream -----
    class FakeResponse:
        def __init__(self, content: bytes) -> None:
            self.raw = io.BytesIO(content)

        def raise_for_status(self) -> None:
            pass

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type: Type[BaseException], exc_val: Type[BaseException], exc_tb: Type[BaseException]) -> None:
            pass

    def fake_stream(method: str, url: str, *args: Any, **kwargs: Any) -> "FakeResponse":
        return FakeResponse(b"fake contents")
    mock_httpx_stream.side_effect = fake_stream

    # ----- Mock AWS S3 -----
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    # ----- Run function -----
    url = download_model("https://huggingface.co/test/model")

    # ----- Assert S3 files exist -----
    objects = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="downloads/test/model/")
    keys = [obj["Key"] for obj in objects.get("Contents", [])]
    assert "downloads/test/model/config.json" in keys
    assert "downloads/test/model/pytorch_model.bin" in keys

    # ----- Assert presigned URL was returned -----
    assert url.startswith("https://")
