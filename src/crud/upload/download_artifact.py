# During upload, upload the artifact into s3 and give a link for users to download it
import os
import shutil
import zipfile

import boto3
from huggingface_hub import snapshot_download

s3 = boto3.client("s3")
BUCKET_NAME = "phase2-s3-bucket"


def download_model(model_url: str) -> str:
    """
    download model locally, zip and store in s3, delete locally, return download url

    Parameters
    ----------
    model_url: str given in upload endpoint by user

    Returns
    ----------
    str download_url for user to download model from s3
    """
    # Step 1: Download model locally
    model_id = model_url.split("huggingface.co/")[-1]
    local_folder = snapshot_download(repo_id=model_id, cache_dir="/tmp/hf_models")

    # Step 2: Zip the folder
    zip_filename = f"/tmp/{model_id.replace('/', '_')}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(local_folder):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, local_folder))

    # Step 3: Upload zip to S3
    s3_key = f"downloads/{model_id}.zip"

    s3.upload_file(zip_filename, BUCKET_NAME, s3_key)

    # Step 4: Delete local folder and zip to free disk
    shutil.rmtree(local_folder)
    os.remove(zip_filename)

    # Step 5: Generate pre-signed URL
    expiration = 7 * 24 * 60 * 60  # 1 week in seconds
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expiration
    )
    return url


def download_dataset(dataset_url: str) -> str:
    pass


def download_code(code_url: str) -> str:
    pass
