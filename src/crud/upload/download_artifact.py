import base64
import re
import shutil
from typing import List

import boto3
import httpx
from huggingface_hub import HfApi
from kaggle.api.kaggle_api_extended import KaggleApi

BUCKET_NAME = "phase2-s3-bucket"


def get_download_url(input_url: str, artifact_id: str, artifact_type: str) -> str:
    """
    call download_url function based on artifact type.

    Parameters
    ----------
    model_url: str given in upload endpoint by user
    artifact_id: str from upload
    artifact_type: str, model database or code

    Returns
    ----------
    url: str
    """
    if artifact_type == "model":
        url = download_model(input_url, artifact_id)
    elif artifact_type == "dataset":
        url = download_dataset(input_url, artifact_id)
    else:
        url = download_code(input_url, artifact_id)
    return url


def generate_index_html(artifact_id: str, file_paths: list[str]):
    """
    make html of list of items in downloaded hf repo/ s3 bucket with repo

    Parameters
    ----------
    artifact_id: str from upload
    file_paths: files from hf repo

    Returns
    ----------
    url: str
    """
    s3 = boto3.client("s3")

    # Build HTML content
    html_lines = ["<html><body><ul>"]
    for file_path in file_paths:
        url = f"https://{BUCKET_NAME}.s3.amazonaws.com/downloads/{artifact_id}/{file_path}"
        html_lines.append(f'<li><a href="{url}">{file_path}</a></li>')
    html_lines.append("</ul></body></html>")

    html_content = "\n".join(html_lines)

    # Upload index.html to S3
    index_key = f"downloads/{artifact_id}/index.html"
    s3.put_object(Bucket=BUCKET_NAME, Key=index_key, Body=html_content, ContentType="text/html")

    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{index_key}"


def download_model(model_url: str, artifact_id: str) -> str:
    """
    Stream download a hugging face model into s3. Return htlm of objects in s3 for download_url

    Parameters
    ----------
    model_url: str given in upload endpoint by user
    artifact_id: str from upload

    Returns
    ----------
    url: str
    """
    model_id = model_url.split("huggingface.co/")[-1]
    api = HfApi()
    s3 = boto3.client("s3")

    # List all files and filter by allowed patterns
    ALLOWED_PATTERNS = [".bin", ".safetensors", "config.json", "tokenizer", ".json", ".txt"]
    files = api.list_repo_files(repo_id=model_id)
    files = [f for f in files if any(f.endswith(p.replace("*", "")) or p in f for p in ALLOWED_PATTERNS)]

    for file_path in files:
        file_url = f"https://huggingface.co/{model_id}/resolve/main/{file_path}"
        s3_key = f"downloads/{artifact_id}/{file_path}"

        # Stream the file in chunks
        with httpx.stream("GET", file_url, follow_redirects=True) as response:
            response.raise_for_status()

            # boto3 upload_fileobj accepts any file-like object with a read() method
            class StreamWrapper:
                def __init__(self, stream, chunk_size=1024*1024):
                    self.stream = stream.iter_bytes(chunk_size)

                def read(self, size=-1):
                    try:
                        return next(self.stream)
                    except StopIteration:
                        return b''

            s3.upload_fileobj(StreamWrapper(response), BUCKET_NAME, s3_key)

    url = generate_index_html(artifact_id, files)
    return url


def download_dataset(dataset_url: str, artifact_id: str) -> str:
    """
    Download dataset files based on source. Return htlm of objects in s3 for download_url

    Parameters
    ----------
    dataset_url: str given in upload endpoint by user
    artifact_id: str from upload

    Returns
    ----------
    url: str
    """
    # Determine the source platform
    if "huggingface.co" in dataset_url:
        files = download_dataset_huggingface(dataset_url, artifact_id)
    elif "kaggle.com" in dataset_url:
        files = download_dataset_kaggle(dataset_url, artifact_id)
    elif "github.com" in dataset_url:
        files = download_dataset_github(dataset_url, artifact_id)
    else:
        raise ValueError(f"Unsupported dataset URL: {dataset_url}")

    url = generate_index_html(artifact_id, files)
    return url


def download_dataset_huggingface(dataset_url: str, artifact_id: str) -> List[str]:
    dataset_id = dataset_url.split("huggingface.co/")[-1].replace("datasets/", "")
    api = HfApi()
    s3 = boto3.client("s3")

    # List all files in the dataset repo
    files = api.list_repo_files(repo_id=dataset_id, repo_type="dataset")

    # No pattern filtering for datasets — download everything in the repo
    for file_path in files:
        file_url = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/{file_path}"
        s3_key = f"downloads/{artifact_id}/{file_path}"

        # Stream the file in chunks
        with httpx.stream("GET", file_url, follow_redirects=True) as response:
            response.raise_for_status()

            class StreamWrapper:
                def __init__(self, stream, chunk_size=1024*1024):
                    self.stream = stream.iter_bytes(chunk_size)

                def read(self, size=-1):
                    try:
                        return next(self.stream)
                    except StopIteration:
                        return b''

            s3.upload_fileobj(StreamWrapper(response), BUCKET_NAME, s3_key)

    return files


def download_dataset_kaggle(dataset_url: str, artifact_id: str) -> List[str]:
    """
    Download Kaggle dataset zip and stream directly to S3 without extracting.
    """
    s3 = boto3.client("s3")

    # Minimal disk space check
    stat = shutil.disk_usage('/tmp')
    free_gb = stat.free / (1024**3)

    if free_gb < 0.1:
        raise Exception(f"Insufficient disk space: {free_gb:.1f}GB free")

    # Parse URL
    if "/datasets/" in dataset_url:
        match = re.search(r'kaggle\.com/datasets/([^/]+/[^/?]+)', dataset_url)
        if not match:
            raise ValueError(f"Invalid Kaggle dataset URL: {dataset_url}")
        dataset_ref = match.group(1)
    else:
        raise ValueError(f"Unsupported Kaggle URL format: {dataset_url}")

    # Authenticate
    api = KaggleApi()
    api.authenticate()

    # Build download URL for entire dataset as zip
    download_url = f"https://www.kaggle.com/api/v1/datasets/download/{dataset_ref}"

    # Get credentials
    username = api.get_config_value('username')
    key = api.get_config_value('key')
    credentials = base64.b64encode(f"{username}:{key}".encode()).decode()
    headers = {"Authorization": f"Basic {credentials}"}

    # Set generous timeout since we're just streaming through
    timeout = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        try:
            with client.stream("GET", download_url, headers=headers) as response:
                if response.status_code == 401:
                    raise Exception("Authentication failed - check Kaggle credentials")
                elif response.status_code == 403:
                    raise Exception("Access forbidden. You may need to accept the dataset's terms on Kaggle website first.")
                elif response.status_code == 404:
                    raise Exception(f"Dataset not found: {dataset_ref}")

                response.raise_for_status()

                # Extract dataset name for a clean filename
                dataset_name = dataset_ref.split('/')[-1]
                s3_key = f"downloads/{artifact_id}/{dataset_name}.zip"

                # Stream directly to S3 as a zip file
                class StreamWrapper:
                    def __init__(self, stream, chunk_size=1024*1024):  # 1MB chunks
                        self.stream = stream.iter_bytes(chunk_size)
                        self.total_mb = 0

                    def read(self, size=-1):
                        try:
                            chunk = next(self.stream)
                            self.total_mb += len(chunk) / (1024 * 1024)
                            return chunk
                        except StopIteration:
                            return b''

                wrapper = StreamWrapper(response)
                s3.upload_fileobj(wrapper, BUCKET_NAME, s3_key)

                # Return list with just the zip file
                return [f"{dataset_name}.zip"]

        except httpx.HTTPError as e:
            raise Exception(f"HTTP error downloading dataset: {str(e)}")
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")


def download_dataset_github(dataset_url: str, artifact_id: str) -> List[str]:
    """
    Stream download a GitHub dataset repo into S3. Return list of files.

    Parameters
    ----------
    dataset_url: str - GitHub repo URL
    artifact_id: str - unique identifier for this artifact

    Returns
    ----------
    files: List[str] - list of file paths downloaded
    """
    s3 = boto3.client("s3")

    # Parse GitHub URL to extract owner and repo
    # Handles: https://github.com/owner/repo
    #          https://github.com/owner/repo/tree/branch/path
    #          https://github.com/owner/repo/blob/branch/file
    dataset_url = dataset_url.rstrip("/")

    # Remove trailing .git if present
    if dataset_url.endswith('.git'):
        dataset_url = dataset_url[:-4]

    # Extract owner and repo from URL
    match = re.match(r'https://github\.com/([^/]+)/([^/]+)(?:/.*)?', dataset_url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {dataset_url}")

    owner, repo = match.groups()

    # Remove any path segments from repo name
    repo = repo.split('/')[0]

    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        # Get default branch of repo
        repo_api = f"https://api.github.com/repos/{owner}/{repo}"
        repo_resp = client.get(repo_api)
        repo_resp.raise_for_status()
        default_branch = repo_resp.json()["default_branch"]

        # Get full recursive tree of default branch
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        tree_resp = client.get(tree_url)
        tree_resp.raise_for_status()
        tree = tree_resp.json().get("tree", [])

        # Keep only blobs (files), not trees (directories)
        files = [item["path"] for item in tree if item["type"] == "blob"]

    # Stream each file from raw GitHub
    downloaded_files = []

    for file_path in files:
        file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{file_path}"
        s3_key = f"downloads/{artifact_id}/{file_path}"

        try:
            # Stream file bytes
            with httpx.stream("GET", file_url, follow_redirects=True) as response:
                if response.status_code == 404:
                    continue

                response.raise_for_status()

                class StreamWrapper:
                    def __init__(self, stream, chunk_size=1024 * 1024):
                        self.stream = stream.iter_bytes(chunk_size)

                    def read(self, size=-1):
                        try:
                            return next(self.stream)
                        except StopIteration:
                            return b""

                # Upload to S3
                s3.upload_fileobj(StreamWrapper(response), BUCKET_NAME, s3_key)
                downloaded_files.append(file_path)

        except Exception as e:
            print(f"Failed to download {file_path}: {e}")
            continue

    if not downloaded_files:
        raise Exception("No files were successfully downloaded from GitHub")

    return downloaded_files


def download_code(code_url: str, artifact_id: str) -> str:
    """
    Stream download a GitHub code repo into s3. Return htlm of objects in s3 for download_url

    Parameters
    ----------
    code_url: str given in upload endpoint by user
    artifact_id: str from upload

    Returns
    ----------
    url: str
    """
    s3 = boto3.client("s3")

    # Extract GitHub owner + repo name
    parts = code_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1]

    with httpx.Client(follow_redirects=True) as client:
        # Get default branch of repo
        repo_api = f"https://api.github.com/repos/{owner}/{repo}"
        repo_resp = client.get(repo_api)
        repo_resp.raise_for_status()
        default_branch = repo_resp.json()["default_branch"]

        # Get full recursive tree of default branch
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        tree_resp = client.get(tree_url)
        tree_resp.raise_for_status()
        tree = tree_resp.json().get("tree", [])

        # Keep only blobs (files)
        files = [item["path"] for item in tree if item["type"] == "blob"]

    # Stream each file from raw GitHub
    for file_path in files:
        file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{file_path}"
        s3_key = f"downloads/{artifact_id}/{file_path}"

        # Stream file bytes using same pattern as model/dataset download
        with httpx.stream("GET", file_url, follow_redirects=True) as response:
            if response.status_code == 404:
                continue  # skip missing raw files
            response.raise_for_status()

            class StreamWrapper:
                def __init__(self, stream, chunk_size=1024 * 1024):
                    self.stream = stream.iter_bytes(chunk_size)

                def read(self, size=-1):
                    try:
                        return next(self.stream)
                    except StopIteration:
                        return b""

            # Upload to S3
            s3.upload_fileobj(StreamWrapper(response), BUCKET_NAME, s3_key)

    # Generate index.html of all files
    url = generate_index_html(artifact_id, files)

    return url


if __name__ == "__main__":
    artifact_id = "02"
    # kaggle_dataset = "https://www.kaggle.com/datasets/hliang001/flickr2k"
    # files = download_dataset(kaggle_dataset, artifact_id)
    github_dataset = "https://github.com/datablist/sample-csv-files"
    files = download_dataset(github_dataset, artifact_id)
    print(files)
