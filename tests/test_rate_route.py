# Test the rate endpoint
# use a mock local storage, not the real s3 client
import json
from typing import Any, Dict, Generator

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from src.crud.app import app
from src.crud.rate_route import findDatasetAndCode  # , rateOnUpload
from src.main import calculate_all_scores

# ---------------------------------------------
# tests for the /rate endpoint
# ---------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Provide a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_s3_bucket() -> Generator[tuple[boto3.client, Dict[str, Any]], None, None]:
    """Start Moto S3 mock and create the test bucket."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-2")
        s3.create_bucket(Bucket="phase2-s3-bucket", CreateBucketConfiguration={"LocationConstraint": "us-east-2"})

        # upload a valid mock rating, id 01
        valid_rating = {
            "name": "bert-base-uncased",
            "category": "model",
            "net_score": 0.95,
            "net_score_latency": 0.02,
            "ramp_up_time": 0.8,
            "ramp_up_time_latency": 0.01,
            "bus_factor": 0.9,
            "bus_factor_latency": 0.01,
            "performance_claims": 0.92,
            "performance_claims_latency": 0.02,
            "license": 1.0,
            "license_latency": 0.01,
            "dataset_and_code_score": 0.88,
            "dataset_and_code_score_latency": 0.01,
            "dataset_quality": 0.9,
            "dataset_quality_latency": 0.01,
            "code_quality": 0.93,
            "code_quality_latency": 0.01,
            "reproducibility": 0.94,
            "reproducibility_latency": 0.01,
            "reviewedness": 0.85,
            "reviewedness_latency": 0.01,
            "tree_score": 0.9,
            "tree_score_latency": 0.01,
            "size_score": {
                "raspberry_pi": 0.8,
                "jetson_nano": 0.85,
                "desktop_pc": 0.9,
                "aws_server": 0.95,
            },
            "size_score_latency": 0.01,
        }
        artifact_id = "01"
        key = f"rating/{artifact_id}.rate.json"
        s3.put_object(Bucket="phase2-s3-bucket", Key=key, Body=json.dumps(valid_rating))

        # upload an invalid mock rating, id 02
        incomplete_rating = {
            "name": "bert-base-uncased",
            "category": "model",
            "net_score": 0.95,
        }
        artifact_id = "02"
        key = f"rating/{artifact_id}.rate.json"
        s3.put_object(
            Bucket="phase2-s3-bucket", Key=key, Body=json.dumps(incomplete_rating)
        )

        # run test
        yield s3, valid_rating


def test_get_rating_success(client: TestClient, mock_s3_bucket: boto3.client) -> None:
    """Test that GET /artifact/model/{id}/rate returns the expected ModelRating
    for a valid stored ModelRating."""
    # mock s3 and stored rating from fixture
    s3_client, mock_valid_rating = mock_s3_bucket

    # rate endpoint
    artifact_id = "01"
    response = client.get(f"/artifact/model/{artifact_id}/rate")

    # Assert successful response
    assert response.status_code == 200
    returned_rating = response.json()
    for key, value in mock_valid_rating.items():
        assert returned_rating[key] == value


def test_get_rating_noartifact(
    client: TestClient, mock_s3_bucket: boto3.client
) -> None:
    """Test that GET /artifact/model/{id}/rate returns the expected error
    given artifact id that doesn't exist."""
    # mock s3 and stored rating from fixture
    s3_client, ignore = mock_s3_bucket

    # rate endpoint
    artifact_id = "03"
    response = client.get(f"/artifact/model/{artifact_id}/rate")

    # assert error type
    assert response.status_code == 404


def test_get_rating_incomplete(
    client: TestClient, mock_s3_bucket: boto3.client
) -> None:
    """Test that GET /artifact/model/{id}/rate returns the expected error
    for a stored incomplete ModelRating."""
    # mock s3 and stored rating from fixture
    s3_client, ignore = mock_s3_bucket

    # rate endpoint
    artifact_id = "02"
    response = client.get(f"/artifact/model/{artifact_id}/rate")

    # assert error type
    assert response.status_code == 500


# ---------------------------------------------
# Tests for rate calculation on upload endpoint
# ---------------------------------------------

def test_find_code_dataset_valid() -> None:
    """Test that llm can find code link and dataset link"""
    model_url = "https://huggingface.co/google-bert/bert-base-uncased"
    expected_code = "https://github.com/google-research/bert"
    expected_dataset = "https://huggingface.co/datasets/bookcorpus/bookcorpus"

    dataset, code = findDatasetAndCode(model_url)

    assert code == expected_code
    assert dataset == expected_dataset


def manual_test_scoring() -> Dict[str, Any]:
    code_url = ""
    dataset_url = ""
    model_url = "https://huggingface.co/google-bert/bert-base-uncased"
    dataset_url, code_url = findDatasetAndCode(model_url)
    rating = calculate_all_scores(code_url, dataset_url, model_url, set(), set())
    return rating


if __name__ == "__main__":
    rating = manual_test_scoring()
    print(rating)
