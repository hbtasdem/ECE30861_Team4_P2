import boto3
import httpx
from huggingface_hub import HfApi

BUCKET_NAME = "phase2-s3-bucket"


def get_download_url(model_url: str, artifact_id: str, artifact_type: str) -> str:
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
        url = download_model(model_url, artifact_id)
    elif artifact_type == "dataset":
        url = "dataset_url"
    else:
        url = "code_url"
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
    print(f"[S3 UPLOAD] index.html → s3://{BUCKET_NAME}/{index_key}")

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
    ALLOWED_PATTERNS = [
        ".bin",
        ".safetensors",
        "config.json",
        "tokenizer",
        ".json",
        ".txt",
    ]
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
            print(f"[S3 UPLOAD] {file_path} → s3://{BUCKET_NAME}/{s3_key}")

    url = generate_index_html(artifact_id, files)
    return url


def download_dataset(dataset_url: str) -> str:
    pass


def download_code(code_url: str) -> str:
    pass
