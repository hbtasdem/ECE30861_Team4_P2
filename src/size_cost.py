import requests
from huggingface_hub import HfApi, hf_hub_url


def get_model_size_gb(model_id: str) -> float:
    api = HfApi()
    files = api.list_repo_files(repo_id=model_id)

    total_bytes = 0
    for file in files:
        url = hf_hub_url(repo_id=model_id, filename=file)
        r = requests.head(url, allow_redirects=True)

        size = r.headers.get("content-length")
        if size:
            total_bytes += int(size)

    return round((total_bytes / (1024 ** 3)) / 0.93, 3)  # division by 0.93 compensates for loss of overhead
