import pytest
from src.size_cost import get_model_size_gb

# Global tolerance (± in GB)
TOLERANCE_PERCENT = 0.05


def is_within_tolerance(actual: float, expected: float, pct_tol: float = TOLERANCE_PERCENT) -> bool:
    """
    Return True if the % difference between actual & expected is <= tolerance.
    % difference = abs(actual - expected) / expected
    """
    if expected == 0:
        return actual == 0  # avoid division by zero, edge-case
    percent_diff = abs(actual - expected) / expected
    return percent_diff <= pct_tol


@pytest.mark.parametrize(
    "model_id, expected_size",
    [
        ("parvk11/audience_classifier_model", 0.268),
        ("microsoft/DialoGPT-medium",         5.43),
        ("openai/whisper-tiny",               0.609),
        ("google-bert/bert-base-uncased",     3.45),
        ("tencent/HunyuanOCR",                2.0),
        ("Tongyi-MAI/Z-Image-Turbo",          32.9),
        # ("deepseek-ai/DeepSeek-Math-V2",      689),
        ("microsoft/Fara-7B",                 16.6),

    ]
)
def test_get_model_size_gb(model_id, expected_size):
    actual_size = get_model_size_gb(model_id)
    assert is_within_tolerance(actual_size, expected_size), (
        f"{model_id}: expected ~{expected_size}GB ±{TOLERANCE_PERCENT}, "
        f"but got {actual_size}GB"
    )
