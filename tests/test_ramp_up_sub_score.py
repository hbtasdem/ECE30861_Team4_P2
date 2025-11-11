from typing import Any
from unittest.mock import patch
import sys, os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src/metrics"))
import ramp_up_time_score

README_WITH_CODE = """
# Example Model

This model does something.

## Usage

```python
import model
"""

README_WITH_EXAMPLE = """

Example Model

Here is an example of how to use this model.
"""

README_PLAIN = """

Example Model

No code or example here.
"""

README_NONE = ""


@patch("ramp_up_time_score.get_model_info")
@patch("ramp_up_time_score.fetch_readme")
@pytest.mark.parametrize(
    "downloads,likes,readme,expected_min_score",
    [
        (100000, 500, README_WITH_CODE, 0.99),
        (0, 0, README_NONE, 0.0),
        (10, 1, README_WITH_EXAMPLE, 0.5),
        (10000, 0, README_PLAIN, 0.25),
        (0, 100, README_WITH_CODE, 0.5),
    ],
)
def test_ramp_up_time_score(
    mock_fetch_readme: Any,
    mock_get_model_info: Any,
    downloads: int,
    likes: int,
    readme: str,
    expected_min_score: float,
) -> None:
    mock_get_model_info.return_value = ({"downloads": downloads, "likes": likes}, 0.01)
    mock_fetch_readme.return_value = readme
    score, elapsed = ramp_up_time_score.ramp_up_time_score("mock-model")
    assert score >= expected_min_score
    assert 0.0 <= score <= 1.0
    assert elapsed >= 0


def test_ramp_up_time_score_no_info(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get_model_info(model_id: str) -> tuple[None, float]:
        return None, 0.01

    monkeypatch.setattr(ramp_up_time_score, "get_model_info", mock_get_model_info)
    score, elapsed = ramp_up_time_score.ramp_up_time_score("mock-model")
    assert score == 0.0
    assert elapsed >= 0
