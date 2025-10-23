"""
Size Score Implementation

This module implements the size scoring metric that evaluates how deployable
a model is on common hardware platforms based on memory requirements.

The function evaluates model memory footprint against four hardware benchmarks:
- 1 GB CPU RAM (Raspberry Pi class)
- 2 GB VRAM (Jetson Nano type GPU)
- 16 GB VRAM (Desktop PC GPU)
- 24 GB VRAM (High-end AWS server/workstation GPU)

Scoring rules:
- < 75% of capacity → score 1 (fits comfortably)
- 75-100% of capacity → score 0.5 (barely fits)
- > 100% of capacity → score 0 (doesn't fit)
"""

import re
import time
from typing import Dict, List, Optional, Tuple

from .logging_config import get_logger, log_error_with_context

logger = get_logger(__name__)

# Hardware memory benchmarks in GB
MEMORY_BENCHMARKS = {
    "raspberry_pi": 1.0,      # 1 GB CPU RAM
    "jetson_nano": 2.0,        # 2 GB VRAM
    "desktop_gpu": 16.0,       # 16 GB VRAM
    "high_end_gpu": 24.0       # 24 GB VRAM
}

# Memory size patterns to extract from README
MEMORY_PATTERNS = [
    r'(\d+(?:\.\d+)?)\s*GB\s*(?:RAM|VRAM|memory|model\s*size)',
    r'model\s*size[:\s]*(\d+(?:\.\d+)?)\s*GB',
    r'memory\s*requirement[:\s]*(\d+(?:\.\d+)?)\s*GB',
    r'(\d+(?:\.\d+)?)\s*GB\s*(?:model|weights|parameters)',
    r'size[:\s]*(\d+(?:\.\d+)?)\s*GB',
    r'(\d+(?:\.\d+)?)\s*GB\s*(?:inference|deployment)',
    r'minimum\s*(\d+(?:\.\d+)?)\s*GB',
    r'recommended\s*(\d+(?:\.\d+)?)\s*GB',
    r'(\d+(?:\.\d+)?)\s*GB\s*(?:GPU|CPU)',
    r'(\d+(?:\.\d+)?)\s*GB\s*(?:required|needed)',
    r'(\d+(?:\.\d+)?)\s*GB',  # Catch any remaining GB patterns
]

# Alternative patterns for different units
UNIT_CONVERSION_PATTERNS = [
    (r'(\d+(?:\.\d+)?)\s*MB', lambda x: float(x) / 1024),  # MB to GB
    (r'(\d+(?:\.\d+)?)\s*TB', lambda x: float(x) * 1024),  # TB to GB
    (r'(\d+(?:\.\d+)?)\s*GiB', lambda x: float(x)),        # GiB ≈ GB
    (r'(\d+(?:\.\d+)?)\s*MiB', lambda x: float(x) / 1024),  # MiB to GB
]


def fetch_readme(model_url: str) -> Optional[str]:
    """
    Fetch README content from a model repository.

    Args:
        model_url: URL to the model repository

    Returns:
        README content as string, or None if fetch fails
    """
    try:
        from urllib.parse import urljoin

        import requests

        # Handle different URL formats
        if 'huggingface.co' in model_url:
            readme_url = urljoin(
                model_url.rstrip('/') + '/', 'raw/main/README.md')
        elif 'github.com' in model_url:
            readme_url = urljoin(
                model_url.rstrip('/') + '/', 'raw/main/README.md')
        else:
            # Try common README paths
            readme_url = urljoin(model_url.rstrip('/') + '/', 'README.md')

        logger.debug(f"Fetching README from: {readme_url}")

        response = requests.get(readme_url, timeout=10)
        response.raise_for_status()

        return response.text

    except Exception as e:
        log_error_with_context(
            e, f"Failed to fetch README from {model_url}", logger)
        return None


def extract_memory_sizes(readme_text: str) -> List[float]:
    """
    Extract memory size requirements from README text.

    Args:
        readme_text: Raw README content

    Returns:
        List of memory sizes in GB found in the README
    """
    if not readme_text:
        return []

    memory_sizes = []

    # Convert to lowercase for case-insensitive matching
    text_lower = readme_text.lower()

    # Extract sizes using GB patterns
    for pattern in MEMORY_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            try:
                size_gb = float(match)
                # Reasonable range check (allow up to 10TB)
                if 0.1 <= size_gb <= 10000:
                    memory_sizes.append(size_gb)
                    logger.debug(f"Found memory size: {size_gb} GB")
            except ValueError:
                continue

    # Extract sizes using alternative units and convert to GB
    for pattern, converter in UNIT_CONVERSION_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            try:
                size_gb = converter(match)  # type: ignore
                # Reasonable range check (allow up to 10TB)
                if 0.1 <= size_gb <= 10000:
                    memory_sizes.append(size_gb)
                    logger.debug(
                        f"Found memory size: {size_gb} GB (converted)")
            except ValueError:
                continue

    # Remove duplicates and sort
    memory_sizes = sorted(list(set(memory_sizes)))
    logger.info(f"Extracted memory sizes: {memory_sizes} GB")

    return memory_sizes


def find_smallest_model_size(memory_sizes: List[float]) -> Optional[float]:
    """
    Find the smallest model size from the list of extracted sizes.

    Args:
        memory_sizes: List of memory sizes in GB

    Returns:
        Smallest memory size in GB, or None if no sizes found
    """
    if not memory_sizes:
        return None

    smallest = min(memory_sizes)
    logger.info(f"Smallest model size: {smallest} GB")
    return smallest


def score_against_benchmark(
        model_size_gb: float, benchmark_gb: float) -> float:
    """
    Score model size against a hardware benchmark.

    Args:
        model_size_gb: Model size in GB
        benchmark_gb: Hardware benchmark capacity in GB

    Returns:
        Score: 1.0 (< 75%), 0.5 (75-100%), 0.0 (> 100%)
    """
    percentage = (model_size_gb / benchmark_gb) * 100

    if percentage < 75:
        score = 1.0
    elif percentage < 100:
        score = 0.5
    else:
        score = 0.0

    logger.debug(
        f"Model {model_size_gb}GB vs {benchmark_gb}GB benchmark: "
        f"{percentage:.1f}% → score {score}")
    return score


def calculate_size_scores(model_size_gb: float) -> Dict[str, float]:
    """
    Calculate size scores for all hardware benchmarks.

    Args:
        model_size_gb: Model size in GB

    Returns:
        Dictionary mapping hardware names to scores
    """
    scores = {}

    for hardware, benchmark_gb in MEMORY_BENCHMARKS.items():
        score = score_against_benchmark(model_size_gb, benchmark_gb)
        scores[hardware] = score

    logger.info(f"Size scores for {model_size_gb}GB model: {scores}")
    return scores


def size_score(model_url: str) -> Tuple[Dict[str, float], float]:
    """
    Calculate size sub-score for a model repository.

    This function evaluates how deployable a model is on common hardware
    platforms based on its memory requirements.

    Args:
        model_url: URL to the model repository

    Returns:
        Tuple of (size_scores_dict, latency_seconds)
        - size_scores_dict: Dictionary with hardware platform scores
        - latency_seconds: Time taken to compute the score

    Example:
        >>> scores, latency = size_score(
        ...     "https://huggingface.co/microsoft/DialoGPT-medium")
        >>> print(scores)
        {'raspberry_pi': 0.0, 'jetson_nano': 0.0, 'desktop_gpu': 1.0,
         'high_end_gpu': 1.0}
    """
    start_time = time.time()

    try:
        logger.info(f"Calculating size score for: {model_url}")

        # Fetch README content
        readme_text = fetch_readme(model_url)
        if not readme_text:
            logger.warning(f"No README content found for {model_url}")
            end_time = time.time()
            return {}, end_time - start_time

        # Extract memory sizes from README
        memory_sizes = extract_memory_sizes(readme_text)
        if not memory_sizes:
            logger.warning(f"No memory sizes found in README for {model_url}")
            end_time = time.time()
            return {}, end_time - start_time

        # Find smallest model size
        smallest_size = find_smallest_model_size(memory_sizes)
        if smallest_size is None:
            logger.warning(f"Could not determine model size for {model_url}")
            end_time = time.time()
            return {}, end_time - start_time

        # Calculate scores against all benchmarks
        size_scores = calculate_size_scores(smallest_size)

        end_time = time.time()
        latency = end_time - start_time

        logger.info(f"Size score calculation completed in {latency:.3f}s")
        return size_scores, latency

    except Exception as e:
        log_error_with_context(
            e, f"Error calculating size score for {model_url}", logger)
        end_time = time.time()
        return {}, end_time - start_time


# Test the function
if __name__ == "__main__":
    # Test with a sample model URL
    test_url = "https://huggingface.co/microsoft/DialoGPT-medium"
    scores, latency = size_score(test_url)

    print(f"Size scores: {scores}")
    print(f"Latency: {latency:.3f}s")

    # Test with sample README text
    sample_readme = """
    # Model Information

    This model requires approximately 7.2 GB of VRAM for inference.
    Minimum system requirements: 8 GB RAM, 2 GB VRAM.
    Recommended: 16 GB RAM, 8 GB VRAM for optimal performance.

    Model size: 7.2 GB
    """

    memory_sizes = extract_memory_sizes(sample_readme)
    print(f"Extracted sizes: {memory_sizes}")

    if memory_sizes:
        smallest = find_smallest_model_size(memory_sizes)
        if smallest is not None:
            scores = calculate_size_scores(smallest)
            print(f"Sample scores: {scores}")
