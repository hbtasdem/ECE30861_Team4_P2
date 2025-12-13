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
    Create a lightweight zip containing only the README for security scanning.

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
            # Download just the README
            readme_url = f"https://huggingface.co/{model_id}/resolve/main/README.md"

            try:
                response = httpx.get(readme_url, follow_redirects=True, timeout=10.0)
                response.raise_for_status()

                # Add README to zip
                zipf.writestr("README.md", response.content)
                print(f"Added README.md to zip for {model_name}")

            except Exception as e:
                # If README doesn't exist, create a minimal one
                print(f"Warning: Could not download README for {model_id}: {e}")
                minimal_readme = f"# {model_name}\n\nModel URL: {model_url}\n"
                zipf.writestr("README.md", minimal_readme)

        return temp_zip.name

    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise Exception(f"Failed to create zip for model {model_name}: {str(e)}")


def sensitive_check(model_name: str, model_url: str, uploader_username: str) -> Any:
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
            [
                'node',
                js_file_path,
                model_name,
                uploader_username,
                uploader_username,  # Same user for upload check
                zip_path
            ],
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
        # Cleanup temp files
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
        raise HTTPException(
            status_code=400,
            detail="Program must be a .js file"
        )

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
async def get_js_program(
    x_authorization: Optional[str] = Header(None),
):
    """Get the current JavaScript monitoring program."""
    s3_client = boto3.client("s3")

    try:
        response = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key="monitoring-program.js"
        )
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
async def delete_js_program(
    x_authorization: Optional[str] = Header(None),
):
    """Delete the JavaScript monitoring program."""

    # Optional: Check if user is admin
    # username = get_current_user(x_authorization, None)
    # if not is_admin(username):
    #     raise HTTPException(status_code=403, detail="Admin access required")

    s3_client = boto3.client("s3")

    try:
        s3_client.delete_object(
            Bucket=BUCKET_NAME,
            Key="monitoring-program.js"
        )
        return {"message": "JavaScript program deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TEST JAVASCRIPT TO UPLOAD
# // test-monitor-keywords.js
# // Rejects models with suspicious keywords

# const [modelName, uploader, downloader, zipPath] = process.argv.slice(2);

# // List of banned keywords
# const bannedKeywords = ['malicious', 'virus', 'hack', 'exploit', 'backdoor'];

# // Check model name
# for (const keyword of bannedKeywords) {
#     if (modelName.toLowerCase().includes(keyword)) {
#         console.log(`REJECTED: Model name contains banned keyword: "${keyword}"`);
#         process.exit(1);  // Non-zero = reject
#     }
# }

# // Check uploader
# const bannedUsers = ['hacker123', 'malicious_user'];
# if (bannedUsers.includes(uploader)) {
#     console.log(`REJECTED: User "${uploader}" is banned`);
#     process.exit(1);
# }

# console.log('APPROVED: Model passed all security checks');
# process.exit(0);
