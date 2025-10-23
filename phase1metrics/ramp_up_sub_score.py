import math
import time
from typing import Tuple

from hugging_face_api import get_model_info
from license_sub_score import fetch_readme


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


def ramp_up_time_score(model_id: str) -> Tuple[float, float]:
    """
    Scores ramp up time based on:
    - Downloads > 0
    - Likes > 0
    - README exists
    - Coding example in README (looks for '```' or 'example' keyword)
    Returns (score, elapsed_time)
    """
    start = time.time()
    score = 0.0

    # Get model info from Hugging Face API
    info, _ = get_model_info(model_id)
    if info is None:
        return 0.0, time.time() - start

    # 1. Downloads
    score += normalize_sigmoid(value=info.get("downloads", 0),
                               mid=10000, steepness=0.0001)

    # 2. Likes
    score += normalize_sigmoid(value=info.get("likes", 0), mid=50,
                               steepness=0.01)

    # 3. README exists
    readme = fetch_readme(model_id)
    if readme:
        score += 1

        # 4. Coding example in README
        if "```" in readme or "example" in readme.lower():
            score += 1

    # Normalize (max score is 4)
    normalized = round(score / 4, 2)
    return normalized, time.time() - start


if __name__ == "__main__":
    model_id = "google/gemma-2b"
    score, elapsed = ramp_up_time_score(model_id)
    print(f"Ramp up time score: {score:.2f} (elapsed: {elapsed:.2f}s)")
