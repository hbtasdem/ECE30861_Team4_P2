"""
NetScore Calculator

Combines all scoring functions using the weighted equation:
NetScore = 0.05⋅Size + 0.2⋅License + 0.2⋅RampUpTime + 0.05⋅BusFactor +
           0.15⋅Dataset&Code + 0.15⋅DatasetQuality + 0.1⋅CodeQuality +
           0.1⋅PerformanceClaims

Note: Only uses existing implemented scoring functions.
Missing functions (Size, CodeQuality) are set to 0.5 as defaults.
"""


import os
import sys
import time
from typing import Dict, Literal, TypedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "metrics"))

from available_dataset_code_score import available_dataset_code_score  # noqa: E402
from bus_factor_score import bus_factor_score  # noqa: E402
from dataset_quality_score import dataset_quality_sub_score  # noqa: E402
from license_score import license_sub_score  # noqa: E402
from performance_claims_score import performance_claims_sub_score  # noqa: E402
from ramp_up_time_score import ramp_up_time_score  # noqa: E402
from size_score import size_score  # noqa: E402


class ProjectMetadata(TypedDict):
    name: str
    category: Literal["MODEL", "DATASET", "CODE"]

    net_score: float
    net_score_latency: int

    ramp_up_time: float
    ramp_up_time_latency: int

    bus_factor: float
    bus_factor_latency: int

    performance_claims: float
    performance_claims_latency: int

    license: float
    license_latency: int

    size_score: Dict[str, float]  # {"raspberry_pi": 0.8, ... }
    size_score_latency: int

    dataset_and_code_score: float
    dataset_and_code_score_latency: int

    dataset_quality: float
    dataset_quality_latency: int

    code_quality: float
    code_quality_latency: int


def calculate_net_score(model_id: str) -> ProjectMetadata:
    """
    Calculate the overall NetScore for a model using all available metrics.

    Args:
        model_id: Hugging Face model ID (e.g., "microsoft/DialoGPT-medium")

    Returns:
        ProjectMetadata object containing all scores and NetScore
    """
    start_time = time.time()

    # Calculate individual scores
    print(f"Calculating scores for model: {model_id}")

    # Size Score (0.05 weight) - Now using actual implementation
    size_scores_dict, net_size_score, size_latency = size_score(model_id)
    print(f"Size Score: {net_size_score:.3f} " f"(latency: {size_latency}ms)")

    # License Score (0.2 weight)
    license_score, license_latency = license_sub_score(model_id)
    print(f"License Score: {license_score:.3f} " f"(latency: {license_latency:.3f}s)")

    # Ramp Up Time Score (0.2 weight)
    ramp_up_score, ramp_up_latency = ramp_up_time_score(model_id)
    print(f"Ramp Up Score: {ramp_up_score:.3f} " f"(latency: {ramp_up_latency:.3f}s)")

    # Bus Factor Score (0.05 weight) - normalize to 0-1 range
    bus_factor_raw, bus_factor_latency = bus_factor_score(model_id)
    # Normalize bus factor: cap at 20 contributors, then scale to 0-1
    bus_factor = min(bus_factor_raw / 20.0, 1.0)
    print(
        f"Bus Factor: {bus_factor:.3f} (raw: {bus_factor_raw}) "
        f"(latency: {bus_factor_latency:.3f}s)"
    )

    # Dataset & Code Score (0.15 weight)
    dataset_code_score, dataset_code_latency = available_dataset_code_score(model_id)
    print(
        f"Dataset & Code Score: {dataset_code_score:.3f} "
        f"(latency: {dataset_code_latency:.3f}s)"
    )

    # Dataset Quality Score (0.15 weight)
    dataset_quality, dataset_quality_latency = dataset_quality_sub_score(model_id)
    print(
        f"Dataset Quality Score: {dataset_quality:.3f} "
        f"(latency: {dataset_quality_latency:.3f}s)"
    )

    # Code Quality Score (0.1 weight) - Not implemented, using default
    code_quality = 0.5  # Default value since no code quality scoring function
    code_quality_latency = 0
    print(f"Code Quality Score: {code_quality:.3f} " f"(default - not implemented)")

    # Performance Claims Score (0.1 weight)
    performance_claims, performance_claims_latency = performance_claims_sub_score(
        model_id
    )
    print(
        f"Performance Claims Score: {performance_claims:.3f} "
        f"(latency: {performance_claims_latency:.3f}s)"
    )

    # Calculate weighted NetScore
    net_score = (
        0.05 * net_size_score
        + 0.2 * license_score
        + 0.2 * ramp_up_score
        + 0.05 * bus_factor
        + 0.15 * dataset_code_score
        + 0.15 * dataset_quality
        + 0.1 * code_quality
        + 0.1 * performance_claims
    )
    net_score = round(net_score, 2)

    total_latency = int((time.time() - start_time) * 1000)

    print(f"\nNetScore: {net_score:.3f}")
    print(f"Total calculation time: {total_latency}ms")

    # Return ProjectMetadata object
    return ProjectMetadata(
        name=model_id,
        category="MODEL",
        net_score=net_score,
        net_score_latency=total_latency,
        ramp_up_time=ramp_up_score,
        ramp_up_time_latency=int(ramp_up_latency * 1000),
        bus_factor=bus_factor,
        bus_factor_latency=int(bus_factor_latency * 1000),
        performance_claims=performance_claims,
        performance_claims_latency=int(performance_claims_latency * 1000),
        license=license_score,
        license_latency=int(license_latency * 1000),
        size_score=size_scores_dict,
        size_score_latency=size_latency,
        dataset_and_code_score=dataset_code_score,
        dataset_and_code_score_latency=int(dataset_code_latency * 1000),
        dataset_quality=dataset_quality,
        dataset_quality_latency=int(dataset_quality_latency * 1000),
        code_quality=code_quality,
        code_quality_latency=code_quality_latency,
    )


def print_score_summary(results: ProjectMetadata) -> None:
    """Print a formatted summary of the scoring results."""
    print("\n" + "=" * 60)
    print("NETSCORE CALCULATION SUMMARY")
    print("=" * 60)
    print(f"Model: {results['name']}")
    print(f"NetScore: {results['net_score']:.3f}")
    print(f"Total Time: {results['net_score_latency']}ms")
    print("\nIndividual Scores:")

    # Handle size_score as a dictionary of device scores
    size_score_dict = results["size_score"]
    if isinstance(size_score_dict, dict) and size_score_dict:
        # Calculate average or use weighted score
        avg_size_score = (
            sum(size_score_dict.values()) / len(size_score_dict)
            if size_score_dict
            else 0.0
        )
        print(f"  Size (avg): {avg_size_score:.3f}")
        for device, score in size_score_dict.items():
            print(f"    - {device}: {score:.3f}")
    else:
        print(f"  Size: {size_score_dict}")

    print(f"  License: {results['license']:.3f}")
    print(f"  Ramp Up Time: {results['ramp_up_time']:.3f}")
    print(f"  Bus Factor: {results['bus_factor']:.3f}")
    print(f"  Dataset & Code: {results['dataset_and_code_score']:.3f}")
    print(f"  Dataset Quality: {results['dataset_quality']:.3f}")
    print(f"  Code Quality: {results['code_quality']:.3f}")
    print(f"  Performance Claims: {results['performance_claims']:.3f}")
    print("=" * 60)


if __name__ == "__main__":
    # Example usage
    test_model = "microsoft/DialoGPT-medium"
    results = calculate_net_score(test_model)
    print_score_summary(results)
