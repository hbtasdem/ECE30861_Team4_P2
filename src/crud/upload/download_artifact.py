import boto3
from huggingface_hub import HfApi, hf_hub_download

BUCKET_NAME = "phase2-s3-bucket"


def download_model(model_url: str) -> str:
    model_id = model_url.split("huggingface.co/")[-1]
    api = HfApi()
    s3 = boto3.client("s3")

    # Download only necessary formats
    ALLOWED_PATTERNS = [
        "*.bin",
        "*.safetensors",
        "config.json",
        "tokenizer*",
        "*.json",
        "*.txt",
    ]

    # List all files in repo and filter manually
    files = api.list_repo_files(repo_id=model_id)
    files = [f for f in files if any(f.endswith(p.replace("*", "")) for p in ALLOWED_PATTERNS)]

    for file_path in files:
        # Download small chunks to a temp file
        tmp_file = hf_hub_download(
            repo_id=model_id,
            filename=file_path,
            local_dir=None,       # keeps it in HF cache, not EC2
            local_dir_use_symlinks=False,
        )

        # Upload to S3
        s3_key = f"models/{model_id}/{file_path}"
        s3.upload_file(tmp_file, BUCKET_NAME, s3_key)
        print(f"[S3 UPLOAD] {file_path} → s3://{BUCKET_NAME}/{s3_key}")

    # Generate folder-style URL
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": f"downloads/{model_id}/"},
        ExpiresIn=7*24*3600
    )
    return url


def download_dataset(dataset_url: str) -> str:
    pass


def download_code(code_url: str) -> str:
    pass
