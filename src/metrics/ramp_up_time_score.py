import math
import time
from typing import Tuple

from src.hugging_face_api import get_model_info
from src.metrics.license_score import fetch_readme


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
    - Downloads (25% weight)
    - Likes (25% weight)
    - README exists and quality (30% weight)
    - Code example in README (20% weight)
    Returns (score, elapsed_time)
    """
    start = time.time()
    score = 0.0

    # Get model info from Hugging Face API
    info, _ = get_model_info(model_id)
    if info is None:
        return 0.0, time.time() - start

    # 1. Downloads (weight: 0.25)
    downloads_score = normalize_sigmoid(
        value=info.get("downloads", 0), mid=100, steepness=0.01
    )
    score += downloads_score * 0.25

    # 2. Likes (weight: 0.25)
    likes_score = normalize_sigmoid(
        value=info.get("likes", 0), mid=5, steepness=0.2
    )
    score += likes_score * 0.25

    # 3. README exists and quality (weight: 0.30)
    readme = fetch_readme(model_id)
    if readme:
        # Base score for having a README
        readme_score = 0.5

        # Bonus for README length (longer = more detailed)
        readme_length = len(readme)
        if readme_length > 500:
            readme_score += 0.25
        if readme_length > 2000:
            readme_score += 0.25

        score += readme_score * 0.30

        # 4. Code example in README (weight: 0.20)
        # Look for actual code blocks (```) and common code patterns
        has_code_block = "```" in readme
        has_code_keywords = any(
            keyword in readme.lower()
            for keyword in ["import", "from ", "def ", "class ", "model.forward", "example"]
        )

        if has_code_block and has_code_keywords:
            score += 1.0 * 0.20
        elif has_code_block or has_code_keywords:
            score += 0.5 * 0.20

    # Score is already weighted to 0-1 range
    score = round(score, 2)
    return score, time.time() - start


if __name__ == "__main__":
    model_id = "google/gemma-2b"
    score, elapsed = ramp_up_time_score(model_id)
    print(f"Ramp up time score: {score:.2f} (elapsed: {elapsed:.2f}s)")
