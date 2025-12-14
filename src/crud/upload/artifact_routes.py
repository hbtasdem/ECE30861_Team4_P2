"""Artifact management and registry endpoints - OpenAPI v3.4.4 BASELINE spec only.

FILE PURPOSE:
Implements artifact management endpoints that accept artifacts from URLs
and manage them in the registry using S3 storage.

S3 STORAGE STRUCTURE (Per Team Design):
  s3://phase2-s3-bucket/
    ├── model/{id}.json           - Model Artifact objects
    ├── dataset/{id}.json         - Dataset Artifact objects
    ├── code/{id}.json            - Code Artifact objects
    ├── rating/{id}.rate.json     - ModelRating objects (homemade)
    └── relations.json            - Relations table (homemade)

ENDPOINTS IMPLEMENTED:
1. POST /artifact/byRegEx - Query artifacts by regular expression
2. POST /artifact/{artifact_type} - Register new artifact from URL
3. GET /artifacts/{artifact_type}/{artifact_id} - Retrieve artifact by type and ID
4. PUT /artifacts/{artifact_type}/{artifact_id} - Update artifact source and metadata
5. POST /artifacts - Query/enumerate artifacts with filters
6. GET /artifacts - Get artifacts by name (query parameter)
7. DELETE /reset - Reset registry (admin only)
8. GET /artifact/{artifact_type}/{artifact_id}/cost - Get artifact cost in MB
9. GET /artifact/model/{artifact_id}/lineage - Get artifact lineage graph
10. POST /artifact/model/{artifact_id}/license-check - Check license compatibility
11. DELETE /artifacts/{artifact_type}/{artifact_id} - Delete artifact

ENVELOPE STRUCTURE (Per Spec Section 3.2.1):
All responses follow:
{
    "metadata": {"name": str, "id": str (ULID), "type": "model|dataset|code"},
    "data": {"url": str, "download_url": str (read-only)}
}
"""


import json
import re
import requests
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session
from ulid import ULID

from src.crud.rate_route import rateOnUpload
from src.crud.upload.artifacts import Artifact, ArtifactData, ArtifactMetadata, ArtifactQuery, ArtifactRegEx, ArtifactLineageGraph
from src.crud.upload.auth import get_current_user
from src.crud.upload.download_artifact import get_download_url
from src.database import get_db
from src.database_models import Artifact as ArtifactModel
from src.database_models import AuditEntry
from src.metrics.license_check import license_check

router = APIRouter(tags=["artifacts"])

# S3 Configuration
BUCKET_NAME = "phase2-s3-bucket"
s3_client = boto3.client("s3")

def try_fetch_readme_from_url(url: str) -> Optional[str]:
    if "huggingface.co/" not in url:
        return None
    try:
        model_id = url.split("huggingface.co/")[-1].split("/tree")[0]
        readme_url = f"https://huggingface.co/{model_id}/resolve/main/README.md"
        resp = requests.get(readme_url, timeout=5)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def _get_artifact_key(artifact_type: str, artifact_id: str) -> str:
    """Get S3 key for artifact object."""
    return f"{artifact_type}/{artifact_id}.json"


def _get_artifacts_by_type(artifact_type: str) -> List[Dict[str, Any]]:
    """List all artifacts of a given type from S3."""
    artifacts = []
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=f"{artifact_type}/")

        for page in pages:
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                key = obj["Key"]
                if key.endswith(".json") and not key.endswith(".rate.json"):
                    try:
                        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
                        artifact_data = json.loads(
                            response["Body"].read().decode("utf-8")
                        )
                        artifacts.append(artifact_data)
                    except Exception:
                        pass
    except ClientError:
        pass

    return artifacts


# ============================================================================
# POST /artifact/byRegEx - QUERY BY REGULAR EXPRESSION (BASELINE)
# ============================================================================
# CRITICAL: This MUST come BEFORE /artifact/{artifact_type} to avoid route conflicts!

@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
async def get_artifacts_by_regex(
    request: ArtifactRegEx,
    x_authorization: Optional[str] = Header(None),
) -> List[ArtifactMetadata]:
    """Search for artifacts using regular expression over artifact names.
    
    Args:
        request: Request body with regex pattern (ArtifactRegEx schema)
        x_authorization: Bearer token for authentication
    
    Returns:
        List[ArtifactMetadata]: Matching artifacts (name, id, type only)
    
    Raises:
        HTTPException: 400 if invalid regex, 403 if auth fails, 404 if no matches
    """
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )
    
    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )
    
    try:
        regex_pattern = re.compile(request.regex, re.IGNORECASE)
    except re.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid",
        )

    matching = []
    for artifact_type in ["model", "dataset", "code"]:
        artifacts = _get_artifacts_by_type(artifact_type)
        for artifact in artifacts:
            name = artifact["metadata"]["name"]
            url = artifact.get("data", {}).get("url", "")
            matched = False

            # Match name
            if regex_pattern.search(name):
                matched = True
            # Match README (models only)
            elif artifact["metadata"]["type"] == "model":
                readme_text = try_fetch_readme_from_url(url)
                if readme_text and regex_pattern.search(readme_text):
                    matched = True

            if matched:
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


# ============================================================================
# POST /artifact/{artifact_type} - CREATE ARTIFACT (BASELINE)
# ============================================================================

@router.post(
    "/artifact/{artifact_type}",
    response_model=Artifact,
    status_code=status.HTTP_201_CREATED,
)
async def create_artifact(
    artifact_type: str,
    artifact_data: ArtifactData,
    x_authorization: Optional[str] = Header(None),
) -> Artifact:
    """Create new artifact from source URL per spec."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    # Validate artifact type
    valid_types = {"model", "dataset", "code"}
    if artifact_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact type: {artifact_type}. "
            f"Must be one of: {', '.join(valid_types)}",
        )

    if not artifact_data.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Artifact data must contain 'url' field",
        )

    try:
        # Generate unique ID
        artifact_id = str(ULID())

        # Extract name from URL
        name = artifact_data.url.split("/")[-1]
        if not name or name.startswith("http"):
            name = f"{artifact_type}_{artifact_id[:8]}"

       # SENSITIVE MODEL
# need to figure out how to get the username from authentication
# is_sensitive = detect_malicious_patterns(name, artifact_data.url, artifact_id, is_sensitive)
# username = x_authorization
# if is_sensitive and artifact_type == "model":
#     log_sensitive_action(username, "upload", artifact_id)
#     check_sensitive_model(name, artifact_data.url, username)

        # RATE MODEL: if model ingestible will store rating in s3 and return True
        if artifact_type == "model":
            if not rateOnUpload(artifact_data.url, artifact_id):
                raise HTTPException(
                    status_code=424,
                    detail="Artifact is not registered due to the disqualified rating.",
                )

        # Get download_url
        download_url = get_download_url(artifact_data.url, artifact_id, artifact_type)

        # Create spec-compliant envelope
        artifact_envelope = {
            "metadata": {"name": name, "id": artifact_id, "type": artifact_type},
            "data": {"url": artifact_data.url, "download_url": download_url},
        }

        # Store in S3
        key = f"{artifact_type}/{artifact_id}.json"
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(artifact_envelope, indent=2),
            ContentType="application/json",
        )

        return artifact_envelope

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create artifact: {str(e)}",
        )


# ============================================================================
# GET /artifacts/{artifact_type}/{artifact_id} - RETRIEVE ARTIFACT (BASELINE)
# ============================================================================

@router.get("/artifacts/{artifact_type}/{artifact_id}", response_model=Artifact)
async def get_artifact(
    artifact_type: str,
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
) -> Artifact:
    """Retrieve artifact by type and ID per spec."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    try:
        key = f"{artifact_type}/{artifact_id}.json"
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        artifact_envelope = json.loads(response["Body"].read().decode("utf-8"))

        return artifact_envelope

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_type}/{artifact_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve artifact: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve artifact: {str(e)}",
        )


# ============================================================================
# PUT /artifacts/{artifact_type}/{artifact_id} - UPDATE ARTIFACT (BASELINE)
# ============================================================================

@router.put("/artifacts/{artifact_type}/{artifact_id}", response_model=Artifact)
async def update_artifact(
    artifact_type: str,
    artifact_id: str,
    artifact_data: ArtifactData,
    x_authorization: Optional[str] = Header(None),
) -> Artifact:
    """Update artifact metadata and source URL per spec."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    try:
        key = _get_artifact_key(artifact_type, artifact_id)

        # Get existing artifact
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        artifact_envelope = json.loads(response["Body"].read().decode("utf-8"))

        # Update URL
        if artifact_data.url:
            artifact_envelope["data"]["url"] = artifact_data.url
            # Update name if derived from URL
            name = artifact_data.url.split("/")[-1]
            if name and not name.startswith("http"):
                artifact_envelope["metadata"]["name"] = name

        # Save back to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(artifact_envelope, indent=2),
            ContentType="application/json",
        )

        return Artifact(
            metadata=ArtifactMetadata(
                name=artifact_envelope["metadata"]["name"],
                id=artifact_envelope["metadata"]["id"],
                type=artifact_envelope["metadata"]["type"],
            ),
            data=ArtifactData(
                url=artifact_envelope["data"]["url"],
                download_url=artifact_envelope["data"]["download_url"],
            ),
        )

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_type}/{artifact_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update artifact: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update artifact: {str(e)}",
        )


# ============================================================================
# POST /artifacts - QUERY/ENUMERATE ARTIFACTS (BASELINE)
# ============================================================================

@router.post("/artifacts", response_model=List[ArtifactMetadata])
async def enumerate_artifacts(
    queries: List[ArtifactQuery],
    offset: Optional[int] = Query(None),
    x_authorization: Optional[str] = Header(None),
) -> List[ArtifactMetadata]:
    """Query and enumerate artifacts per spec."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    if not queries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one query is required",
        )

    try:
        offset_int = offset if offset is not None else 0
        page_size = 100

        results = []
        seen_ids = set()

        # Check if S3 is empty for all types
        s3_empty = True
        for artifact_type in ["model", "dataset", "code"]:
            artifacts = _get_artifacts_by_type(artifact_type)
            if artifacts:
                s3_empty = False
        if s3_empty:
            return []

        for query in queries:
            # Determine types to search
            types_to_search = (
                query.types if query.types else ["model", "dataset", "code"]
            )

            for artifact_type in types_to_search:
                artifacts = _get_artifacts_by_type(artifact_type)

                # Filter by name if not wildcard
                if query.name != "*":
                    artifacts = [
                        a
                        for a in artifacts
                        if query.name.lower() in a["metadata"]["name"].lower()
                    ]

                # Add to results, avoiding duplicates
                for artifact in artifacts:
                    artifact_id = artifact["metadata"]["id"]
                    if artifact_id not in seen_ids:
                        seen_ids.add(artifact_id)
                        results.append(artifact)

        # Apply pagination
        paginated_results = results[offset_int:offset_int + page_size]

        # Convert to metadata
        metadata_list = [
            ArtifactMetadata(
                name=artifact["metadata"]["name"],
                id=artifact["metadata"]["id"],
                type=artifact["metadata"]["type"],
            )
            for artifact in paginated_results
        ]

        return metadata_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query failed: {str(e)}",
        )


# ============================================================================
# GET /artifacts - GET ARTIFACTS BY NAME (QUERY PARAMETER)
# ============================================================================

@router.get("/artifacts", response_model=List[ArtifactMetadata])
async def get_artifacts_by_name(
    name: str = Query(..., description="Artifact name to search for"),
    x_authorization: Optional[str] = Header(None),
) -> List[ArtifactMetadata]:
    """Get artifacts by name using query parameter.
    
    Args:
        name: Artifact name to search for (exact match)
        x_authorization: Bearer token for authentication
    
    Returns:
        List[ArtifactMetadata]: Matching artifacts
    
    Raises:
        HTTPException: 403 if auth fails, 404 if no matches
    """
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )
    
    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )
    
    # Search across all types for exact name match
    matching = []
    for artifact_type in ["model", "dataset", "code"]:
        artifacts = _get_artifacts_by_type(artifact_type)
        
        for artifact in artifacts:
            if artifact["metadata"]["name"] == name:  # Exact match
                matching.append(
                    ArtifactMetadata(
                        name=artifact["metadata"]["name"],
                        id=artifact["metadata"]["id"],
                        type=artifact["metadata"]["type"],
                    )
                )
    
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with name '{name}' not found.",
        )
    
    return matching


# ============================================================================
# DELETE /reset - RESET REGISTRY (BASELINE)
# ============================================================================

@router.delete("/reset")
async def reset_registry(
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Reset the registry to system default state (admin only)."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        current_user = get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to reset the registry",
        )

    try:
        # Delete all artifacts from S3
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=BUCKET_NAME)

        for page in pages:
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])

        # Delete all artifacts from database
        db.query(ArtifactModel).delete()

        # Delete all audit entries from database
        db.query(AuditEntry).delete()

        # Delete all users from database
        from src.database_models import User as DBUser
        db.query(DBUser).delete()

        # Recreate default admin user
        admin_username = "ece30861defaultadminuser"
        admin_password = "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
        from src.crud.upload.auth import hash_password
        hashed = hash_password(admin_password)
        admin_user = DBUser(
            username=admin_username,
            email="admin@registry.local",
            hashed_password=hashed,
            is_admin=True,
        )
        db.add(admin_user)

        # Commit the database changes
        db.commit()

        return {"message": "Registry is reset and default admin user recreated."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reset registry: {str(e)}",
        )


# ============================================================================
# GET /artifact/{artifact_type}/{artifact_id}/cost - GET ARTIFACT COST
# ============================================================================

@router.get("/artifact/{artifact_type}/{artifact_id}/cost")
async def get_artifact_cost(
    artifact_type: str,
    artifact_id: str,
    dependency: bool = Query(False),
    x_authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Get the cost of an artifact and optionally its dependencies."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    try:
        # Get artifact metadata
        key = _get_artifact_key(artifact_type, artifact_id)
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        artifact_envelope = json.loads(response["Body"].read().decode("utf-8"))
        artifact_url = artifact_envelope["data"]["url"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact does not exist.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve artifact: {str(e)}",
        )

    # Calculate artifact size in MB
    try:
        from src.size_cost import get_model_size_gb

        # Extract model ID from URL
        model_id = artifact_url
        if "huggingface.co/" in artifact_url:
            parts = artifact_url.split("huggingface.co/")[-1].split("/")
            if len(parts) >= 2:
                model_id = f"{parts[0]}/{parts[1]}"

        # Get size in GB, convert to MB
        size_gb = get_model_size_gb(model_id)
        size_mb = round(size_gb * 1024, 2)
    except Exception:
        # Fallback to default size if calculation fails
        size_mb = 100.0

    # Build response per spec
    if not dependency:
        cost_data = {artifact_id: {"total_cost": size_mb}}
    else:
        # Get dependencies from lineage (if available)
        dependencies = {}
        try:
            from src.lineage_tree import extract_lineage_graph

            lineage = extract_lineage_graph(artifact_url, artifact_id)

            # Calculate cost for each dependency node
            for node in lineage.get("nodes", []):
                dep_id = node.get("artifact_id")
                if dep_id and dep_id != artifact_id:
                    try:
                        dep_key = f"model/{dep_id}.json"
                        dep_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=dep_key)
                        dep_envelope = json.loads(dep_response["Body"].read().decode("utf-8"))
                        dep_url = dep_envelope["data"]["url"]

                        dep_model_id = dep_url
                        if "huggingface.co/" in dep_url:
                            parts = dep_url.split("huggingface.co/")[-1].split("/")
                            if len(parts) >= 2:
                                dep_model_id = f"{parts[0]}/{parts[1]}"

                        dep_size_gb = get_model_size_gb(dep_model_id)
                        dep_size_mb = round(dep_size_gb * 1024, 2)

                        dependencies[dep_id] = {
                            "standalone_cost": dep_size_mb,
                            "total_cost": dep_size_mb
                        }
                    except Exception:
                        pass
        except Exception:
            pass

        # Calculate total_cost
        total_cost = size_mb + sum(dep.get("total_cost", 0) for dep in dependencies.values())

        cost_data = {
            artifact_id: {
                "standalone_cost": size_mb,
                "total_cost": total_cost
            }
        }
        cost_data.update(dependencies)

    return cost_data


# ============================================================================
# GET /artifact/model/{artifact_id}/lineage - GET ARTIFACT LINEAGE
# ============================================================================

@router.get(
    "/artifact/model/{artifact_id}/lineage", response_model=ArtifactLineageGraph
)
async def get_artifact_lineage(
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
) -> ArtifactLineageGraph:
    """Retrieve the lineage graph for an artifact."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    try:
        # Get artifact
        key = _get_artifact_key("model", artifact_id)
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        artifact_envelope = json.loads(response["Body"].read().decode("utf-8"))
        artifact_url = artifact_envelope["data"]["url"]

        # Extract lineage graph
        from src.lineage_tree import extract_lineage_graph

        lineage = extract_lineage_graph(artifact_url, artifact_id)
        return lineage

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: model/{artifact_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve artifact: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get lineage: {str(e)}",
        )


# ============================================================================
# POST /artifact/model/{artifact_id}/license-check - LICENSE COMPATIBILITY
# ============================================================================

@router.post("/artifact/model/{artifact_id}/license-check")
async def check_license_compatibility(
    artifact_id: str,
    request_body: Dict[str, Any],
    x_authorization: Optional[str] = Header(None),
) -> bool:
    """Assess license compatibility for fine-tune and inference usage."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    # Validate request body
    if "github_url" not in request_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The license check request is malformed or references an unsupported usage context.",
        )

    github_url = request_body.get("github_url")
    if not github_url or not isinstance(github_url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The license check request is malformed or references an unsupported usage context.",
        )

    # Verify artifact exists
    try:
        key = _get_artifact_key("model", artifact_id)
        s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The artifact or GitHub project could not be found.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="External license information could not be retrieved.",
        )

    return license_check(github_url, artifact_id)


# ============================================================================
# DELETE /artifacts/{artifact_type}/{artifact_id} - DELETE ARTIFACT
# ============================================================================

@router.delete("/artifacts/{artifact_type}/{artifact_id}")
async def delete_artifact(
    artifact_type: str,
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
) -> Dict[str, str]:
    """Delete an artifact from the registry."""
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, None)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    try:
        # Delete from S3
        key = _get_artifact_key(artifact_type, artifact_id)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)

        # Also delete downloads folder
        downloads_prefix = f"downloads/{artifact_id}/"
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=downloads_prefix)

        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])

        # Delete rating if exists
        try:
            rating_key = f"rating/{artifact_id}.rate.json"
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=rating_key)
        except:
            pass

        return {"message": f"Artifact {artifact_id} deleted successfully"}

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_type}/{artifact_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete artifact: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete artifact: {str(e)}",
        )