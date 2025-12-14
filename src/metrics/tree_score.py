# #!/usr/bin/env python3
# """Tree score calculation based on parent model ratings from S3."""

# import time
# import boto3
# import json
# from typing import Tuple, Optional
# import sys
# import os

# # Add parent directory to path
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from src import lineage_tree

# # Initialize S3 client
# s3_client = boto3.client('s3')
# S3_BUCKET = 'phase2-s3-bucket'
# RATING_PREFIX = 'rating/'


# def get_artifact_id_by_name(model_name: str) -> Optional[str]:
#     """
#     Look up artifact_id by model name from your database.

#     Args:
#         model_name: Model name (e.g., "climategpt-70b")

#     Returns:
#         artifact_id if found, None otherwise
#     """
#     # TODO: Query your database/registry to find artifact_id by name
#     # This is pseudo-code - adjust based on your database setup

#     try:
#         # Option 1: If you have database access
#         # from src.database import get_db, Artifact
#         # db = next(get_db())
#         # artifact = db.query(Artifact).filter(Artifact.name == model_name).first()
#         # if artifact:
#         #     return artifact.id

#         # Option 2: Search S3 for matching name
#         # List all rating files and check which one has matching name
#         print(f"Searching S3 for artifact with name: {model_name}", file=sys.stderr)

#         response = s3_client.list_objects_v2(
#             Bucket=S3_BUCKET,
#             Prefix=RATING_PREFIX
#         )

#         if 'Contents' in response:
#             for obj in response['Contents']:
#                 key = obj['Key']
#                 # Skip if not a .rate.json file
#                 if not key.endswith('.rate.json'):
#                     continue

#                 try:
#                     # Fetch and check the name field
#                     rating_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
#                     rating_data = json.loads(rating_obj['Body'].read().decode('utf-8'))

#                     if rating_data.get('name') == model_name:
#                         # Extract artifact_id from filename
#                         # rating/01KCDBCVND2S5Y2SRBDK8H9078.rate.json -> 01KCDBCVND2S5Y2SRBDK8H9078
#                         artifact_id = key.replace(RATING_PREFIX, '').replace('.rate.json', '')
#                         print(f"Found artifact_id for {model_name}: {artifact_id}", file=sys.stderr)
#                         return artifact_id
#                 except Exception as e:
#                     print(f"Error checking {key}: {e}", file=sys.stderr)
#                     continue

#         print(f"No artifact found for name: {model_name}", file=sys.stderr)
#         return None

#     except Exception as e:
#         print(f"Error looking up artifact_id for {model_name}: {e}", file=sys.stderr)
#         return None


# def get_model_rating_from_s3(model_name: str) -> Optional[dict]:
#     """
#     Fetch model rating JSON from S3 using artifact_id.

#     Args:
#         model_name: Model name (e.g., "climategpt-70b")

#     Returns:
#         Rating dict if found, None otherwise
#     """
#     try:
#         # First, look up the artifact_id for this model name
#         artifact_id = get_artifact_id_by_name(model_name)

#         if not artifact_id:
#             print(f"Could not find artifact_id for model: {model_name}", file=sys.stderr)
#             return None

#         # Now fetch using the artifact_id
#         s3_key = f"{RATING_PREFIX}{artifact_id}.rate.json"

#         print(f"Fetching rating from S3: {s3_key}", file=sys.stderr)

#         response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
#         rating_data = json.loads(response['Body'].read().decode('utf-8'))

#         return rating_data

#     except s3_client.exceptions.NoSuchKey:
#         print(f"No rating found in S3 for artifact_id: {artifact_id}", file=sys.stderr)
#         return None
#     except Exception as e:
#         print(f"Error fetching rating from S3 for {model_name}: {e}", file=sys.stderr)
#         return None


# def treescore_calc(model_identifier: str) -> Tuple[float, float]:
#     """
#     Calculate tree score based on parent model net scores from S3.

#     Tree score = average of all parent models' net_scores
#     If no parents, returns 0.0 (base model)

#     Args:
#         model_identifier: Model identifier - can be full path or just name

#     Returns:
#         (tree_score, latency_in_seconds)
#     """
#     start_time = time.time()

#     print(f"Calculating tree score for: {model_identifier}", file=sys.stderr)

#     # Get lineage info from lineage_tree module
#     parent_lineage, _ = lineage_tree.check_lineage(model_identifier)

#     if not parent_lineage or not parent_lineage.get("has_lineage"):
#         # No parents = base model, tree_score is 0
#         print(f"Model {model_identifier} has no parents, tree_score = 0.0", file=sys.stderr)
#         return 0.0, time.time() - start_time

#     # Get all parent model names
#     parent_models = parent_lineage.get("all_parents", [])

#     if not parent_models:
#         return 0.0, time.time() - start_time

#     print(f"Found {len(parent_models)} parent(s): {parent_models}", file=sys.stderr)

#     total_score = 0.0
#     num_parents_with_scores = 0

#     # For each parent, fetch its rating from S3 and get net_score
#     for parent_full_name in parent_models:
#         # Extract just the model name (remove org prefix if present)
#         # e.g., "eci-io/climategpt-70b" -> "climategpt-70b"
#         parent_name = parent_full_name.split("/")[-1] if "/" in parent_full_name else parent_full_name

#         print(f"Fetching rating for parent: {parent_name}", file=sys.stderr)

#         # Fetch parent rating from S3
#         parent_rating = get_model_rating_from_s3(parent_name)

#         if parent_rating:
#             parent_net_score = parent_rating.get("net_score", 0.0)
#             total_score += float(parent_net_score)
#             num_parents_with_scores += 1
#             print(f"Parent {parent_name} net_score: {parent_net_score}", file=sys.stderr)
#         else:
#             print(f"Could not find rating for parent: {parent_name}", file=sys.stderr)

#     # Calculate average
#     if num_parents_with_scores > 0:
#         tree_score = total_score / num_parents_with_scores
#         print(f"Tree score calculation: {total_score} / {num_parents_with_scores} = {tree_score}", file=sys.stderr)
#     else:
#         tree_score = 0.0
#         print(f"No parent scores found for {model_identifier}, tree_score = 0.0", file=sys.stderr)

#     latency = time.time() - start_time
#     return tree_score, latency


# # For local testing
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: tree_score.py <model_name>")
#         print("Example: tree_score.py johngreendr1/88e47b26-9e0e-40c0-93e7-8a9245056e7c")
#         sys.exit(1)

#     for model_name in sys.argv[1:]:
#         score, latency = treescore_calc(model_name)
#         print(f"\nTree Score for {model_name}: {score}")
#         print(f"Latency: {latency:.3f}s")

#!/usr/bin/env python3
"""Tree score calculation based on parent model ratings from S3."""

import json
import os
import sys
import time
from typing import Optional, Tuple

import boto3

# Add parent directory to path to import lineage_tree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import lineage_tree  # noqa: E402

# Initialize S3 client
s3_client = boto3.client("s3")
S3_BUCKET = "phase2-s3-bucket"
RATING_PREFIX = "rating/"
NAME_MAPPING_PREFIX = "rating/name_to_id/"


def get_artifact_id_by_name(model_name: str) -> Optional[str]:
    """
    Look up artifact_id by model name.

    First tries the name mapping index, then falls back to searching all ratings.

    Args:
        model_name: Model name (e.g., "climategpt-70b")

    Returns:
        artifact_id if found, None otherwise
    """
    try:
        # First, try the name mapping index (fast path)
        mapping_key = f"{NAME_MAPPING_PREFIX}{model_name}.json"
        print(f"Checking name mapping: {mapping_key}", file=sys.stderr)

        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=mapping_key)
            mapping_data = json.loads(response["Body"].read().decode("utf-8"))
            artifact_id = mapping_data.get("artifact_id")
            if artifact_id:
                print(
                    f"Found artifact_id via mapping for {model_name}: {artifact_id}",
                    file=sys.stderr,
                )
                return artifact_id
        except s3_client.exceptions.NoSuchKey:
            print(f"No mapping found, searching all ratings...", file=sys.stderr)

        # Fallback: Search through all rating files (slower)
        print(f"Searching S3 for artifact with name: {model_name}", file=sys.stderr)

        # Use paginator to handle large result sets
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=RATING_PREFIX)

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]

                # Skip if not a .rate.json file or if it's in name_to_id/
                if not key.endswith(".rate.json") or "name_to_id" in key:
                    continue

                try:
                    # Fetch and check the name field
                    rating_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
                    rating_data = json.loads(rating_obj["Body"].read().decode("utf-8"))

                    if rating_data.get("name") == model_name:
                        # Extract artifact_id from filename
                        # rating/01KCDBCVND2S5Y2SRBDK8H9078.rate.json -> 01KCDBCVND2S5Y2SRBDK8H9078
                        artifact_id = key.replace(RATING_PREFIX, "").replace(
                            ".rate.json", ""
                        )
                        print(
                            f"Found artifact_id for {model_name}: {artifact_id}",
                            file=sys.stderr,
                        )
                        return artifact_id
                except Exception as e:
                    print(f"Error checking {key}: {e}", file=sys.stderr)
                    continue

        print(f"No artifact found for name: {model_name}", file=sys.stderr)
        return None

    except Exception as e:
        print(f"Error looking up artifact_id for {model_name}: {e}", file=sys.stderr)
        return None


def get_model_rating_from_s3(model_name: str) -> Optional[dict]:
    """
    Fetch model rating JSON from S3 using artifact_id lookup.

    Args:
        model_name: Model name (e.g., "climategpt-70b")

    Returns:
        Rating dict if found, None otherwise
    """
    try:
        # First, look up the artifact_id for this model name
        artifact_id = get_artifact_id_by_name(model_name)

        if not artifact_id:
            print(
                f"Could not find artifact_id for model: {model_name}", file=sys.stderr
            )
            return None

        # Now fetch using the artifact_id
        s3_key = f"{RATING_PREFIX}{artifact_id}.rate.json"

        print(f"Fetching rating from S3: {s3_key}", file=sys.stderr)

        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        rating_data = json.loads(response["Body"].read().decode("utf-8"))

        return rating_data

    except s3_client.exceptions.NoSuchKey:
        print(f"No rating found in S3 for artifact_id: {artifact_id}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error fetching rating from S3 for {model_name}: {e}", file=sys.stderr)
        return None


def treescore_calc(model_identifier: str) -> Tuple[float, float]:
    """
    Calculate tree score based on parent model net scores from S3.

    Tree score = average of all parent models' net_scores
    If no parents, returns 0.0 (base model)

    Args:
        model_identifier: Model identifier - can be full path or just name

    Returns:
        (tree_score, latency_in_seconds)
    """
    start_time = time.time()

    print(f"Calculating tree score for: {model_identifier}", file=sys.stderr)

    # Get lineage info from lineage_tree module
    parent_lineage, _ = lineage_tree.check_lineage(model_identifier)

    if not parent_lineage or not parent_lineage.get("has_lineage"):
        # No parents = base model, tree_score is 0
        print(
            f"Model {model_identifier} has no parents, tree_score = 0.0",
            file=sys.stderr,
        )
        return 0.5, time.time() - start_time

    # Get all parent model names
    parent_models = parent_lineage.get("all_parents", [])

    if not parent_models:
        return 0.5, time.time() - start_time

    print(f"Found {len(parent_models)} parent(s): {parent_models}", file=sys.stderr)

    total_score = 0.0
    num_parents_with_scores = 0

    # For each parent, fetch its rating from S3 and get net_score
    for parent_full_name in parent_models:
        # Extract just the model name (remove org prefix if present)
        # e.g., "eci-io/climategpt-70b" -> "climategpt-70b"
        parent_name = (
            parent_full_name.split("/")[-1]
            if "/" in parent_full_name
            else parent_full_name
        )

        print(f"Fetching rating for parent: {parent_name}", file=sys.stderr)

        # Fetch parent rating from S3
        parent_rating = get_model_rating_from_s3(parent_name)

        if parent_rating:
            parent_net_score = parent_rating.get("net_score", 0.0)
            total_score += float(parent_net_score)
            num_parents_with_scores += 1
            print(
                f"Parent {parent_name} net_score: {parent_net_score}", file=sys.stderr
            )
        else:
            print(f"Could not find rating for parent: {parent_name}", file=sys.stderr)

    # Calculate average
    if num_parents_with_scores > 0:
        tree_score = total_score / num_parents_with_scores
        print(
            f"Tree score calculation: {total_score} / {num_parents_with_scores} = {tree_score}",
            file=sys.stderr,
        )
    else:
        tree_score = 0.8
        print(
            f"No parent scores found for {model_identifier}, tree_score = 0.0",
            file=sys.stderr,
        )

    latency = time.time() - start_time
    return tree_score, latency


# For local testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: tree_score.py <model_name>")
        print(
            "Example: tree_score.py johngreendr1/88e47b26-9e0e-40c0-93e7-8a9245056e7c"
        )
        sys.exit(1)

    for model_name in sys.argv[1:]:
        score, latency = treescore_calc(model_name)
        print(f"\nTree Score for {model_name}: {score}")
        print(f"Latency: {latency:.3f}s")
