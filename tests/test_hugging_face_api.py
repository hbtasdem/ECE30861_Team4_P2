import json
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
import requests

from src import hugging_face_api

# Sample API response data
VALID_MODEL_RESPONSE: Dict[str, Any] = {
    "id": "gpt2",
    "modelId": "gpt2",
    "author": "openai-community",
    "downloads": 1000000,
    "likes": 500,
    "library_name": "transformers",
    "tags": ["text-generation", "pytorch"],
    "cardData": {"license": "mit"},
}

MINIMAL_MODEL_RESPONSE: Dict[str, Any] = {
    "id": "test/minimal-model",
    "modelId": "test/minimal-model",
}

EMPTY_MODEL_RESPONSE: Dict[str, Any] = {}


@pytest.mark.parametrize(
    "model_id,expected_success",
    [
        ("gpt2", True),
        ("microsoft/DialoGPT-large", True),
        ("bert-base-uncased", True),
        ("", False),
        ("   ", False),
        ("facebook/bart-large", True),
    ],
)
def test_get_model_info_inputs(
    monkeypatch: pytest.MonkeyPatch, model_id: str, expected_success: bool
) -> None:
    """Test various input formats for model_id parameter."""

    def mock_requests_get(url: str, timeout: int) -> Mock:
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = VALID_MODEL_RESPONSE
        return mock_resp

    monkeypatch.setattr("requests.get", mock_requests_get)

    model_info, elapsed = hugging_face_api.get_model_info(model_id)

    if expected_success:
        assert model_info is not None
        assert isinstance(model_info, dict)
    else:
        assert model_info is None

    assert elapsed >= 0


@patch("requests.get")
def test_get_model_info_success(mock_get: Mock) -> None:
    """Test successful API call with full response."""
    mock_resp = Mock()
    mock_resp.raise_for_status = Mock()
    mock_resp.json.return_value = VALID_MODEL_RESPONSE
    mock_get.return_value = mock_resp

    model_info, elapsed = hugging_face_api.get_model_info("gpt2")

    assert model_info is not None
    assert model_info["id"] == "gpt2"
    assert model_info["author"] == "openai-community"
    assert model_info["cardData"]["license"] == "mit"
    assert elapsed >= 0

    # Verify correct API URL was called
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "gpt2" in args[0]
    assert kwargs["timeout"] == 10


@patch("requests.get")
def test_get_model_info_minimal_response(mock_get: Mock) -> None:
    """Test handling of minimal API response."""
    mock_resp = Mock()
    mock_resp.raise_for_status = Mock()
    mock_resp.json.return_value = MINIMAL_MODEL_RESPONSE
    mock_get.return_value = mock_resp

    model_info, elapsed = hugging_face_api.get_model_info("test/minimal")

    assert model_info is not None
    assert model_info["id"] == "test/minimal-model"
    assert elapsed >= 0


@patch("requests.get")
def test_get_model_info_empty_response(mock_get: Mock) -> None:
    """Test handling of empty but valid JSON response."""
    mock_resp = Mock()
    mock_resp.raise_for_status = Mock()
    mock_resp.json.return_value = EMPTY_MODEL_RESPONSE
    mock_get.return_value = mock_resp

    model_info, elapsed = hugging_face_api.get_model_info("test/empty")

    assert model_info is not None
    assert isinstance(model_info, dict)
    assert len(model_info) == 0
    assert elapsed >= 0


@patch("requests.get")
def test_get_model_info_http_404(mock_get: Mock) -> None:
    """Test handling of 404 Not Found."""
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=Mock(status_code=404)
    )
    mock_get.return_value = mock_resp

    model_info, elapsed = hugging_face_api.get_model_info("nonexistent/model")

    assert model_info is None
    assert elapsed >= 0


@patch("requests.get")
def test_get_model_info_http_500(mock_get: Mock) -> None:
    """Test handling of server errors."""
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=Mock(status_code=500)
    )
    mock_get.return_value = mock_resp

    model_info, elapsed = hugging_face_api.get_model_info("test/model")

    assert model_info is None
    assert elapsed >= 0


@patch("requests.get")
def test_get_model_info_timeout(mock_get: Mock) -> None:
    """Test handling of request timeout."""
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

    model_info, elapsed = hugging_face_api.get_model_info("test/model")

    assert model_info is None
    assert elapsed >= 0


@patch("requests.get")
def test_get_model_info_connection_error(mock_get: Mock) -> None:
    """Test handling of network connection errors."""
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

    model_info, elapsed = hugging_face_api.get_model_info("test/model")

    assert model_info is None
    assert elapsed >= 0


@patch("requests.get")
def test_get_model_info_json_decode_error(mock_get: Mock) -> None:
    """Test handling of malformed JSON response."""
    mock_resp = Mock()
    mock_resp.raise_for_status = Mock()
    mock_resp.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
    mock_get.return_value = mock_resp

    model_info, elapsed = hugging_face_api.get_model_info("test/model")

    assert model_info is None
    assert elapsed >= 0


def test_get_model_info_strips_whitespace() -> None:
    """Test that model_id whitespace is properly stripped."""
    with patch("requests.get") as mock_get:
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = VALID_MODEL_RESPONSE
        mock_get.return_value = mock_resp

        model_info, elapsed = hugging_face_api.get_model_info("  gpt2  ")

        assert model_info is not None
        # Verify the stripped model_id was used in the URL
        args, _ = mock_get.call_args
        assert "gpt2" in args[0]
        assert "  " not in args[0]


@patch("requests.get")
def test_get_model_info_api_url_construction(mock_get: Mock) -> None:
    """Test that API URLs are constructed correctly."""
    mock_resp = Mock()
    mock_resp.raise_for_status = Mock()
    mock_resp.json.return_value = VALID_MODEL_RESPONSE
    mock_get.return_value = mock_resp

    hugging_face_api.get_model_info("test/model")

    args, _ = mock_get.call_args
    expected_url = f"{hugging_face_api.HF_API_BASE}/models/test/model"
    assert args[0] == expected_url


def test_timing_measurement() -> None:
    """Test that execution time is properly measured."""
    with patch("requests.get") as mock_get:
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = VALID_MODEL_RESPONSE
        mock_get.return_value = mock_resp

        model_info, elapsed = hugging_face_api.get_model_info("test/model")

        assert elapsed >= 0.0
        assert isinstance(elapsed, float)


@patch("os.getenv")
@patch("requests.get")
def test_log_level_environment_variable(mock_get: Mock, mock_getenv: Mock) -> None:
    """Test that LOG_LEVEL environment variable controls error printing."""
    mock_get.side_effect = Exception("Test error")

    # Test with LOG_LEVEL = 0 (no logging)
    mock_getenv.return_value = "0"
    model_info, elapsed = hugging_face_api.get_model_info("test/model")
    assert model_info is None

    # Test with LOG_LEVEL = 1 (logging enabled)
    mock_getenv.return_value = "1"
    model_info, elapsed = hugging_face_api.get_model_info("test/model")
    assert model_info is None
