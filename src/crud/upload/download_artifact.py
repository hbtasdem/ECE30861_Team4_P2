import boto3
import httpx
from huggingface_hub import HfApi

BUCKET_NAME = "phase2-s3-bucket"

# Only download/upload these file patterns
ALLOWED_PATTERNS = [
    ".bin",
    ".safetensors",
    "config.json",
    "tokenizer",
    ".json",
    ".txt",
]


def download_model(model_url: str) -> str:
    """
    Stream a Hugging Face model repo directly to S3.
    Returns a presigned URL for the "folder" (S3 objects prefix).
    """
    model_id = model_url.split("huggingface.co/")[-1]
    api = HfApi()
    s3 = boto3.client("s3")

    files = api.list_repo_files(repo_id=model_id)
    files = [f for f in files if any(f.endswith(p.replace("*", "")) or p in f for p in ALLOWED_PATTERNS)]

    for file_path in files:
        # Get the raw file URL from HF Hub
        file_url = f"https://huggingface.co/{model_id}/resolve/main/{file_path}"
        s3_key = f"downloads/{model_id}/{file_path}"

        # Stream file from HF to S3
        with httpx.stream("GET", file_url) as r:
            r.raise_for_status()
            s3.upload_fileobj(r.raw, BUCKET_NAME, s3_key)
        print(f"[S3 UPLOAD] {file_path} → s3://{BUCKET_NAME}/{s3_key}")

    # Generate presigned URL for the model folder (objects prefix)
    # NOTE: S3 doesn’t support folder URLs directly; you can list objects with the prefix
    url = s3.generate_presigned_url(
        "list_objects_v2",
        Params={"Bucket": BUCKET_NAME, "Prefix": f"downloads/{model_id}/"},
        ExpiresIn=7*24*3600
    )
    return url


def download_dataset(dataset_url: str) -> str:
    pass


def download_code(code_url: str) -> str:
    pass
