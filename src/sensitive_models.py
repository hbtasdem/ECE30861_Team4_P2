"""
Functions and endpoints for the sensitive models part of phase 2 security track

v1:
On upload:
- Assume a boolean "sensitive" variable is passed in on model upload
- Track whenever a "sensitive" model is uploaded or updated, don't track when a user actually clicks the download_url
- If "sensitive" is true, it will call sensitive_check to run the javascript on the model

NEW ENDPOINTS
To post a javascript program into an s3 that will get used later?
@router.post("/sensitive/javascript-program")
@router.get("/sensitive/javascript-program")
@router.delete("/sensitive/javascript-program")

JavaScript program:
- Run under Node.js v 24
- Accepts four command line arguments "MODEL_NAME UPLOADER_USERNAME DOWNLOADER_USERNAME ZIP_FILE_PATH”.
If the program exits with a non-zero code, the download of the model should
be rejected with an appropriate error message that includes the stdout from the program.
"""

import json
import os
import subprocess
import tempfile
import zipfile
from typing import Any, Optional

import boto3
import httpx
from fastapi import APIRouter, File, Header, HTTPException, UploadFile

# Create or import the router
router = APIRouter()

BUCKET_NAME = "phase2-s3-bucket"


def make_sensitive_zip(model_name: str, model_url: str) -> str:
    """
    Create a  zip containing README and metadata for security scanning.
    Does NOT download large model files - only metadata.

    Args:
        model_name: Name of the model
        model_url: HuggingFace model URL

    Returns:
        str: Path to the temporary zip file
    """

    model_id = model_url.split("huggingface.co/")[-1]

    # Create temp zip file
    temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    temp_zip.close()

    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Download README
            readme_url = f"https://huggingface.co/{model_id}/resolve/main/README.md"
            try:
                response = httpx.get(readme_url, follow_redirects=True, timeout=10.0)
                response.raise_for_status()
                zipf.writestr("README.md", response.content)
                print(f"Added README.md to zip for {model_name}")
            except Exception as e:
                print(f"Warning: Could not download README for {model_id}: {e}")
                minimal_readme = f"# {model_name}\n\nModel URL: {model_url}\n"
                zipf.writestr("README.md", minimal_readme)

            # 2. Get model info from HuggingFace API
            try:
                api_url = f"https://huggingface.co/api/models/{model_id}"
                response = httpx.get(api_url, timeout=10.0)
                response.raise_for_status()
                model_info = response.json()
                zipf.writestr("model_info.json", json.dumps(model_info, indent=2))
                print(f"Added model_info.json for {model_name}")
            except Exception as e:
                print(f"Warning: Could not fetch model info: {e}")

            # 3. Get model config
            config_url = f"https://huggingface.co/{model_id}/resolve/main/config.json"
            try:
                response = httpx.get(config_url, follow_redirects=True, timeout=10.0)
                response.raise_for_status()
                zipf.writestr("config.json", response.content)
                print(f"Added config.json for {model_name}")
            except Exception:
                print("Info: No config.json found (this is OK)")

            # 4. Get list of files in the repo (metadata only, not downloading)
            try:
                from huggingface_hub import HfApi
                api = HfApi()
                file_list = api.list_repo_files(repo_id=model_id)
                file_manifest = {
                    "model_id": model_id,
                    "total_files": len(file_list),
                    "files": file_list
                }
                zipf.writestr("file_manifest.json", json.dumps(file_manifest, indent=2))
                print(f"Added file_manifest.json for {model_name}")

            except Exception as e:
                print(f"Warning: Could not list repo files: {e}")

            # 5. Create a security scan summary
            scan_summary = {
                "model_name": model_name,
                "model_url": model_url,
                "model_id": model_id,
                "note": "This scan includes only metadata and README - no model weights downloaded"
            }
            zipf.writestr("_scan_summary.json", json.dumps(scan_summary, indent=2))

        return temp_zip.name

    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise Exception(f"Failed to create zip for model {model_name}: {str(e)}")


def sensitive_check(model_name: str, model_url: str, uploader_username: str) -> Any:
    """
    Run JS program on model.

    Args:
        model_name: Name of the model
        model_url: HuggingFace model URL
        uploader_username: Username that accessed upload endpoint

    Returns:
        If JS returns 0, nothing just accept the download
        If JS returns non-zero, print the error and reject download
    """
    s3_client = boto3.client("s3")
    # get JS program from s3
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key="monitoring-program.js")
        js_program = response['Body'].read()
    except s3_client.exceptions.NoSuchKey:
        # No JS program configured - reject
        return

    # create model zip
    zip_path = make_sensitive_zip(model_name, model_url)

    try:
        # write JS program to temp file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.js', delete=False) as js_file:
            js_file.write(js_program)
            js_file_path = js_file.name

        # run JS program with args MODEL_NAME UPLOADER_USERNAME DOWNLOADER_USERNAME ZIP_FILE_PATH
        result = subprocess.run(
            ['node', js_file_path, model_name, uploader_username, uploader_username, zip_path],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        # check JS return code
        if result.returncode != 0:
            raise HTTPException(
                status_code=403,
                detail=f"Model upload rejected by monitoring program: {result.stdout}"
            )

    finally:
        # Clean up temp files
        if os.path.exists(js_file_path):
            os.unlink(js_file_path)
        if os.path.exists(zip_path):
            os.unlink(zip_path)


# ==================================================
# ENDPOINTS
# ==================================================

@router.post("/sensitive/javascript-program")
async def upload_js_program(program: UploadFile = File(...), x_authorization: Optional[str] = Header(None)):
    """
    Upload a JavaScript program that will be run on sensitive model uploads.
    Only one JS program is active at a time (overwrites previous).

    The program should:
    - Run under Node.js v24
    - Accept args: MODEL_NAME UPLOADER_USERNAME DOWNLOADER_USERNAME ZIP_FILE_PATH
    - Exit with 0 for success, non-zero for rejection
    """

    # Optional: Check if user is admin
    # username = get_current_user(x_authorization, None)
    # if not is_admin(username):
    #     raise HTTPException(status_code=403, detail="Admin access required")

    s3_client = boto3.client("s3")

    # Validate it's a JS file
    if not program.filename.endswith('.js'):
        raise HTTPException(status_code=400, detail="Program must be a .js file")

    # Read the program
    js_content = await program.read()

    # Store in S3 (overwrites any existing program)
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key="monitoring-program.js",
        Body=js_content,
        ContentType="application/javascript"
    )

    return {
        "message": "JavaScript program uploaded successfully",
        "filename": program.filename,
        "size": len(js_content)
    }


@router.get("/sensitive/javascript-program")
async def get_js_program(x_authorization: Optional[str] = Header(None)):
    """Get the current JavaScript monitoring program."""
    s3_client = boto3.client("s3")

    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key="monitoring-program.js")
        js_content = response['Body'].read().decode('utf-8')

        return {
            "program": js_content,
            "last_modified": response['LastModified'].isoformat(),
        }
    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(
            status_code=404,
            detail="No JavaScript program has been uploaded yet"
        )


@router.delete("/sensitive/javascript-program")
async def delete_js_program(x_authorization: Optional[str] = Header(None)):
    """Delete the JavaScript monitoring program."""

    # Optional: Check if user is admin
    # username = get_current_user(x_authorization, None)
    # if not is_admin(username):
    #     raise HTTPException(status_code=403, detail="Admin access required")

    s3_client = boto3.client("s3")

    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key="monitoring-program.js")
        return {"message": "JavaScript program deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TEST JAVASCRIPT TO UPLOAD

# // simple-monitor.js
# const fs = require('fs');
# const [modelName, uploader, downloader, zipPath] = process.argv.slice(2);

# console.log(`Checking model: ${modelName}`);
# console.log(`Uploader: ${uploader}`);

# // Basic checks without parsing the ZIP
# // (Your Python code already extracted the metadata)

# // Check 1: Model name patterns
# const bannedKeywords = ['malicious', 'virus', 'exploit', 'nsfw', 'illegal'];
# for (const keyword of bannedKeywords) {
#     if (modelName.toLowerCase().includes(keyword)) {
#         console.log(`REJECTED: Model name contains: ${keyword}`);
#         process.exit(1);
#     }
# }

# // Check 2: Banned uploaders
# const bannedUsers = ['known_bad_actor', 'spam_account'];
# if (bannedUsers.includes(uploader)) {
#     console.log(`REJECTED: Uploader is banned`);
#     process.exit(1);
# }

# // Check 3: ZIP file exists and has reasonable size
# if (!fs.existsSync(zipPath)) {
#     console.log('REJECTED: ZIP file missing');
#     process.exit(1);
# }

# const stats = fs.statSync(zipPath);
# if (stats.size < 100) {
#     console.log('REJECTED: ZIP file too small (likely empty)');
#     process.exit(1);
# }

# console.log('APPROVED: Basic checks passed');
# process.exit(0);
