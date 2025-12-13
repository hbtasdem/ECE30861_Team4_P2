#!/usr/bin/env python3
"""Tree score calculation based on parent model ratings from S3."""

import time
import boto3
import json
from typing import Tuple, Optional
import sys
import os

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from lineage_tree import check_lineage

# Initialize S3 client
s3_client = boto3.client('s3')
S3_BUCKET = 'phase2-s3-bucket'
RATING_PREFIX = 'rating/'


def get_model_rating_from_s3(model_name: str) -> Optional[dict]:
    """
    Fetch model rating JSON from S3.
    
    Args:
        model_name: Model name (e.g., "resnet-50", "bert-base-uncased")
    
    Returns:
        Rating dict if found, None otherwise
    """
    try:
        # Construct S3 key: rating/{model_name}.json
        s3_key = f"{RATING_PREFIX}{model_name}.json"
        
        print(f"Fetching rating from S3: {s3_key}", file=sys.stderr)
        
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        rating_data = json.loads(response['Body'].read().decode('utf-8'))
        
        return rating_data
    
    except s3_client.exceptions.NoSuchKey:
        print(f"No rating found in S3 for model: {model_name}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error fetching rating from S3 for {model_name}: {e}", file=sys.stderr)
        return None


def treescore_calc(model_name: str) -> Tuple[float, float]:
    """
    Calculate tree score based on parent model net scores from S3.
    
    Tree score = average of all parent models' net_scores
    If no parents, returns 0.0 (base model)
    
    Args:
        model_name: Model to calculate tree score for
    
    Returns:
        (tree_score, latency_in_seconds)
    """
    start_time = time.time()
    
    # Get lineage info from lineage_tree module
    parent_lineage, _ = check_lineage(model_name)
    
    if not parent_lineage or not parent_lineage.get("has_lineage"):
        # No parents = base model, tree_score is 0
        print(f"Model {model_name} has no parents, tree_score = 0.0", file=sys.stderr)
        return 0.0, time.time() - start_time
    
    # Get all parent model names
    parent_models = parent_lineage.get("all_parents", [])
    
    if not parent_models:
        return 0.0, time.time() - start_time
    
    total_score = 0.0
    num_parents_with_scores = 0
    
    # For each parent, fetch its rating from S3 and get net_score
    for parent_full_name in parent_models:
        # Extract just the model name (remove org prefix if present)
        # e.g., "google-bert/bert-base-uncased" -> "bert-base-uncased"
        parent_name = parent_full_name.split("/")[-1] if "/" in parent_full_name else parent_full_name
        
        print(f"Fetching rating for parent: {parent_name}", file=sys.stderr)
        
        # Fetch parent rating from S3
        parent_rating = get_model_rating_from_s3(parent_name)
        
        if parent_rating:
            parent_net_score = parent_rating.get("net_score", 0.0)
            total_score += float(parent_net_score)
            num_parents_with_scores += 1
            print(f"Parent {parent_name} net_score: {parent_net_score}", file=sys.stderr)
        else:
            print(f"Could not find rating for parent: {parent_name}", file=sys.stderr)
    
    # Calculate average
    if num_parents_with_scores > 0:
        tree_score = total_score / num_parents_with_scores
        print(f"Tree score calculation: {total_score} / {num_parents_with_scores} = {tree_score}", file=sys.stderr)
    else:
        tree_score = 0.0
        print(f"No parent scores found for {model_name}, tree_score = 0.0", file=sys.stderr)
    
    latency = time.time() - start_time
    return tree_score, latency


# For local testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: tree_score.py <model_name>")
        print("Example: tree_score.py parvk11/audience_classifier_model")
        sys.exit(1)
    
    for model_name in sys.argv[1:]:
        score, latency = treescore_calc(model_name)
        print(f"\nTree Score for {model_name}: {score}")
        print(f"Latency: {latency:.3f}s")