"""Pytest configuration - imports fixtures from test_setup module."""

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# Import all fixtures from test_setup module so pytest can discover them
from tests.test_setup import client, db, test_db, test_token  # noqa: F401


@pytest.fixture
def auth_token(test_token: str) -> str:  # noqa: F811
    """Alias for test_token to use in tests."""
    return test_token


@pytest.fixture  # georgia turned off (autouse=True) bc it was messing w my tests that don't use this
def mock_s3_operations() -> Generator[None, None, None]:
    """Mock boto3 S3 operations to avoid AWS calls during tests."""
    # Mock the s3_client to succeed without actual S3 calls
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
    mock_s3.get_object = MagicMock(return_value={
        "Body": MagicMock(read=lambda: b'{"test": "data"}')
    })
    mock_s3.list_objects_v2 = MagicMock(return_value={"Contents": []})
    mock_s3.get_paginator = MagicMock(return_value=MagicMock(
        paginate=lambda **kwargs: [{"Contents": []}]
    ))
    mock_s3.delete_object = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 204}})

    # Patch boto3.client to return our mock
    with patch("boto3.client", return_value=mock_s3):
        yield
