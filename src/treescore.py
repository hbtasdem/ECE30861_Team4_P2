#!/usr/bin/env python3
"""this file is not finalized, it is a hardcoded placeholder for the more complex treescore calc which will take place
once models are uploaded to the registry and therefore have recorded score"""
import time
from typing import Tuple

import lineage_tree


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
        print("Example: treescore.py microsoft/DialoGPT-medium")
        sys.exit(1)

    for model_id in sys.argv[1:]:
        score, latency = treescore_calc(model_id)
        print(f"\nTreescore for {model_id}: {score:.4f}")
        print(f"Latency: {latency:.3f}s")

"""this part can be used for complex calcs once registry is uploaded and metric scores are calculated for models
That way, this set up will be able to pull the already calculates model scores for parents of the lineage graph"""
# !/usr/bin/env python3

# import time
# import json
# import os
# import lineage_tree

# MODEL_REGISTRY_FILE = "model_registry.json"


# def load_model_registry():
#     """Load the model registry from file."""
#     if os.path.exists(MODEL_REGISTRY_FILE):
#         try:
#             with open(MODEL_REGISTRY_FILE, 'r') as f:
#                 return json.load(f)
#         except Exception as e:
#             print(f"Warning: Could not load model registry: {e}")
#     return {}


# def get_parent_scores(model_identifier: str, max_depth: int = 3):
#     """
#     Get scores for all parents in the lineage tree.
#     Returns a list of (model_name, score) tuples.
#     """
#     registry = load_model_registry()
#     parent_scores = []
#     visited = set()  # Prevent circular references

#     def traverse(model_id, depth):
#         if depth >= max_depth or model_id in visited:
#             return

#         visited.add(model_id)

#         # Get lineage info
#         lineage_info, _ = lineage_tree.check_lineage(model_id)

#         if not lineage_info or not lineage_info.get("has_lineage"):
#             return

#         base_model = lineage_info.get("base_model")
#         if not base_model:
#             return

#         # Check if parent score exists in registry
#         if base_model in registry:
#             score = registry[base_model].get("net_score", 0.0)
#             parent_scores.append((base_model, score))

#             # Recursively check parent's parents
#             traverse(base_model, depth + 1)

#     # Start traversal
#     traverse(model_identifier, 0)

#     return parent_scores


# def treescore_calc(model_identifier: str):
#     """
#     Calculate tree score by averaging net scores of all parent models.

#     Score calculation:
#     - If no parents found: 0.0
#     - If parents found: average of all parent net_scores

#     Returns (score, latency_in_seconds)
#     """
#     start_time = time.time()

#     parent_scores = get_parent_scores(model_identifier, max_depth=3)

#     if not parent_scores:
#         # No parent models found or no scores available
#         return 0.0, time.time() - start_time

#     # Calculate average of parent scores
#     total_score = sum(score for _, score in parent_scores)
#     avg_score = total_score / len(parent_scores)

#     total_latency = time.time() - start_time
#     return avg_score, total_latency


# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) < 2:
#         print("Usage: treescore.py <model_identifier>")
#         print("Example: treescore.py microsoft/DialoGPT-medium")
#         sys.exit(1)

#     for model_id in sys.argv[1:]:
#         score, latency = treescore_calc(model_id)
#         print(f"\nTreescore for {model_id}: {score:.4f}")
#         print(f"Latency: {latency:.3f}s")
