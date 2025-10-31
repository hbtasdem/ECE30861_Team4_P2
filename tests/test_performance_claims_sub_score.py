from typing import Any
from unittest.mock import patch

import pytest

import src.performance_claims_sub_score as performance


@patch("src.performance_claims_sub_score.get_model_info")
@pytest.mark.parametrize(
    "downloads,likes,expected_min_score",
    [
        (100000, 500, 0.99),
        (0, 0, 0.0),
        (10, 1, 0.2),
        (10000, 0, 0.25),
        (0, 100, 0.2),
    ],
)  # type: ignore[misc]
def test_performance_claims_score(
    mock_get_model_info: Any, downloads: int, likes: int, expected_min_score: float
) -> None:
    mock_get_model_info.return_value = ({"downloads": downloads, "likes": likes}, 0.01)
    score, elapsed = performance.performance_claims_sub_score("mock-model")
    assert score >= expected_min_score
    assert 0.0 <= score <= 1.0
    assert elapsed >= 0
