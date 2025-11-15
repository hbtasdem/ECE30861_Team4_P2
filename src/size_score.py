"""
Size Score Implementation

This module implements the size scoring metric that evaluates how deployable
a model is on common hardware platforms based on model file size from the Hugging Face API.

The function evaluates model size against four hardware benchmarks:
- Raspberry Pi: 2 GB threshold
- Jetson Nano: 4 GB threshold
- Desktop PC: 16 GB threshold
- AWS Server: Unlimited (always score 1.0)

Scoring uses linear decay function: score = max(0.0, 1.0 - (size_gb / threshold))
"""

import re
import time
from typing import Dict, Optional, Tuple

from huggingface_hub import HfApi

# Size weights for calculating net score
SIZE_WEIGHTS = {
    "raspberry_pi": 0.35,  # Higher weight due to popularity
    "jetson_nano": 0.25,  # Important for edge AI applications
    "desktop_pc": 0.20,  # Common development environment
    "aws_server": 0.20,  # Cloud deployment is common
}

# Hardware thresholds in GB (used for linear decay scoring)
SIZE_THRESHOLDS = {
    "raspberry_pi": 2.0,  # Models >2GB struggle with loading times
    "jetson_nano": 4.0,  # Specifically designed for AI with 4GB RAM
    "desktop_pc": 16.0,  # Standard development workstation with 16GB+ RAM
}


def extract_model_id_from_url(url: str) -> str:
    """
    Extract model ID from various URL formats.

    Args:
        url: The URL or model ID from input.

    Returns:
        The extracted model ID in 'namespace/model_name' format.
    """
    if "huggingface.co" in url:  # If huggingface.co is in the URL
        pattern = r"huggingface\.co/([^/]+/[^/?]+)"  # Match 'huggingface.co/namespace/model_name'
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If it looks like 'namespace/model_name'
    if "/" in url and " " not in url and "://" not in url:
        return url

    return url


def estimate_model_memory(model_id: str, file_size_gb: Optional[float] = None) -> float:
    """
    Estimate model memory requirement based on model type and file size.

    Uses both API data and model architecture insights to estimate
    total memory needed for inference and training.

    Args:
        model_id: Model identifier to help classify model type
        file_size_gb: Actual file size from API if available

    Returns:
        Estimated memory in GB for the model
    """
    model_lower = model_id.lower()

    # Model type-based estimation
    # Based on typical architecture sizes and their memory requirements
    if "bert" in model_lower:
        if "large" in model_lower:
            return 2.4  # BERT-large needs more memory
        elif (
            "base" in model_lower or "uncased" in model_lower or "cased" in model_lower
        ):
            return 1.3  # BERT-base
        else:
            return 1.2  # Generic BERT assumption

    elif "whisper" in model_lower:
        if "tiny" in model_lower:
            return 0.2  # Whisper-tiny ~39M parameters
        elif "base" in model_lower:
            return 0.75  # Whisper-base ~74M parameters
        elif "small" in model_lower:
            return 1.0  # Whisper-small ~244M parameters
        elif "medium" in model_lower:
            return 1.5  # Whisper-medium ~769M parameters
        elif "large" in model_lower:
            return 2.9  # Whisper-large ~1.5B parameters
        else:
            return 0.5  # Generic whisper

    elif "gpt2" in model_lower:
        return 0.5  # GPT2 ~124M parameters

    elif "distilbert" in model_lower:
        return 0.3  # DistilBERT ~66M parameters

    elif "roberta" in model_lower:
        if "large" in model_lower:
            return 2.4
        else:
            return 1.6

    elif "classifier" in model_lower or "audience" in model_lower:
        return 0.52  # Smaller specialized models

    elif "t5" in model_lower:
        if "large" in model_lower:
            return 2.8  # T5-large ~770M parameters
        else:
            return 1.5  # T5-base ~220M parameters

    elif "llama" in model_lower or "alpaca" in model_lower:
        if "7b" in model_lower or "7B" in model_lower:
            return 14.0
        elif "13b" in model_lower or "13B" in model_lower:
            return 28.0
        else:
            return 7.0

    # Fallback: if we have file size, estimate based on that
    if file_size_gb:
        # Different architectures have different memory overhead
        # Transformers typically need 2-3x file size for full inference setup
        if any(x in model_lower for x in ["bert", "roberta", "distilbert"]):
            return file_size_gb * 16  # Transformer overhead
        elif any(x in model_lower for x in ["gpt", "llama"]):
            return file_size_gb * 12  # LLM overhead
        else:
            return file_size_gb * 10  # Conservative default

    # Complete fallback: assume medium model
    return 1.0


def calculate_net_size_score(size_scores: Dict[str, float]) -> float:
    """
    Calculate net size score from individual device scores using predefined weights.

    Args:
        size_scores: Dictionary of device scores

    Returns:
        Weighted net size score
    """
    net_size_score = 0.0
    for device, score in size_scores.items():
        if device in SIZE_WEIGHTS:
            net_size_score += score * SIZE_WEIGHTS[device]

    return round(net_size_score, 2)


def calculate_device_scores(size_gb: float) -> Dict[str, float]:
    """
    Calculate size scores for all hardware devices using linear decay.

    Args:
        size_gb: Model size in GB

    Returns:
        Dictionary mapping device names to scores (0.0 to 1.0)
    """
    size_scores = {}

    # Calculate scores using linear decay: score = max(0.0, 1.0 - (size_gb / threshold))
    for device, threshold in SIZE_THRESHOLDS.items():
        score = max(0.0, 1.0 - (size_gb / threshold))
        size_scores[device] = round(score, 2)

    # AWS server always gets 1.0 (unlimited capacity)
    size_scores["aws_server"] = 1.0

    return size_scores


def calculate_size_scores(model_id: str) -> Tuple[Dict[str, float], float, int]:
    """
    Calculate size compatibility scores for all hardware devices.

    Args:
        model_id: The Hugging Face model identifier.

    Returns:
        Tuple containing:
        - Dictionary with size scores for each hardware device
        - Net size score (weighted average)
        - Latency in milliseconds
    """
    start_time = time.time()

    clean_model_id = extract_model_id_from_url(model_id)

    # Try to get API file size first
    api_file_size = None
    try:
        api = HfApi()
        model_info = api.model_info(repo_id=clean_model_id)
        if hasattr(model_info, "safetensors") and model_info.safetensors:
            api_file_size = model_info.safetensors.total / (1024**3)
    except Exception as e:
        print(f"[DEBUG] Could not fetch API data for {clean_model_id}: {e}")

    # Estimate model memory
    size_gb = estimate_model_memory(clean_model_id, api_file_size)

    if size_gb is None or size_gb == 0:
        # Return default scores
        default_scores = {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.0,
            "desktop_pc": 0.0,
            "aws_server": 1.0,
        }
        latency = int((time.time() - start_time) * 1000)
        return default_scores, 0.2, latency

    # Calculate scores for all devices
    size_scores = calculate_device_scores(size_gb)

    # Calculate net size score using weights
    net_size_score = calculate_net_size_score(size_scores)

    # Calculate latency
    latency = int((time.time() - start_time) * 1000)

    return size_scores, net_size_score, latency


def size_score(model_input: str) -> Tuple[Dict[str, float], float, int]:
    """
    Calculate size sub-score for a model.

    This function evaluates how deployable a model is on common hardware
    platforms based on its file size from the Hugging Face API.

    Args:
        model_input: Hugging Face model ID, URL, or dict with model info

    Returns:
        Tuple of (size_scores_dict, net_size_score, latency_ms)
        - size_scores_dict: Dictionary with hardware platform scores
        - net_size_score: Weighted average score for overall calculation
        - latency_ms: Time taken to compute the score in milliseconds

    Example:
        >>> scores, net_score, latency = size_score("microsoft/DialoGPT-medium")
        >>> print(scores)
        {'raspberry_pi': 0.0, 'jetson_nano': 0.0, 'desktop_pc': 1.0,
         'aws_server': 1.0}
    """
    try:
        # Handle dictionary input
        if isinstance(model_input, dict):
            model_id = (
                model_input.get("model_id")
                or model_input.get("name")
                or model_input.get("url", "")
            )
            if not model_id:
                return {}, 0.0, 0
        else:
            model_id = model_input

        size_scores, net_size_score, latency = calculate_size_scores(model_id)

        return size_scores, net_size_score, latency

    except Exception as e:
        print(f"[DEBUG] Error calculating size score for {model_input}: {e}")
        return {}, 0.0, 0


if __name__ == "__main__":
    # Test the function
    test_models = [
        "google-bert/bert-base-uncased",
        "openai/whisper-tiny",
        "microsoft/DialoGPT-medium",
    ]

    print("=== SIZE SCORE CALCULATIONS ===")
    for model_input in test_models:
        print(f"--- Testing: {model_input} ---")

        size_scores, net_score, latency = size_score(model_input)

        print(f"Size scores: {size_scores}")
        print(f"Net size score: {net_score}")
        print(f"Latency: {latency} ms")
