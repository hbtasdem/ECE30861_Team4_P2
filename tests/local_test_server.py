"""
LOCAL TEST SERVER FOR ARTIFACT ROUTES
======================================

Runs a local FastAPI server on Windows to test artifact_routes.py
WITHOUT connecting to AWS S3 or the remote server.

Usage:
    python local_test_server.py

Then test with:
    python tests/test_regex_live.py basic
    (But change SERVER_URL to "http://localhost:8000" first)
"""

import json
import os
from typing import Dict, List, Any
from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# ===========================================================================
# MOCK DATA - Simulates S3 artifacts
# ===========================================================================

MOCK_ARTIFACTS = {
    "model/01KCF66B22KT18BTTQV8XQB52M.json": {
        "metadata": {
            "name": "bert-base-uncased",
            "id": "01KCF66B22KT18BTTQV8XQB52M",
            "type": "model"
        },
        "data": {
            "url": "https://huggingface.co/bert-base-uncased",
            "download_url": "https://example.com/download/bert"
        }
    },
    "model/01KCF66MCCSG0VVS6YJRZAHMS9.json": {
        "metadata": {
            "name": "distilbert-base-uncased-distilled-squad",
            "id": "01KCF66MCCSG0VVS6YJRZAHMS9",
            "type": "model"
        },
        "data": {
            "url": "https://huggingface.co/distilbert-base-uncased-distilled-squad",
            "download_url": "https://example.com/download/distilbert"
        }
    },
    "code/01KCF66B22KT18BTTQV8XQB52M.json": {
        "metadata": {
            "name": "bert",
            "id": "01ABC126",
            "type": "code"
        },
        "data": {
            "url": "https://github.com/user/bert",
            "download_url": "https://example.com/download/bert-code"
        }
    },
    "model/01KCF66EKYZQ3RA0WHCPBA4EQN.json": {
        "metadata": {
            "name": "audience_classifier_model",
            "id": "01KCF66EKYZQ3RA0WHCPBA4EQN",
            "type": "model"
        },
        "data": {
            "url": "https://huggingface.co/some/audience-classifier",
            "download_url": "https://example.com/download/audience"
        }
    },
    "dataset/01ABC127.json": {
        "metadata": {
            "name": "my-dataset",
            "id": "01ABC127",
            "type": "dataset"
        },
        "data": {
            "url": "https://example.com/dataset",
            "download_url": "https://example.com/download/dataset"
        }
    }
}

# Valid auth token for testing
VALID_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6ImVjZTMwODYxZGVmYXVsdGFkbWludXNlciIsImlzX2FkbWluIjp0cnVlLCJleHAiOjE3NjU3NzkzNTZ9.o75fVtL8U8bz3xalRbCVT0MhjQ8M1qOpt4GpMZmqaGc"

# ===========================================================================
# PYDANTIC MODELS
# ===========================================================================

class ArtifactMetadata(BaseModel):
    name: str
    id: str
    type: str

class ArtifactRegEx(BaseModel):
    regex: str

# ===========================================================================
# MOCK S3 CLIENT
# ===========================================================================

class MockS3Client:
    """Mock boto3 S3 client for local testing."""
    
    def get_paginator(self, operation):
        return MockPaginator()
    
    def get_object(self, Bucket, Key):
        if Key in MOCK_ARTIFACTS:
            class MockResponse:
                def __init__(self, data):
                    self.data = data
                
                class Body:
                    def __init__(self, data):
                        self.data = data
                    
                    def read(self):
                        return json.dumps(self.data).encode('utf-8')
                
                def __getitem__(self, key):
                    if key == "Body":
                        return self.Body(self.data)
                    raise KeyError(key)
            
            return MockResponse(MOCK_ARTIFACTS[Key])
        else:
            from botocore.exceptions import ClientError
            error_response = {'Error': {'Code': 'NoSuchKey'}}
            raise ClientError(error_response, 'get_object')

class MockPaginator:
    """Mock S3 paginator."""
    
    def paginate(self, Bucket, Prefix):
        # Filter mock artifacts by prefix
        matching_keys = [
            key for key in MOCK_ARTIFACTS.keys()
            if key.startswith(Prefix)
        ]
        
        if matching_keys:
            return [{
                "Contents": [{"Key": key} for key in matching_keys]
            }]
        else:
            return [{}]

# ===========================================================================
# MOCK DEPENDENCIES
# ===========================================================================

def mock_get_current_user(x_authorization, db):
    """Mock authentication - just check if token matches."""
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing auth")
    
    token = x_authorization.replace("bearer ", "").replace("Bearer ", "")
    if token != VALID_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Return mock user
    class MockUser:
        username = "testuser"
        is_admin = True
    
    return MockUser()

def mock_try_fetch_readme_from_url(url: str):
    """Mock README fetching."""
    return None  # Simplified for testing

# ===========================================================================
# HELPER FUNCTIONS (from artifact_routes.py)
# ===========================================================================

def _get_artifacts_by_type(artifact_type: str) -> List[Dict[str, Any]]:
    """List all artifacts of a given type from mock data."""
    artifacts = []
    prefix = f"{artifact_type}/"
    
    for key, artifact_data in MOCK_ARTIFACTS.items():
        if key.startswith(prefix) and key.endswith(".json"):
            artifacts.append(artifact_data)
    
    return artifacts

# ===========================================================================
# FASTAPI APP
# ===========================================================================

app = FastAPI(title="Local Artifact Registry Test Server")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# REGEX ENDPOINT (from your artifact_routes.py)
# ===========================================================================

@app.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
async def get_artifacts_by_regex(
    request: ArtifactRegEx,
    x_authorization: str = Header(None),
):
    """Search for artifacts using regular expression."""
    import re
    
    # Auth check
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )
    
    try:
        mock_get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )
    
    # Compile regex
    try:
        regex_pattern = re.compile(request.regex, re.IGNORECASE)
    except re.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid",
        )
    
    # Search artifacts
    matching = []
    for artifact_type in ["model", "dataset", "code"]:
        artifacts = _get_artifacts_by_type(artifact_type)
        
        for artifact in artifacts:
            name = artifact["metadata"]["name"]
            
            # Match name
            if regex_pattern.search(name):
                matching.append(
                    ArtifactMetadata(
                        name=name,
                        id=artifact["metadata"]["id"],
                        type=artifact["metadata"]["type"],
                    )
                )
    
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No artifact found under this regex.",
        )
    
    return matching

# ===========================================================================
# HEALTH CHECK
# ===========================================================================

@app.get("/")
def health_check():
    """Health check endpoint."""
    return {
        "status": "running",
        "message": "Local test server is running",
        "artifacts": len(MOCK_ARTIFACTS),
        "note": "This is a LOCAL test server with MOCK data"
    }

@app.get("/artifacts/list")
def list_artifacts():
    """List all mock artifacts."""
    return {
        "total": len(MOCK_ARTIFACTS),
        "artifacts": [
            {
                "name": artifact["metadata"]["name"],
                "type": artifact["metadata"]["type"],
                "id": artifact["metadata"]["id"]
            }
            for artifact in MOCK_ARTIFACTS.values()
        ]
    }

# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("LOCAL ARTIFACT REGISTRY TEST SERVER")
    print("="*70)
    print("Status: Starting...")
    print("URL: http://localhost:8000")
    print("Mock Artifacts:", len(MOCK_ARTIFACTS))
    print("="*70)
    print("\nEndpoints available:")
    print("  - POST /artifact/byRegEx")
    print("  - GET /artifacts/list")
    print("  - GET /")
    print("\nValid auth token:")
    print(f"  {VALID_TOKEN}")
    print("\nTo test, run in another terminal:")
    print("  python tests/test_regex_live.py basic")
    print("  (Change SERVER_URL to http://localhost:8000 first)")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")