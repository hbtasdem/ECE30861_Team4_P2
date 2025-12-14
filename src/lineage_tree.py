#!/usr/bin/env python3

import hashlib
import json
import sys  # ← ADD THIS
import time
from typing import Any, Dict, List, Optional, Tuple, cast

import boto3
import requests
from fastapi import APIRouter, Header, HTTPException

# Create router
router = APIRouter()

# S3 configuration
S3_BUCKET = 'phase2-s3-bucket'
MODEL_PREFIX = 'model/'

# Cache for artifact_id -> model data
_artifact_cache: Dict[str, Dict[str, Any]] = {}


def build_artifact_cache() -> Dict[str, Dict[str, Any]]:
    """
    Build a cache of all artifacts from the models/ folder in S3.
    
    Returns:
        Dict mapping artifact_id -> full model data
    """
    global _artifact_cache
    
    # Return cached data if already built
    if _artifact_cache:
        return _artifact_cache
    
    print("Building artifact cache from S3 models/ folder...", file=sys.stderr)
    
    s3_client = boto3.client('s3')
    cache = {}
    
    try:
        # Use paginator to handle large result sets
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=MODEL_PREFIX)
        
        for page in pages:
            if 'Contents' not in page:
                continue
            
            for obj in page['Contents']:
                key = obj['Key']
                
                # Skip directories
                if key.endswith('/'):
                    continue
                
                try:
                    # Fetch model data
                    model_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
                    model_data = json.loads(model_obj['Body'].read().decode('utf-8'))
                    
                    # Extract artifact_id from metadata
                    metadata = model_data.get('metadata', {})
                    artifact_id = metadata.get('id')
                    
                    if artifact_id:
                        cache[artifact_id] = model_data
                
                except Exception as e:
                    print(f"Error processing {key}: {e}", file=sys.stderr)
                    continue
        
        print(f"Built cache with {len(cache)} artifacts", file=sys.stderr)
        _artifact_cache = cache
        return cache
    
    except Exception as e:
        print(f"Error building artifact cache: {e}", file=sys.stderr)
        return {}


def get_artifact_by_id(artifact_id: str) -> Optional[Dict[str, Any]]:
    """
    Look up artifact data by artifact_id.
    
    Args:
        artifact_id: Artifact ID (e.g., "01KCDBCVND2S5Y2SRBDK8H9078")
    
    Returns:
        Full artifact data if found, None otherwise
    """
    cache = build_artifact_cache()
    return cache.get(artifact_id)


def generate_artifact_id(name: str) -> str:
    """
    Generate a consistent artifact_id from a name using hash.
    This ensures the same name always gets the same ID.
    Returns STRING not int (per spec: artifact_id must be string).
    """
    # Use MD5 hash and convert to string (spec requires string IDs)
    hash_obj = hashlib.md5(name.encode())
    # Return as string of hex digits (matches spec pattern ^[a-zA-Z0-9\-]+$)
    return hash_obj.hexdigest()[:16]


def get_model_config(model_identifier: str) -> Optional[Dict[str, Any]]:
    """
    Return JSON metadata for a Hugging Face model via API.
    model_identifier can be either:
    - Full URL: https://huggingface.co/microsoft/DialoGPT-medium
    - Model path: microsoft/DialoGPT-medium
    """
    # Handle empty or invalid input
    if not model_identifier or not model_identifier.strip():
        print("Empty model identifier provided")
        return None
    
    # Clean up the model identifier
    if "huggingface.co/" in model_identifier:
        # Extract path from URL
        model_path = model_identifier.split("huggingface.co/")[1]
        model_path = model_path.split("/tree")[0].split("/blob")[0].strip("/")
    else:
        model_path = model_identifier.strip()
    
    # Validate model_path is not empty after cleaning
    if not model_path:
        print("Model path is empty after cleaning")
        return None

    api_url = f"https://huggingface.co/api/models/{model_path}"

    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Ensure we got a dict, not a list
        if not isinstance(data, dict):
            print(f"Unexpected response type: {type(data)}")
            return None
            
        return cast(Dict[str, Any], data)
    except Exception as e:
        print(f"Could not fetch HF API metadata for {model_path}: {e}")
        return None


def check_lineage(model_identifier: str) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Synchronous function to check if a model has lineage (parent models).
    Returns a tuple of (lineage_info, latency).

    This is a simplified version for use in scoring functions.
    """
    start_time = time.time()

    metadata = get_model_config(model_identifier)

    if not metadata:
        return None, time.time() - start_time

    # Extract parent models
    parent_models = []

    # Check tags
    tags = metadata.get("tags", [])
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("base_model:"):
                parent = tag.replace("base_model:", "")
                parent_models.append(parent)

    # Check cardData
    card_data = metadata.get("cardData", {})
    if isinstance(card_data, dict) and "base_model" in card_data:
        base = card_data["base_model"]
        if base and base not in parent_models:
            parent_models.append(base)

    # Check direct base_model field
    if "base_model" in metadata:
        base = metadata["base_model"]
        if base and base not in parent_models:
            parent_models.append(base)

    lineage_info = {
        "model": model_identifier,
        "base_model": parent_models[0] if parent_models else None,
        "has_lineage": len(parent_models) > 0,
        "lineage_depth": 1 if parent_models else 0,
        "all_parents": parent_models,
    }

    elapsed_time = time.time() - start_time
    return lineage_info, elapsed_time


def extract_lineage_graph(
    model_identifier: str, metadata: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract lineage and build graph structure with nodes and edges.

    Per spec: Returns ArtifactLineageGraph with:
    - nodes: List[ArtifactLineageNode]
    - edges: List[ArtifactLineageEdge]

    Returns:
        {
            "nodes": [...],
            "edges": [...]
        }
    """
    nodes = []
    edges = []

    if not isinstance(metadata, dict):
        return {"nodes": nodes, "edges": edges}

    # Get clean model name and ID
    model_id = metadata.get("id") or metadata.get("modelId") or model_identifier
    model_name = model_id.split("/")[-1] if "/" in model_id else model_id

    # Create the main model node (artifact_id must be STRING per spec)
    model_artifact_id = generate_artifact_id(model_id)
    nodes.append(
        {
            "artifact_id": model_artifact_id,  # STRING per spec
            "name": model_name,
            "source": "config_json",  # Per spec: how node was discovered
        }
    )

    # Extract parent models from tags
    tags = metadata.get("tags", [])
    parent_models = []
    datasets = []
    papers = []

    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str):
                if tag.startswith("base_model:"):
                    parent = tag.replace("base_model:", "")
                    parent_models.append(parent)
                elif tag.startswith("dataset:"):
                    dataset = tag.replace("dataset:", "")
                    datasets.append(dataset)
                elif tag.startswith("arxiv:"):
                    paper = tag.replace("arxiv:", "")
                    papers.append(paper)

    # Check cardData for additional info
    card_data = metadata.get("cardData", {})
    if isinstance(card_data, dict):
        # Base model from cardData
        if "base_model" in card_data:
            base = card_data["base_model"]
            if base and base not in parent_models:
                parent_models.append(base)

        # Datasets from cardData
        if "datasets" in card_data and isinstance(card_data["datasets"], list):
            for dataset in card_data["datasets"]:
                if dataset and dataset not in datasets:
                    datasets.append(dataset)

    # Direct base_model field
    if "base_model" in metadata:
        base = metadata["base_model"]
        if base and base not in parent_models:
            parent_models.append(base)

    # Add parent model nodes and edges
    for parent in parent_models:
        parent_artifact_id = generate_artifact_id(parent)
        parent_name = parent.split("/")[-1] if "/" in parent else parent

        nodes.append(
            {
                "artifact_id": parent_artifact_id,  # STRING
                "name": parent_name,
                "source": "base_model",
            }
        )

        # Per spec: Edge shows from_node -> to_node relationship
        edges.append(
            {
                "from_node_artifact_id": parent_artifact_id,
                "to_node_artifact_id": model_artifact_id,
                "relationship": "fine_tuned_from",
            }
        )

    # Add dataset nodes and edges
    for dataset in datasets:
        dataset_artifact_id = generate_artifact_id(dataset)

        nodes.append(
            {
                "artifact_id": dataset_artifact_id,  # STRING
                "name": dataset,
                "source": "upstream_dataset",  # Per spec example
            }
        )

        edges.append(
            {
                "from_node_artifact_id": dataset_artifact_id,
                "to_node_artifact_id": model_artifact_id,
                "relationship": "fine_tuning_dataset",  # Per spec example
            }
        )

    # Add paper nodes and edges (optional)
    for paper in papers:
        paper_artifact_id = generate_artifact_id(f"arxiv:{paper}")

        nodes.append(
            {
                "artifact_id": paper_artifact_id,  # STRING
                "name": f"arXiv:{paper}",
                "source": "research_paper",
            }
        )

        edges.append(
            {
                "from_node_artifact_id": paper_artifact_id,
                "to_node_artifact_id": model_artifact_id,
                "relationship": "implements",
            }
        )

    return {"nodes": nodes, "edges": edges}


@router.get("/artifact/model/{artifact_id}/lineage")
async def get_artifact_lineage(
    artifact_id: str, x_authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Retrieve the lineage graph for an artifact.

    Per OpenAPI v3.4.4 spec:
    - Returns lineage graph extracted from structured metadata
    - Returns 404 if artifact not found

    Args:
        artifact_id: Unique artifact identifier
        x_authorization: Bearer token for authentication

    Returns:
        ArtifactLineageGraph with nodes and edges

    Raises:
        HTTPException: 403 if auth fails, 404 if not found
    """
    # Validate authentication if provided
    if x_authorization:
        if not x_authorization.startswith("Bearer ") and not x_authorization.startswith(
            "bearer "
        ):
            raise HTTPException(
                status_code=403, detail="Invalid authorization header format"
            )

    # Look up artifact in the models/ folder
    artifact_data = get_artifact_by_id(artifact_id)
    
    if not artifact_data:
        raise HTTPException(
            status_code=404, 
            detail=f"Artifact {artifact_id} not found"
        )
    
    # Extract the model URL from the artifact data
    data_section = artifact_data.get('data', {})
    model_url = data_section.get('url', '')
    
    if not model_url:
        raise HTTPException(
            status_code=404,
            detail=f"No URL found for artifact {artifact_id}"
        )

    # Fetch metadata from HuggingFace using the model URL
    metadata = get_model_config(model_url)

    if not metadata:
        raise HTTPException(
            status_code=404, 
            detail=f"Could not fetch metadata for artifact {artifact_id}"
        )

    # Extract lineage graph
    graph = extract_lineage_graph(model_url, metadata)

    # Per spec: Return ArtifactLineageGraph (just nodes and edges, no wrapper)
    return {"nodes": graph["nodes"], "edges": graph["edges"]}


# For local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: lineage_tree.py <model_identifier_or_artifact_id>")
        print("Example: lineage_tree.py google-bert/bert-base-uncased")
        print("Example: lineage_tree.py 01KCDBCVND2S5Y2SRBDK8H9078")
        sys.exit(1)

    for model_id in sys.argv[1:]:
        # Try as artifact_id first
        if len(model_id) == 26 and model_id[0:2] == "01":  # Looks like ULID
            artifact = get_artifact_by_id(model_id)
            if artifact:
                print(f"\n{'='*60}")
                print(f"Found artifact: {model_id}")
                print(f"Name: {artifact['metadata']['name']}")
                print(f"URL: {artifact['data']['url']}")
                model_url = artifact['data']['url']
                
                metadata = get_model_config(model_url)
                if metadata:
                    graph = extract_lineage_graph(model_url, metadata)
                    print(json.dumps(graph, indent=2))
            else:
                print(f"Artifact not found: {model_id}")
        else:
            # Treat as model identifier
            lineage_info, latency = check_lineage(model_id)
            if lineage_info:
                print(f"\n{'='*60}")
                print(f"Lineage info for {model_id}:")
                print("=" * 60)
                print(json.dumps(lineage_info, indent=2))
                print(f"Latency: {latency:.3f}s")
            else:
                print(f"\nCould not fetch lineage for {model_id}")