from typing import Optional
from unittest.mock import Mock, patch

import pytest

from src import license_sub_score as license

README_YAML: str = """---
name: Example Model
license: MIT
---
# Model
This is a test model.
"""

README_MD: str = """
# Example Model

## License
Apache-1.0
"""

README_NONE: str = """
# Example Model
No license here.
"""

README_MULTIPLE: str = """
# Model
## License
MIT
## License
GPL-2.0
"""

README_EMPTY: str = ""


@pytest.mark.parametrize(
    "readme_text,expected_score",
    [
        (README_YAML, 1),
        (README_MD, 0),
        (README_NONE, 0),
        ("---\nlicense: Apache-1.0\n---", 0),
        ("---\nlicense: MIT License\n---", 1),
    ],
)  # type: ignore[misc]
def test_license_sub_score(
    monkeypatch: pytest.MonkeyPatch, readme_text: str, expected_score: int
) -> None:
    def mock_fetch_readme(url: str) -> str:
        return readme_text

    monkeypatch.setattr(license, "fetch_readme", mock_fetch_readme)
    score, elapsed = license.license_sub_score("https://huggingface.co/mock-model")
    assert score == expected_score
    assert elapsed >= 0


def test_license_sub_score_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_fetch_readme(url: str) -> str:
        return README_EMPTY

    monkeypatch.setattr(license, "fetch_readme", mock_fetch_readme)
    score, _ = license.license_sub_score("https://huggingface.co/mock-model")
    assert score == 0


def test_extract_license_yaml() -> None:
    license_str: Optional[str] = license.extract_license(README_YAML)
    assert license_str == "mit"


def test_extract_license_md() -> None:
    license_str: Optional[str] = license.extract_license(README_MD)
    assert license_str == "apache-1.0"


def test_extract_license_none() -> None:
    license_str: Optional[str] = license.extract_license(README_NONE)
    assert license_str is None


def test_extract_license_multiple() -> None:
    license_str: Optional[str] = license.extract_license(README_MULTIPLE)
    assert license_str is not None
    assert license_str.lower() == "mit"


@patch("requests.get")
def test_fetch_readme_success(mock_get: Mock) -> None:
    mock_resp: Mock = Mock()
    mock_resp.raise_for_status = Mock()
    mock_resp.text = README_YAML
    mock_get.return_value = mock_resp

    result: Optional[str] = license.fetch_readme("https://huggingface.co/mock-model")
    assert result is not None
    assert "MIT" in result


@patch("requests.get")
def test_fetch_readme_tree_main(mock_get: Mock) -> None:
    mock_resp: Mock = Mock()
    mock_resp.raise_for_status = Mock()
    mock_resp.text = "Tree main README"
    mock_get.return_value = mock_resp

    result: Optional[str] = license.fetch_readme(
        "https://huggingface.co/model/tree/main"
    )
    assert result is not None
    assert result == "Tree main README"


@patch("requests.get")
def test_fetch_readme_failure(mock_get: Mock) -> None:
    mock_get.side_effect = Exception("Network error")
    result: Optional[str] = license.fetch_readme("https://huggingface.co/mock-model")
    assert result is None
