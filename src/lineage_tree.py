#!/usr/bin/env python3

import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple, cast

import requests
from fastapi import APIRouter, HTTPException, Header

# Create router
router = APIRouter()


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
        "all_parents": parent_models
    }
    
    elapsed_time = time.time() - start_time
    return lineage_info, elapsed_time


def extract_lineage_graph(
    model_identifier: str, 
    metadata: Dict[str, Any]
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
    nodes.append({
        "artifact_id": model_artifact_id,  # STRING per spec
        "name": model_name,
        "source": "config_json"  # Per spec: how node was discovered
    })
    
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
        
        nodes.append({
            "artifact_id": parent_artifact_id,  # STRING
            "name": parent_name,
            "source": "base_model"
        })
        
        # Per spec: Edge shows from_node -> to_node relationship
        edges.append({
            "from_node_artifact_id": parent_artifact_id,
            "to_node_artifact_id": model_artifact_id,
            "relationship": "fine_tuned_from"
        })
    
    # Add dataset nodes and edges
    for dataset in datasets:
        dataset_artifact_id = generate_artifact_id(dataset)
        
        nodes.append({
            "artifact_id": dataset_artifact_id,  # STRING
            "name": dataset,
            "source": "upstream_dataset"  # Per spec example
        })
        
        edges.append({
            "from_node_artifact_id": dataset_artifact_id,
            "to_node_artifact_id": model_artifact_id,
            "relationship": "fine_tuning_dataset"  # Per spec example
        })
    
    # Add paper nodes and edges (optional)
    for paper in papers:
        paper_artifact_id = generate_artifact_id(f"arxiv:{paper}")
        
        nodes.append({
            "artifact_id": paper_artifact_id,  # STRING
            "name": f"arXiv:{paper}",
            "source": "research_paper"
        })
        
        edges.append({
            "from_node_artifact_id": paper_artifact_id,
            "to_node_artifact_id": model_artifact_id,
            "relationship": "implements"
        })
    
    return {
        "nodes": nodes,
        "edges": edges
    }


@router.get("/artifact/model/{artifact_id}/lineage")
async def get_artifact_lineage(
    artifact_id: str,
    x_authorization: Optional[str] = Header(None)
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
        if not x_authorization.startswith("Bearer ") and not x_authorization.startswith("bearer "):
            raise HTTPException(status_code=403, detail="Invalid authorization header format")
    
    # TODO: Look up artifact in YOUR database
    # For now, treat artifact_id as HuggingFace model identifier
    # In production, you should:
    # 1. Query your artifact database by artifact_id
    # 2. Get the model URL from the artifact record
    # 3. Then fetch metadata from HuggingFace
    
    model_identifier = artifact_id
    
    # Fetch metadata from HuggingFace
    metadata = get_model_config(model_identifier)
    
    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {artifact_id} not found"
        )
    
    # Extract lineage graph
    graph = extract_lineage_graph(model_identifier, metadata)
    
    # Per spec: Return ArtifactLineageGraph (just nodes and edges, no wrapper)
    return {
        "nodes": graph["nodes"],
        "edges": graph["edges"]
    }


# For local testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: lineage_tree.py <model_identifier>")
        print("Example: lineage_tree.py google-bert/bert-base-uncased")
        print("Example: lineage_tree.py parvk11/audience_classifier_model")
        print("Example: lineage_tree.py eci-io/climategpt-70b")
        
        sys.exit(1)

    for model_id in sys.argv[1:]:
        lineage_info, latency = check_lineage(model_id)
        if lineage_info:
            print(f"\n{'='*60}")
            print(f"Lineage info for {model_id}:")
            print('='*60)
            print(json.dumps(lineage_info, indent=2))
            print(f"Latency: {latency:.3f}s")
        else:
            print(f"\nCould not fetch lineage for {model_id}")