#!/usr/bin/env python3

import json
import time
from typing import Any, Dict, Optional, Tuple, cast

import requests


def get_model_config(model_identifier: str) -> Optional[Dict[str, Any]]:
    """
    Return JSON metadata for a Hugging Face model via API.
    model_identifier can be either:
    - Full URL: https://huggingface.co/microsoft/DialoGPT-medium
    - Model path: microsoft/DialoGPT-medium
    """
    # Clean up the model identifier
    if "huggingface.co/" in model_identifier:
        # Extract path from URL
        model_path = model_identifier.split("huggingface.co/")[1]
        model_path = model_path.split("/tree")[0].split("/blob")[0].strip("/")
    else:
        model_path = model_identifier.strip()

    api_url = f"https://huggingface.co/api/models/{model_path}"

    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())
    except Exception as e:
        print(f"Could not fetch HF API metadata for {model_path}: {e}")
        return None


def check_lineage(model_identifier: str) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Create a lineage tree by checking base-model tag in the metadata.
    Returns a dict with lineage information and the score calculation time.
    """
    start_time = time.time()

    metadata = get_model_config(model_identifier)

    if not metadata:
        return None, time.time() - start_time

    lineage_info = {
        "model": model_identifier,
        "base_model": None,
        "has_lineage": False,
        "lineage_depth": 0,
    }

    # Check for base_model in metadata
    # Common locations: metadata['base_model'], metadata['tags'], metadata['cardData']
    if isinstance(metadata, dict):
        # Direct base_model field
        if "base_model" in metadata:
            lineage_info["base_model"] = metadata["base_model"]
            lineage_info["has_lineage"] = True
            lineage_info["lineage_depth"] = 1

        # Check in cardData
        elif "cardData" in metadata and isinstance(metadata["cardData"], dict):
            if "base_model" in metadata["cardData"]:
                lineage_info["base_model"] = metadata["cardData"]["base_model"]
                lineage_info["has_lineage"] = True
                lineage_info["lineage_depth"] = 1

        # Check tags for base model references
        elif "tags" in metadata and isinstance(metadata["tags"], list):
            for tag in metadata["tags"]:
                if isinstance(tag, str) and tag.startswith("base_model:"):
                    lineage_info["base_model"] = tag.replace("base_model:", "")
                    lineage_info["has_lineage"] = True
                    lineage_info["lineage_depth"] = 1
                    break

    elapsed_time = time.time() - start_time
    return lineage_info, elapsed_time


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: lineage_tree.py <model_identifier>")
        print("Example: lineage_tree.py microsoft/DialoGPT-medium")
        sys.exit(1)

    for model_id in sys.argv[1:]:
        lineage_info, latency = check_lineage(model_id)
        if lineage_info:
            print(f"\nLineage info for {model_id}:")
            print(json.dumps(lineage_info, indent=2))
            print(f"Latency: {latency:.3f}s")
        else:
            print(f"\nCould not fetch lineage for {model_id}")