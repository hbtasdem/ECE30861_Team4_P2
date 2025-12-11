# /artifact/model/{artifact_id}/rate

import json
import re
from typing import Any, Optional, Tuple

import boto3
import requests
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

# from src.crud.upload.auth import get_current_user
from src.main import calculate_all_scores
from src.purdue_api import PurdueGenAI

router = APIRouter()

BUCKET_NAME = "phase2-s3-bucket"


# -----------ModelRating schema-----------
class rating_sizescore(BaseModel):  # type: ignore[misc]
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float


class ModelRating(BaseModel):  # type: ignore[misc]
    name: str
    category: str
    net_score: float
    net_score_latency: float
    ramp_up_time: float
    ramp_up_time_latency: float
    bus_factor: float
    bus_factor_latency: float
    performance_claims: float
    performance_claims_latency: float
    license: float
    license_latency: float
    dataset_and_code_score: float
    dataset_and_code_score_latency: float
    dataset_quality: float
    dataset_quality_latency: float
    code_quality: float
    code_quality_latency: float
    reproducibility: float
    reproducibility_latency: float
    reviewedness: float
    reviewedness_latency: float
    tree_score: float
    tree_score_latency: float
    size_score: rating_sizescore
    size_score_latency: float

# ---------------------------------------------


@router.get("/artifact/model/{artifact_id}/rate")
async def get_model_rating(
    artifact_id: str,
    x_authorization: Optional[str] = Header(None)
) -> Any:
    """
    Return the stored ModelRating for a given artifact ID.
    """
    if not artifact_id:
        raise HTTPException(
            status_code=400,
            detail="There is missing field(s) in the artifact_id or it is formed improperly, or is invalid.",
        )

    # Validate authentication token
    # Per OpenAPI spec: All endpoints require X-Authorization header
    if not x_authorization:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    # get ModelRating from s3 bucket
    s3_client = boto3.client("s3")
    key = f"rating/{artifact_id}.rate.json"
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        model_rating_obj = obj["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")

    # check ModelRating is valid
    try:
        model_rating = json.loads(model_rating_obj)
        model_rating = ModelRating(**model_rating)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The artifact rating system encountered an error while computing at least one metric.",
        )

    return model_rating


# ---------------------------------------------
# Rate functions called on upload to rate model
# ---------------------------------------------

def findDatasetAndCode(model_url: str) -> Tuple[str, str]:
    """
    Use ai to find code and dataset associated with hf model

    Parameters
    ----------
    model_url: str given in upload endpoint by user

    Returns
    ----------
    (code_url: str, dataset_url: str)
    """
    dataset_url = ""
    code_url = ""

    # First, try to get metadata from HuggingFace API
    try:
        # Extract model_id from URL (e.g., "google-bert/bert-base-uncased")
        model_id = model_url.replace("https://huggingface.co/", "").strip("/")

        # Fetch model metadata from HuggingFace API
        api_url = f"https://huggingface.co/api/models/{model_id}"
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            metadata = response.json()

            # Check for dataset in cardData or tags
            if 'cardData' in metadata:
                card_data = metadata['cardData']
                # Look for datasets in cardData
                if 'datasets' in card_data and card_data['datasets']:
                    dataset_name = card_data['datasets'][0]
                    # Handle both full URLs and dataset names
                    if dataset_name.startswith('http'):
                        dataset_url = dataset_name
                    elif '/' in dataset_name:
                        # Already has namespace (e.g., "bookcorpus/bookcorpus")
                        dataset_url = f"https://huggingface.co/datasets/{dataset_name}"
                    else:
                        # No namespace, assume it's namespace/name format (e.g., "bookcorpus" -> "bookcorpus/bookcorpus")
                        dataset_url = f"https://huggingface.co/datasets/{dataset_name}/{dataset_name}"

            # Check for code repository links, HuggingFace models often have a "library_name" or links in tags/cardData
            if 'tags' in metadata:
                for tag in metadata['tags']:
                    if isinstance(tag, str) and 'github.com' in tag:
                        code_url = tag if tag.startswith('http') else f"https://{tag}"
                        break

            # Also check model card for GitHub links if not found
            if not code_url or not dataset_url:
                model_card_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
                card_response = requests.get(model_card_url, timeout=10)
                if card_response.status_code == 200:
                    readme_text = card_response.text
                    # Look for GitHub links in README
                    if not code_url:
                        github_pattern = r'https://github\.com/[^\s\)\]\,]+'
                        github_matches = re.findall(github_pattern, readme_text)
                        if github_matches:
                            code_url = github_matches[0]

                    # Also look for dataset links if not found yet
                    if not dataset_url:
                        dataset_pattern = r'https://huggingface\.co/datasets/[^\s\)\]\,]+'
                        dataset_matches = re.findall(dataset_pattern, readme_text)
                        if dataset_matches:
                            dataset_url = dataset_matches[0]

    except Exception as e:
        print(f"Error fetching HuggingFace metadata: {e}")

    # If didn't find both, use LLM to search README
    if (not dataset_url) or (not code_url):
        prompt = ("Given a link to a HuggingFace model, analyze the metadata and README to find the links to the"
                  "associated dataset and code for the model."
                  "It is expected that the dataset will be a huggingface dataset and the code with be a GitHub repo."
                  "Teturn ONLY the actual links, including http://. If only one is found, return one. If none are found, return None."
                  "DO NOT return any other explanation, only the links."
                  "An example of the expected response I want: Given model_url = https://huggingface.co/google-bert/bert-base-uncased."
                  "Output https://github.com/google-research/bert,https://huggingface.co/datasets/bookcorpus/bookcorpus. Notice that the link is"
                  " to the actual dataset folder/ code folder, since I will be using github and hugginface api calls with it, "
                  "I need it to be exact. For example, something like https://huggingface.co/datasets/bookcorpus/bookcorpus is correct,"
                  "https://huggingface.co/datasets/bookcorpus is wrong."
                  "\n\nFind and tell me the dataset and code for " + model_url)

        client = PurdueGenAI()
        response = client.chat(prompt)
        # Find all URLs in the response using regex
        url_pattern = r'https?://[^\s,]+'
        urls = re.findall(url_pattern, response)

        for url in urls:
            # Only update the dataset/code url if it wasn't previously found
            if not code_url:
                if 'github.com' in url.lower():
                    code_url = url
            if not dataset_url:
                if 'huggingface.co/datasets' in url.lower():
                    dataset_url = url

    return dataset_url, code_url


def rateOnUpload(model_url: str, artifact_id: str) -> bool:
    """
    Calculate the rating for a model, store it, return if ingestible

    Parameters
    ----------
    model_url: str given in upload endpoint by user

    Returns
    ----------
    boolean: True if model, ingestible, False if not
    """
    # Find dataset and code url for model
    dataset_url, code_url = findDatasetAndCode(model_url)
    # calculate metrics
    rating = calculate_all_scores(code_url, dataset_url, model_url, set(), set())
    # check if ingestible comment out until rate works
    # for key, value in rating.items():
    #     # skip non-score items
    #     if (key == "name") or (key == "category") or key.endswith("latency"):
    #         continue
    #     # handle score dict
    #     if isinstance(value, dict):
    #         for val in value.values():
    #             if val < 0.5:
    #                 return False
    #     elif value < 0.5:
    #         return False

    # if ingestible: store metrics
    s3_client = boto3.client("s3")
    try:
        key = f"rating/{artifact_id}.rate.json"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=json.dumps(rating))
    except Exception as e:
        raise HTTPException(status_code=424, detail=f"Error rating model: {str(e)}")

    return True


if __name__ == "__main__":
    # for manual testing
    model_url = "https://huggingface.co/distilbert/distilbert-base-uncased"
    response = findDatasetAndCode(model_url)
    print(response)
