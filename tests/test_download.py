import tempfile
from unittest.mock import MagicMock, patch

import boto3
from moto import mock_aws

from src.crud.upload.download_artifact import BUCKET_NAME, download_model


@mock_aws
@patch("src.crud.upload.download_artifact.hf_hub_download")
@patch("src.crud.upload.download_artifact.HfApi")
def test_stream_model_to_s3(mock_hfapi_class: MagicMock, mock_hf_download: MagicMock) -> None:
    # Mock HuggingFace
    mock_hfapi = MagicMock()
    mock_hfapi.list_repo_files.return_value = ["config.json", "pytorch_model.bin"]
    mock_hfapi_class.return_value = mock_hfapi

    # Mock hf_hub_download to return a temp file
    def fake_download(*args: object, **kwargs: object) -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(b"fake contents")
        tmp.close()
        return tmp.name
    mock_hf_download.side_effect = fake_download

    # Mock AWS S3
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    # Call download function
    url = download_model("https://huggingface.co/test/model")

    # Check files are in mocked S3
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="models/test/model/")
    s3_files = [obj["Key"] for obj in response.get("Contents", [])]

    assert "models/test/model/config.json" in s3_files
    assert "models/test/model/pytorch_model.bin" in s3_files

    # Check url assigned
    assert url.startswith("https://")
