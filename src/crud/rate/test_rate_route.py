# Test the rate endpoint
# use a mock local storage, not the real s3 client
import json
from typing import Any, Dict, Generator

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from crud.app import app


@pytest.fixture
def client() -> TestClient:
    """Provide a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_s3_bucket() -> Generator[tuple[boto3.client, Dict[str, Any]], None, None]:
    """Start Moto S3 mock and create the test bucket."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="phase2-s3-bucket")

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
            "net_score": 0.95
        }
        artifact_id = "02"
        key = f"rating/{artifact_id}.rate.json"
        s3.put_object(Bucket="phase2-s3-bucket", Key=key, Body=json.dumps(incomplete_rating))

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


def test_get_rating_invalidartifactid(client: TestClient, mock_s3_bucket: boto3.client) -> None:
    """Test that GET /artifact/model/{id}/rate returns the expected error
    given a non-integer artifact id."""
    # rate endpoint
    artifact_id = "not_integer"
    response = client.get(f"/artifact/model/{artifact_id}/rate")

    # assert error type
    assert response.status_code == 400


def test_get_rating_noartifact(client: TestClient, mock_s3_bucket: boto3.client) -> None:
    """Test that GET /artifact/model/{id}/rate returns the expected error
    given artifact id that doesn't exist."""
    # mock s3 and stored rating from fixture
    s3_client, ignore = mock_s3_bucket

    # rate endpoint
    artifact_id = "03"
    response = client.get(f"/artifact/model/{artifact_id}/rate")

    # assert error type
    assert response.status_code == 404


def test_get_rating_incomplete(client: TestClient, mock_s3_bucket: boto3.client) -> None:
    """Test that GET /artifact/model/{id}/rate returns the expected error
    for a stored incomplete ModelRating."""
    # mock s3 and stored rating from fixture
    s3_client, ignore = mock_s3_bucket

    # rate endpoint
    artifact_id = "02"
    response = client.get(f"/artifact/model/{artifact_id}/rate")

    # assert error type
    assert response.status_code == 500
