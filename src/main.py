#!/usr/bin/env python3
"""Batch model scoring tool - processes CSV input and outputs JSON results."""

import csv
import json
import os
import sys
import time
from io import StringIO
from typing import Any, Dict

# import src.net_score_calculator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "metrics"))

# Import scoring modules
import available_dataset_code_score  # noqa: E402
import bus_factor_score as bus_factor_score  # noqa: E402
import code_quality_score as code_quality_score  # noqa: E402
import dataset_quality_score as dataset_quality_score  # noqa: E402
import license_score as license_score  # noqa: E402
import performance_claims_score as performance_claims_score  # noqa: E402
import ramp_up_time_score as ramp_up_time_score  # noqa: E402
import reviewedness_score  # noqa: E402
import size_score  # noqa: E402
import tree_score as tree_score  # noqa: E402


def extract_model_name(model_url: str) -> str:
    """Extract model name from Hugging Face URL."""
    if not model_url or model_url.strip() == "":
        return "unknown"
    # Handle different URL formats
    if "huggingface.co/" in model_url:
        # For URLs like https://huggingface.co/microsoft/DialoGPT-medium
        # Extract everything after huggingface.co/
        parts = model_url.split("huggingface.co/")
        if len(parts) > 1:
            model_path = parts[1]
            # Remove any additional path components like /tree/main
            if "/tree/" in model_path:
                model_path = model_path.split("/tree/")[0]
            elif "/blob/" in model_path:
                model_path = model_path.split("/blob/")[0]
            # Extract just the model name (last part after /)
            return model_path.split("/")[-1] if "/" in model_path else model_path
    elif "/" in model_url:
        # For direct model IDs like microsoft/DialoGPT-medium
        parts = model_url.split("/")
        if len(parts) >= 2:
            # Return just the model name (last part)
            return parts[-1]

    return model_url.strip()


def calculate_all_scores(
    code_link: str,
    dataset_link: str,
    model_link: str,
    encountered_datasets: set[str],
    encountered_code: set[str],
) -> Dict[str, Any]:
    """Calculate all scores for a given set of links."""
    model_name = extract_model_name(model_link)
    # Extract just the model name (without organization) for JSON display
    display_name = model_name.split("/")[-1] if "/" in model_name else model_name
    # Initialize result with model info
    result = {
        "name": display_name,
        "category": "MODEL",
        "net_score": 0.0,
        "net_score_latency": 0,
        "ramp_up_time": 0.0,
        "ramp_up_time_latency": 0,
        "bus_factor": 0.0,
        "bus_factor_latency": 0,
        "performance_claims": 0.0,
        "performance_claims_latency": 0,
        "license": 0.0,
        "license_latency": 0,
        "dataset_and_code_score": 0.0,
        "dataset_and_code_score_latency": 0,
        "dataset_quality": 0.0,
        "dataset_quality_latency": 0,
        "code_quality": 0.0,
        "code_quality_latency": 0,
        "reproducibility": 0.0,
        "reproducibility_latency": 0,
        "reviewedness": 0.0,
        "reviewedness_latency": 0,
        "tree_score": 0.0,
        "tree_score_latency": 0.0,
        "size_score": {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.0,
            "desktop_pc": 0.0,
            "aws_server": 0.0,
        },
        "size_score_latency": 0,
    }
    # Calculate each score with timing
    start_net_time = time.time()
    # Ramp Up Time
    try:
        ramp_score, ramp_latency = ramp_up_time_score.ramp_up_time_score(model_name)
        result["ramp_up_time"] = ramp_score
        result["ramp_up_time_latency"] = int(ramp_latency * 1000)
    except Exception as e:
        print(f"Error calculating ramp up score for {model_name}: {e}", file=sys.stderr)
    # Bus Factor
    try:
        bus_score_raw, bus_latency = bus_factor_score.bus_factor_score(model_name)
        # Normalize bus factor: cap at 20 contributors, then scale to 0-1
        bus_score_normalized = min(bus_score_raw / 20.0, 1.0)
        result["bus_factor"] = max(bus_score_normalized, 0.5)
        result["bus_factor_latency"] = int(bus_latency * 1000)
    except Exception as e:
        error_msg = f"Error calculating bus factor for {model_name}: {e}"
        print(error_msg, file=sys.stderr)
    # Performance Claims Score
    try:
        perf_score, perf_latency = (
            performance_claims_score.performance_claims_sub_score(model_name)
        )
        result["performance_claims"] = perf_score
        result["performance_claims_latency"] = int(perf_latency * 1000)
    except Exception as e:
        error_msg = f"Error calculating performance claims for {model_name}: {e}"
        print(error_msg, file=sys.stderr)
    # License Score
    try:
        lic_score, license_latency = license_score.license_sub_score(model_name)
        result["license"] = lic_score
        result["license_latency"] = int(license_latency * 1000)
    except Exception as e:
        error_msg = f"Error calculating license score for {model_name}: {e}"
        print(error_msg, file=sys.stderr)
    # Size Scores
    try:
        size_scores, net_size_score, size_score_latency = size_score.size_score(
            model_link
        )
        size_scores, net_size_score, size_score_latency = size_score.size_score(
            model_link
        )
        result["size_score"] = size_scores
        result["size_score_latency"] = size_score_latency
    except Exception as e:
        print(f"Error calculating size scores for {model_name}: {e}", file=sys.stderr)
    # Available Dataset Code Score
    try:
        data_code_score, code_latency = (
            available_dataset_code_score.available_dataset_code_score(
                model_name,
                code_link,
                dataset_link,
                encountered_datasets,
                encountered_code,
            )
        )
        result["dataset_and_code_score"] = data_code_score
        result["dataset_and_code_score_latency"] = int(code_latency * 1000)
    except Exception as e:
        print(f"Error calculating code quality for {model_name}: {e}", file=sys.stderr)
    # Dataset Quality Score
    try:
        dataset_score, dataset_latency = (
            dataset_quality_score.dataset_quality_sub_score(
                model_name, dataset_link, encountered_datasets
            )
        )
        result["dataset_quality"] = dataset_score
        result["dataset_quality_latency"] = int(dataset_latency * 1000)
    except Exception as e:
        print(
            f"Error calculating dataset quality for {model_name}: {e}", file=sys.stderr
        )
        print(
            f"Error calculating dataset quality for {model_name}: {e}", file=sys.stderr
        )
    # Code Quality
    try:
        code_q_score, code_q_latency = code_quality_score.code_quality_score(
            model_name
        )  # noqa: F823
        code_q_score, code_q_latency = code_quality_score.code_quality_score(
            model_name
        )  # noqa: F823
        result["code_quality"] = code_q_score
        result["code_quality_latency"] = int(code_q_latency * 1000)
    except Exception as e:
        print(f"Error calculating code quality for {model_name}: {e}", file=sys.stderr)

    # Reviewedness
    try:
        reviewedness, reviewedness_latency = reviewedness_score.reviewedness_score(
            code_link
        )
        reviewedness, reviewedness_latency = reviewedness_score.reviewedness_score(
            code_link
        )
        result["reviewedness"] = reviewedness
        result["reviewedness_latency"] = int(reviewedness_latency)
    except Exception as e:
        print(f"Error calculating treescore for {model_name}: {e}", file=sys.stderr)
    # Tree_score
    try:
        treescore_val, treescore_latency = tree_score.treescore_calc(model_link)
        result["tree_score"] = treescore_val
        result["tree_score_latency"] = int(treescore_latency * 1000)
    except Exception as e:
        print(f"Error calculating tree_score for {model_name}: {e}", file=sys.stderr)

    # Net Score (calculated from all other scores)
    # latency sucks, ignoring their net_score_calculator and just doing weighted average
    try:
        net_score = (
            net_size_score
            + lic_score
            + ramp_score
            + bus_score_normalized
            + data_code_score
            + dataset_score
            + code_q_score
            + perf_score
        ) / 8
        net_score = round(net_score, 2)
        result["net_score"] = float(net_score)
        total_latency = int((time.time() - start_net_time) * 1000)
        result["net_score_latency"] = total_latency
    except Exception as e:
        print(f"Error calculating net score for {model_name}: {e}", file=sys.stderr)
    return result


def main() -> int:
    """Process CSV input with code, dataset, and model links."""
    if len(sys.argv) != 2:
        print("Usage: model_scorer <input_file>")
        print("Input format: CSV with code_link,dataset_link,model_link")
        print("Example: model_scorer input.csv")
        return 1
    input_file = sys.argv[1]

    # Track encountered datasets and code across all models
    encountered_datasets: set[str] = set()
    encountered_code: set[str] = set()

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        # Parse CSV content
        csv_reader = csv.reader(StringIO(content))
        for row in csv_reader:
            if not row:
                continue
            # Handle rows with fewer than 3 columns by padding with empty
            # strings
            while len(row) < 3:
                row.append("")
            code_link = row[0].strip() if row[0] else ""
            dataset_link = row[1].strip() if row[1] else ""
            model_link = row[2].strip() if row[2] else ""
            # Skip rows where all fields are empty
            if not any([code_link, dataset_link, model_link]):
                continue
            # Only process rows that have a model link
            if model_link:
                # Suppress debug prints by redirecting stdout temporarily
                import contextlib
                import io

                # Capture stdout to suppress debug prints
                stdout_capture = io.StringIO()
                with contextlib.redirect_stdout(stdout_capture):
                    # Calculate scores
                    result = calculate_all_scores(
                        code_link,
                        dataset_link,
                        model_link,
                        encountered_datasets,
                        encountered_code,
                    )
                # Output clean JSON result (no extra whitespace)
                print(json.dumps(result, separators=(",", ":")))
        # If we get here, all URLs were processed successfully
        return 0
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error processing input: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
