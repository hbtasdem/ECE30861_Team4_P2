#!/usr/bin/env python3
"""this file is not finalized, it is a hardcoded placeholder for the more complex treescore calc which will take place
once models are uploaded to the registry and therefore have recorded score"""
import os
import sys
import time
from typing import Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lineage_tree  # noqa: E402


def treescore_calc(model_name: str) -> Tuple[float, float]:
    """
    Calculate tree score based on model lineage depth and quality.
    Score is based on:
    - Whether the model has documented lineage (base model)
    - The "reputation" of the base model (if recognizable)
    - Depth of lineage chain

    Returns (score, latency_in_seconds)
    """
    start_time = time.time()

    lineage_info, lineage_latency = lineage_tree.check_lineage(model_name)

    if not lineage_info or not lineage_info["has_lineage"]:
        # No lineage info available - score 0
        return 0.0, time.time() - start_time

    score = 0.0
    base_model = lineage_info.get("base_model", "")

    # Base score for having lineage documentation (0.3 points)
    score += 0.3

    # Additional points for well-known/reputable base models (0.5 points)
    reputable_bases = [
        "bert",
        "gpt2",
        "roberta",
        "t5",
        "bart",
        "distilbert",
        "llama",
        "mistral",
        "falcon",
        "bloom",
        "opt",
        "pythia",
        "gpt-neo",
        "gpt-j",
        "whisper",
        "wav2vec",
        "clip",
        "vit",
    ]

    if base_model and any(base in base_model.lower() for base in reputable_bases):
        score += 0.5

    # Check if base model has its own lineage (depth > 1) - up to 0.2 points
    if base_model:
        parent_lineage, _ = lineage_tree.check_lineage(base_model)
        if parent_lineage and parent_lineage["has_lineage"]:
            score += 0.2

    # Cap score at 1.0
    score = min(score, 1.0)

    total_latency = time.time() - start_time
    return score, total_latency


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: treescore.py <model_identifier>")
        print("Example: tree_score.py microsoft/DialoGPT-medium")
        sys.exit(1)

    for model_id in sys.argv[1:]:
        score, latency = treescore_calc(model_id)
        print(f"\nTreescore for {model_id}: {score:.4f}")
        print(f"Latency: {latency:.3f}s")

"""this part can be used for complex calcs once registry is uploaded and metric scores are calculated for models
That way, this set up will be able to pull the already calculates model scores for parents of the lineage graph"""
