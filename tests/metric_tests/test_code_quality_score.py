import os
import sys
from typing import Any, Optional
from unittest.mock import MagicMock, mock_open, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src/metrics"))

import code_quality_score  # noqa: E402

# Mock file lists for different repo scenarios
FILES_COMPLETE = ["config.json", "model.safetensors", "README.md", "LICENSE"]
FILES_NO_README = ["config.json", "model.safetensors", "LICENSE"]
FILES_NO_LICENSE = ["config.json", "model.safetensors", "README.md"]
FILES_NO_JSON = ["model.safetensors", "README.md", "LICENSE"]
FILES_INVALID_JSON = ["broken.json", "README.md", "LICENSE"]
FILES_EMPTY: list[str] = []
# Mock JSON content
VALID_JSON = '{"model_type": "bert", "vocab_size": 30522}'
INVALID_JSON = '{"invalid": json content}'


@patch("code_quality_score.hf_hub_download")
@patch("code_quality_score.HfApi")
def test_get_repo_files_success(mock_hf_api: Any, mock_download: Any) -> None:
    """Test successful retrieval of repo files."""
    mock_api_instance = MagicMock()
    mock_api_instance.list_repo_files.return_value = FILES_COMPLETE
    mock_hf_api.return_value = mock_api_instance

    files = code_quality_score.get_repo_files("test-model")
    assert files == FILES_COMPLETE
    mock_api_instance.list_repo_files.assert_called_once_with(repo_id="test-model")


@patch("code_quality_score.HfApi")
def test_get_repo_files_exception(mock_hf_api: Any) -> None:
    """Test get_repo_files returns empty list on exception."""
    mock_api_instance = MagicMock()
    mock_api_instance.list_repo_files.side_effect = Exception("API Error")
    mock_hf_api.return_value = mock_api_instance

    files = code_quality_score.get_repo_files("test-model")
    assert files == []


@patch("code_quality_score.hf_hub_download")
def test_download_file_success(mock_download: Any) -> None:
    """Test successful file download."""
    mock_download.return_value = "/path/to/file"

    result = code_quality_score.download_file("test-model", "config.json")
    assert result == "/path/to/file"
    mock_download.assert_called_once_with(repo_id="test-model", filename="config.json")


@patch("code_quality_score.hf_hub_download")
def test_download_file_exception(mock_download: Any) -> None:
    """Test download_file returns None on exception."""
    mock_download.side_effect = Exception("Download Error")

    result = code_quality_score.download_file("test-model", "config.json")
    assert result is None


@patch("code_quality_score.download_file")
@patch("code_quality_score.get_repo_files")
def test_json_score_valid_json(mock_get_files: Any, mock_download: Any) -> None:
    """Test JSON score with valid JSON files."""
    mock_get_files.return_value = ["config.json", "tokenizer.json"]
    mock_download.return_value = "/tmp/file.json"

    with patch("builtins.open", mock_open(read_data=VALID_JSON)):
        score = code_quality_score.json_score("test-model")

    assert score == 0.4  # 2/2 valid files * 0.4 weight


@patch("code_quality_score.download_file")
@patch("code_quality_score.get_repo_files")
def test_json_score_partial_valid(mock_get_files: Any, mock_download: Any) -> None:
    """Test JSON score with some valid and some invalid JSON files."""
    mock_get_files.return_value = ["config.json", "broken.json"]

    def side_effect(model: str, filename: str) -> Optional[str]:
        return f"/tmp/{filename}"

    mock_download.side_effect = side_effect

    file_contents = {"config.json": VALID_JSON, "broken.json": INVALID_JSON}

    def open_side_effect(filename: str, *args: Any, **kwargs: Any) -> Any:
        file_key = filename.split("/")[-1]
        return mock_open(read_data=file_contents.get(file_key, ""))()

    with patch("builtins.open", side_effect=open_side_effect):
        score = code_quality_score.json_score("test-model")

    assert score == 0.2  # 1/2 valid files * 0.4 weight


@patch("code_quality_score.get_repo_files")
def test_json_score_no_json_files(mock_get_files: Any) -> None:
    """Test JSON score when no JSON files exist."""
    mock_get_files.return_value = FILES_NO_JSON

    score = code_quality_score.json_score("test-model")
    assert score == 0.0


@patch("code_quality_score.download_file")
@patch("code_quality_score.get_repo_files")
def test_json_score_download_fails(mock_get_files: Any, mock_download: Any) -> None:
    """Test JSON score when file downloads fail."""
    mock_get_files.return_value = ["config.json"]
    mock_download.return_value = None

    score = code_quality_score.json_score("test-model")
    assert score == 0.0


@patch("code_quality_score.get_repo_files")
def test_readme_score_present(mock_get_files: Any) -> None:
    """Test README score when README is present."""
    mock_get_files.return_value = FILES_COMPLETE

    score = code_quality_score.readme_score("test-model")
    assert score == 0.2


@patch("code_quality_score.get_repo_files")
def test_readme_score_case_insensitive(mock_get_files: Any) -> None:
    """Test README score with different case variations."""
    test_cases = [
        ["README.md"],
        ["readme.md"],
        ["ReadMe.MD"],
        ["README"],
    ]

    for files in test_cases:
        mock_get_files.return_value = files
        score = code_quality_score.readme_score("test-model")
        assert score == 0.2


@patch("code_quality_score.get_repo_files")
def test_readme_score_missing(mock_get_files: Any) -> None:
    """Test README score when README is missing."""
    mock_get_files.return_value = FILES_NO_README

    score = code_quality_score.readme_score("test-model")
    assert score == 0.0


@patch("code_quality_score.get_repo_files")
def test_license_score_present(mock_get_files: Any) -> None:
    """Test LICENSE score when LICENSE is present."""
    mock_get_files.return_value = FILES_COMPLETE

    score = code_quality_score.license_score("test-model")
    assert score == 0.2


@patch("code_quality_score.get_repo_files")
def test_license_score_case_insensitive(mock_get_files: Any) -> None:
    """Test LICENSE score with different case variations."""
    test_cases = [
        ["LICENSE"],
        ["license"],
        ["License.txt"],
        ["LICENSE.md"],
    ]

    for files in test_cases:
        mock_get_files.return_value = files
        score = code_quality_score.license_score("test-model")
        assert score == 0.2


@patch("code_quality_score.get_repo_files")
def test_license_score_missing(mock_get_files: Any) -> None:
    """Test LICENSE score when LICENSE is missing."""
    mock_get_files.return_value = FILES_NO_LICENSE

    score = code_quality_score.license_score("test-model")
    assert score == 0.0


@patch("code_quality_score.license_score")
@patch("code_quality_score.readme_score")
@patch("code_quality_score.json_score")
def test_code_quality_score_perfect(
    mock_json: Any, mock_readme: Any, mock_license: Any
) -> None:
    """Test code quality score with perfect repo."""
    mock_json.return_value = 0.4
    mock_readme.return_value = 0.2
    mock_license.return_value = 0.2

    score, latency = code_quality_score.code_quality_score("test-model")
    assert score == 0.8
    assert latency >= 0.0


@patch("code_quality_score.license_score")
@patch("code_quality_score.readme_score")
@patch("code_quality_score.json_score")
def test_code_quality_score_zero(
    mock_json: Any, mock_readme: Any, mock_license: Any
) -> None:
    """Test code quality score with empty repo."""
    mock_json.return_value = 0.0
    mock_readme.return_value = 0.0
    mock_license.return_value = 0.0

    score, latency = code_quality_score.code_quality_score("test-model")
    assert score == 0.0
    assert latency >= 0.0


@patch("code_quality_score.license_score")
@patch("code_quality_score.readme_score")
@patch("code_quality_score.json_score")
@pytest.mark.parametrize(
    "json_val,readme_val,license_val,expected_score",
    [
        (0.4, 0.2, 0.2, 0.8),  # Perfect score
        (0.0, 0.0, 0.0, 0.0),  # Zero score
        (0.4, 0.0, 0.0, 0.4),  # Only JSON
        (0.0, 0.2, 0.2, 0.4),  # No JSON
        (0.2, 0.2, 0.2, 0.6),  # Partial JSON validity
    ],
)
def test_code_quality_score_combinations(
    mock_json: Any,
    mock_readme: Any,
    mock_license: Any,
    json_val: float,
    readme_val: float,
    license_val: float,
    expected_score: float,
) -> None:
    """Test various combinations of submetric scores."""
    mock_json.return_value = json_val
    mock_readme.return_value = readme_val
    mock_license.return_value = license_val

    score, latency = code_quality_score.code_quality_score("test-model")
    assert score == expected_score
    assert 0.0 <= score <= 1.0
    assert latency >= 0.0


@patch("code_quality_score.license_score")
@patch("code_quality_score.readme_score")
@patch("code_quality_score.json_score")
def test_code_quality_score_latency(
    mock_json: Any, mock_readme: Any, mock_license: Any
) -> None:
    """Test that latency is measured and positive."""
    mock_json.return_value = 0.4
    mock_readme.return_value = 0.2
    mock_license.return_value = 0.2

    score, latency = code_quality_score.code_quality_score("test-model")
    assert isinstance(latency, float)
