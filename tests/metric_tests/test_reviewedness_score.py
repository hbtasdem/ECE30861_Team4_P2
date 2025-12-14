import os
import sys

from reviewedness_score import reviewedness_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src/metrics"))


def test_reviewedness_bert_repo():
    """Test reviewedness score for google-research/bert repo (expects 0)."""
    code_url = "https://github.com/google-research/bert"
    reviewedness, latency = reviewedness_score(code_url)

    assert reviewedness == 0.0, f"Expected reviewedness of 0.0, got {reviewedness}"
    assert latency >= 0, f"Expected non-negative latency, got {latency}"
    assert isinstance(latency, (int, float)), "Latency should be numeric"


def test_reviewedness_requests_repo():
    """Test reviewedness score for psf/requests repo (expects 1)."""
    code_url = "https://github.com/psf/requests"
    reviewedness, latency = reviewedness_score(code_url)

    assert reviewedness == 1.0, f"Expected reviewedness of 1.0, got {reviewedness}"
    assert latency >= 0, f"Expected non-negative latency, got {latency}"
    assert isinstance(latency, (int, float)), "Latency should be numeric"


def test_reviewedness_invalid_url():
    """Test reviewedness score with no URL (expects -1)."""
    code_url = ""
    reviewedness, latency = reviewedness_score(code_url)

    assert (
        reviewedness == -1
    ), f"Expected reviewedness of -1 for empty URL, got {reviewedness}"
    assert latency >= 0, f"Expected non-negative latency, got {latency}"


def test_reviewedness_none_url():
    """Test reviewedness score with None URL (expects -1)."""
    code_url = None
    reviewedness, latency = reviewedness_score(code_url)

    assert (
        reviewedness == -1
    ), f"Expected reviewedness of -1 for None URL, got {reviewedness}"
    assert latency >= 0, f"Expected non-negative latency, got {latency}"
