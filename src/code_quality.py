# code_quality.py
"""
Evaluate Hugging Face model repository quality.
Submetrics:
- JSON/config presence and validity [weight 0.4]
- README presence [weight 0.2]
- LICENSE presence [weight 0.2]
- Example notebooks / usage examples [weight 0.2]
Only fetches repo metadata/files, not full model weights.
"""

import json
import time
from huggingface_hub import HfApi, hf_hub_download

# --------- Helper functions ---------


def get_repo_files(model_name):
    """Return a list of all files in the HF repo."""
    api = HfApi()
    try:
        return api.list_repo_files(repo_id=model_name)
    except Exception:
        return []


def download_file(model_name, filename):
    """Download a single file and return local path."""
    try:
        return hf_hub_download(repo_id=model_name, filename=filename)
    except Exception:
        return None


# --------- Submetric calculators ---------


def json_score(model_name):
    """Score based on presence and validity of JSON/config files."""
    files = get_repo_files(model_name)
    json_files = [f for f in files if f.endswith(".json")]
    if not json_files:
        return 0.0

    valid_count = 0
    for f in json_files:
        local_path = download_file(model_name, f)
        if not local_path:
            continue
        try:
            with open(local_path, "r", encoding="utf-8") as fi:
                json.load(fi)
            valid_count += 1
        except Exception:
            continue

    score = valid_count / len(json_files)
    return score * 0.4  # weight of 0.4


def readme_score(model_name):
    files = get_repo_files(model_name)
    for f in files:
        if f.lower().startswith("readme"):
            return 0.2
    return 0.0


def license_score(model_name):
    files = get_repo_files(model_name)
    for f in files:
        if "license" in f.lower():
            return 0.2
    return 0.0


# --------- Main metric calculator ---------


def code_quality_score(model_name):
    """
    Calculate overall code quality for a Hugging Face model repo.
    Returns: (score 0-1 float, latency in seconds)
    """
    start_time = time.time()

    j_score = json_score(model_name)
    rd_score = readme_score(model_name)
    lic_score = license_score(model_name)

    print(j_score)
    print(rd_score)  #
    print(lic_score)  #

    overall_score = j_score + rd_score + lic_score
    latency = time.time() - start_time
    return overall_score, latency


# --------- Test / CLI ---------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python code_quality.py <model_name>")
        sys.exit(1)
    model_name = sys.argv[1]
    score, latency = code_quality_score(model_name)
    print(f"Code quality score for {model_name}: {score:.3f}, latency: {latency:.2f}s")
