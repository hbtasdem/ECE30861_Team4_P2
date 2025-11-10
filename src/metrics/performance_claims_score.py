import math
import time
from typing import Tuple

from hugging_face_api import get_model_info


def normalize_sigmoid(value: int, mid: int, steepness: float) -> float:
    """
    Sigmoid normalization capped at 1.0
    - mid: value where score ~0.5
    - steepness: controls curve sharpness
    """
    if value <= 0:
        return 0.0
    score = 1 / (1 + math.exp(-steepness * (value - mid)))
    return min(1.0, score)


def performance_claims_sub_score(model_id: str) -> Tuple[float, float]:
    """
    Scores ramp up time based on:
    - Downloads > 0
    - Likes > 0
    Returns (score, elapsed_time)
    """
    start = time.time()
    score = 0.0

    # Get model info from Hugging Face API
    info, _ = get_model_info(model_id)
    if info is None:
        return 0.0, time.time() - start

    # 1. Downloads
    score += normalize_sigmoid(
        value=info.get("downloads", 0), mid=10000, steepness=0.0001
    )

    # 2. Likes
    score += normalize_sigmoid(value=info.get("likes", 0), mid=50, steepness=0.01)

    # Normalize (max score is 2)
    normalized = round(score / 2, 2)
    return normalized, time.time() - start


if __name__ == "__main__":
    model_id = "google/gemma-2b"
    score, elapsed = performance_claims_sub_score(model_id)
    print(f"Performance Claim score: {score:.2f} (elapsed: {elapsed:.2f}s)")
