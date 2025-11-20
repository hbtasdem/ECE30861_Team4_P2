#!/usr/bin/env python3

import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple, cast

import requests
from fastapi import APIRouter, HTTPException

# Create router
router = APIRouter()


def generate_artifact_id(name: str) -> int:
    """
    Generate a consistent artifact_id from a name using hash.
    This ensures the same name always gets the same ID.
    """
    # Use MD5 hash and convert first 8 bytes to int
    hash_obj = hashlib.md5(name.encode())
    hash_int = int(hash_obj.hexdigest()[:10], 16)
    return hash_int


def get_model_config(model_identifier: str) -> Dict[str, Any] | None:
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


def extract_lineage_graph(
    model_identifier: str, 
    metadata: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract lineage and build graph structure with nodes and edges.
    
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
    
    # Get clean model name
    model_id = metadata.get("id") or metadata.get("modelId") or model_identifier
    model_name = model_id.split("/")[-1] if "/" in model_id else model_id
    
    # Create the main model node
    model_artifact_id = generate_artifact_id(model_id)
    nodes.append({
        "artifact_id": model_artifact_id,
        "name": model_name,
        "source": "huggingface_model"
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
    
    # Check cardData for additional datasets
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
            "artifact_id": parent_artifact_id,
            "name": parent_name,
            "source": "base_model"
        })
        
        edges.append({
            "from_node_artifact_id": parent_artifact_id,
            "to_node_artifact_id": model_artifact_id,
            "relationship": "fine_tuned_from"
        })
    
    # Add dataset nodes and edges
    for dataset in datasets:
        dataset_artifact_id = generate_artifact_id(dataset)
        
        nodes.append({
            "artifact_id": dataset_artifact_id,
            "name": dataset,
            "source": "training_dataset"
        })
        
        edges.append({
            "from_node_artifact_id": dataset_artifact_id,
            "to_node_artifact_id": model_artifact_id,
            "relationship": "trained_on"
        })
    
    # Add paper nodes and edges
    for paper in papers:
        paper_artifact_id = generate_artifact_id(f"arxiv:{paper}")
        
        nodes.append({
            "artifact_id": paper_artifact_id,
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


@router.get("/artifact/model/{model_identifier:path}/lineage")
async def get_model_lineage(model_identifier: str) -> Dict[str, Any]:
    """
    Get lineage information for a HuggingFace model in graph format.
    
    Args:
        model_identifier: Either a full URL or model path (e.g., "google-bert/bert-base-uncased")
    
    Returns:
        JSON response with graph structure:
        {
            "nodes": [
                {
                    "artifact_id": 3847247294,
                    "name": "model-name",
                    "source": "huggingface_model"
                },
                ...
            ],
            "edges": [
                {
                    "from_node_artifact_id": 5738291045,
                    "to_node_artifact_id": 3847247294,
                    "relationship": "trained_on"
                },
                ...
            ],
            "metadata": {
                "model_id": "...",
                "downloads": 123,
                "latency": 0.234
            }
        }
    """
    start_time = time.time()

    # Fetch metadata
    metadata = get_model_config(model_identifier)

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch metadata for model: {model_identifier}"
        )

    # Extract lineage graph
    graph = extract_lineage_graph(model_identifier, metadata)

    # Add metadata
    model_id = metadata.get("id") or metadata.get("modelId") or model_identifier
    
    response = {
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "metadata": {
            "model_id": model_id,
            "downloads": metadata.get("downloads", 0),
            "likes": metadata.get("likes", 0),
            "created_at": metadata.get("createdAt"),
            "last_modified": metadata.get("lastModified"),
            "latency": round(time.time() - start_time, 3)
        }
    }

    return response


@router.get("/artifact/models/lineage-batch")
async def get_batch_lineage(model_identifiers: str) -> Dict[str, Any]:
    """
    Get lineage information for multiple models and merge into a single graph.
    
    Args:
        model_identifiers: Comma-separated list of model identifiers
    
    Returns:
        Combined graph with all models and their relationships
    """
    start_time = time.time()
    
    # Split and clean model identifiers
    models = [m.strip() for m in model_identifiers.split(",") if m.strip()]
    
    all_nodes = []
    all_edges = []
    seen_artifact_ids = set()
    errors = []
    
    for model_id in models:
        try:
            metadata = get_model_config(model_id)
            if metadata:
                graph = extract_lineage_graph(model_id, metadata)
                
                # Add nodes (avoid duplicates)
                for node in graph["nodes"]:
                    if node["artifact_id"] not in seen_artifact_ids:
                        all_nodes.append(node)
                        seen_artifact_ids.add(node["artifact_id"])
                
                # Add edges
                all_edges.extend(graph["edges"])
            else:
                errors.append(f"Could not fetch metadata for {model_id}")
        except Exception as e:
            errors.append(f"Error processing {model_id}: {str(e)}")
    
    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "metadata": {
            "total_models": len(models),
            "successful": len(models) - len(errors),
            "errors": errors,
            "latency": round(time.time() - start_time, 3)
        }
    }


# For local testing
if __name__ == "__main__":
    import sys
    import asyncio

    async def test_endpoint():
        if len(sys.argv) < 2:
            print("Usage: lineage_tree.py <model_identifier>")
            print("Example: lineage_tree.py google-bert/bert-base-uncased")
            print("Example: lineage_tree.py parvk11/audience_classifier_model")
            sys.exit(1)

        for model_id in sys.argv[1:]:
            try:
                result = await get_model_lineage(model_id)
                print(f"\n{'='*60}")
                print(f"Lineage Graph for {model_id}:")
                print('='*60)
                print(json.dumps(result, indent=2))
            except HTTPException as e:
                print(f"\nError: {e.detail}")

    asyncio.run(test_endpoint())