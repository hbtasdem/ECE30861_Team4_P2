"""Artifact management and registry endpoints - OpenAPI v3.4.4 BASELINE spec only.

FILE PURPOSE:
Implements 9 BASELINE artifact management endpoints that accept artifacts from URLs
and manage them in the registry using S3 storage. All requests require URL-based
artifact sources with no file uploads accepted.

S3 STORAGE STRUCTURE (Per Team Design):
  s3://phase2-s3-bucket/
    ├── model/{id}.json           - Model Artifact objects
    ├── dataset/{id}.json         - Dataset Artifact objects
    ├── code/{id}.json            - Code Artifact objects
    ├── rating/{id}.rate.json     - ModelRating objects (homemade)
    └── relations.json            - Relations table (homemade)

ENDPOINTS IMPLEMENTED (9 BASELINE):
1. POST /artifact/{artifact_type} - Register new artifact from URL
2. GET /artifacts/{artifact_type}/{artifact_id} - Retrieve artifact by type and ID
3. PUT /artifacts/{artifact_type}/{artifact_id} - Update artifact source and metadata
4. POST /artifacts - Query/enumerate artifacts with filters
5. DELETE /reset - Reset registry (admin only)
6. GET /artifact/{artifact_type}/{artifact_id}/cost - Get artifact cost in MB
7. GET /artifact/model/{artifact_id}/lineage - Get artifact lineage graph
8. POST /artifact/model/{artifact_id}/license-check - Check license compatibility
9. POST /artifact/byRegEx - Query artifacts by regular expression

ENVELOPE STRUCTURE (Per Spec Section 3.2.1):
All responses follow:
{
    "metadata": {"name": str, "id": str (ULID), "type": "model|dataset|code"},
    "data": {"url": str, "download_url": str (read-only)}
}
"""

import json
import re
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Header, HTTPException, Query, status
from ulid import ULID

from src.crud.rate_route import rateOnUpload
from src.crud.upload.artifacts import (Artifact, ArtifactData,
                                       ArtifactLineageGraph,
                                       ArtifactLineageNode, ArtifactMetadata,
                                       ArtifactQuery, ArtifactRegEx)
from src.crud.upload.auth import get_current_user
from src.crud.upload.download_artifact import get_download_url
from src.metrics.license_check import license_check

# from src.database import get_db
# from src.database_models import Artifact as ArtifactModel
# from src.database_models import AuditEntry

router = APIRouter(tags=["artifacts"])

# S3 Configuration
BUCKET_NAME = "phase2-s3-bucket"
s3_client = boto3.client("s3")


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
# NOTE: This route MUST come BEFORE /artifact/{artifact_type} in the file
# because FastAPI matches routes in order. If this comes after, the parameterized
# route will match "/artifact/byRegEx" first, treating "byRegEx" as the artifact_type.


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
async def get_artifacts_by_regex(
    request: ArtifactRegEx,
    x_authorization: Optional[str] = Header(None),
) -> List[ArtifactMetadata]:
    """Search for artifacts using regular expression over names.

    Per OpenAPI v3.4.4 spec:
    - Searches artifact names
    - Similar to search by name but using regex
    - Returns 404 if no artifacts found

    Args:
        request: Request body with regex pattern
        x_authorization: Bearer token for authentication

    Returns:
        List[ArtifactMetadata]: Matching artifacts

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

    # Validate regex pattern for DoS protection
    regex_str = request.regex

    # Check for malicious patterns (ReDoS)
    # Detect catastrophic backtracking patterns
    dangerous_patterns = [
        r"\(.*\+.*\)\+",  # Nested quantifiers like (a+)+
        r"\(.*\*.*\)\*",  # Nested quantifiers like (a*)*
        r"\(.*\+.*\)\*",  # Mixed nested quantifiers
        r"\(.*\{.*,.*\}.*\)\+",  # Nested bounded quantifiers
        r"(\(.*\|.*){3,}",  # Excessive alternation
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, regex_str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "There is missing field(s) in the artifact_regex "
                    "or it is formed improperly, or is invalid: "
                    "Potentially malicious regex pattern detected (ReDoS risk)"
                ),
            )

    # Limit regex complexity
    if len(regex_str) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "There is missing field(s) in the artifact_regex "
                "or it is formed improperly, or is invalid: "
                "Regex pattern too long (max 200 characters)"
            ),
        )

    try:
        regex_pattern = re.compile(regex_str, re.IGNORECASE)
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid: {str(e)}",
        )

    # Search artifacts across all types
    matching = []
    for artifact_type in ["model", "dataset", "code"]:
        artifacts = _get_artifacts_by_type(artifact_type)
        for artifact in artifacts:
            if regex_pattern.search(artifact["metadata"]["name"]):
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
    """Create new artifact from source URL per spec.

    Per OpenAPI v3.4.4 spec:
    - Registers a new artifact by providing a downloadable source URL
    - Artifacts may share a name; refer to id as unique identifier
    - Returns HTTP 201 Created with full Artifact envelope

    Args:
        artifact_type: Artifact type (model, dataset, or code)
        artifact_data: Request body with source URL
        x_authorization: Bearer token for authentication

    Returns:
        Artifact: Full artifact with generated id and download_url

    Raises:
        HTTPException: 400 if invalid type, 403 if auth fails, 409 if duplicate
    """
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    # georgia: commenting this out until it works, so upload not dependent

    # if not x_authorization:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Missing X-Authorization header",
    #     )

    # try:
    #     get_current_user(x_authorization, None)
    # except HTTPException:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Authentication failed: Invalid or expired token",
    #     )

    # ========================================================================
    # VALIDATION
    # ========================================================================
    # Validate artifact type (reject reserved keywords)
    if artifact_type == "byRegEx":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid artifact type: 'byRegEx' is a reserved keyword. "
            "Use POST /artifact/byRegEx endpoint for regex searches.",
        )

    valid_types = {"model", "dataset", "code"}
    if artifact_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact type: {artifact_type}. "
            f"Must be one of: {', '.join(valid_types)}",
        )

    # Validate artifact data
    if not artifact_data.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Artifact data must contain 'url' field",
        )

    # ========================================================================
    # CREATE ARTIFACT IN S3
    # ========================================================================
    try:
        # Generate unique ID
        artifact_id = str(ULID())

        # RATE MODEL: if model ingestible will store rating in s3 and return True
        if artifact_type == "model":
            if not rateOnUpload(artifact_data.url, artifact_id):
                raise HTTPException(
                    status_code=424,
                    detail="Artifact is not registered due to the disqualified rating.",
                )

        # Get download_url
        download_url = get_download_url(artifact_data.url, artifact_id, artifact_type)

        # Extract name from URL
        name = artifact_data.url.split("/")[-1]
        if not name or name.startswith("http"):
            name = f"{artifact_type}_{artifact_id[:8]}"

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
    """Retrieve artifact by type and ID per spec.

    Per OpenAPI v3.4.4 spec:
    - Returns the artifact with specified type and ID
    - Returns 404 if artifact not found

    Args:
        artifact_type: Artifact type (model, dataset, or code)
        artifact_id: Unique artifact identifier
        x_authorization: Bearer token for authentication

    Returns:
        Artifact: Full artifact envelope with metadata and data

    Raises:
        HTTPException: 403 if auth fails, 404 if not found
    """
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    # georgia commenting out for now
    # if not x_authorization:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Missing X-Authorization header",
    #     )

    # try:
    #     get_current_user(x_authorization, None)
    # except HTTPException:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Authentication failed: Invalid or expired token",
    #     )

    # ========================================================================
    # RETRIEVE ARTIFACT FROM S3
    # ========================================================================
    try:
        key = f"{artifact_type}/{artifact_id}.json"
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        artifact_envelope = json.loads(response["Body"].read().decode("utf-8"))

        return artifact_envelope
        # Artifact(
        #     metadata=ArtifactMetadata(
        #         name=artifact_envelope["metadata"]["name"],
        #         id=artifact_envelope["metadata"]["id"],
        #         type=artifact_envelope["metadata"]["type"],
        #     ),
        #     data=ArtifactData(
        #         url=artifact_envelope["data"]["url"],
        #         download_url=artifact_envelope["data"]["download_url"],
        #     ),
        # )

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
    """Update artifact metadata and source URL per spec.

    Per OpenAPI v3.4.4 spec:
    - Updates the artifact source (from artifact_data)
    - Returns 404 if artifact not found

    Args:
        artifact_type: Artifact type (model, dataset, or code)
        artifact_id: Unique artifact identifier
        artifact_data: New artifact data (url and optional download_url)
        x_authorization: Bearer token for authentication

    Returns:
        Artifact: Updated artifact envelope

    Raises:
        HTTPException: 403 if auth fails, 404 if not found
    """
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
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

    # ========================================================================
    # RETRIEVE AND UPDATE ARTIFACT IN S3
    # ========================================================================
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
# DELETE /artifacts/{artifact_type}/{artifact_id} - DELETE ARTIFACT (BASELINE)
# ============================================================================


@router.delete("/artifacts/{artifact_type}/{artifact_id}")
async def delete_artifact(
    artifact_type: str,
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
) -> Dict[str, str]:
    """Delete artifact by type and ID per spec.

    Per OpenAPI v3.4.7 spec:
    - Deletes the artifact with specified type and ID
    - Returns 200 if successful
    - Returns 404 if artifact not found

    Args:
        artifact_type: Artifact type (model, dataset, or code)
        artifact_id: Unique artifact identifier
        x_authorization: Bearer token for authentication

    Returns:
        Dict with success message

    Raises:
        HTTPException: 400 if invalid, 403 if auth fails, 404 if not found
    """
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
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

    # ========================================================================
    # VALIDATION
    # ========================================================================
    valid_types = {"model", "dataset", "code"}
    if artifact_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the artifact_type or artifact_id or invalid",
        )

    # ========================================================================
    # DELETE ARTIFACT FROM S3
    # ========================================================================
    try:
        key = _get_artifact_key(artifact_type, artifact_id)

        # Check if artifact exists first
        try:
            s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
        except ClientError as client_err:
            if client_err.response["Error"]["Code"] == "404":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Artifact does not exist.",
                )
            raise

        # Delete the artifact
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)

        return {
            "message": f"Artifact {artifact_type}/{artifact_id} deleted successfully"
        }

    except HTTPException:
        raise
    except ClientError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the artifact_type or artifact_id or invalid",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the artifact_type or artifact_id or invalid",
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
    """Query and enumerate artifacts per spec.

    Per OpenAPI v3.4.4 spec:
    - Request body is array of ArtifactQuery objects
    - Each query specifies name pattern and optional type filters
    - Multiple queries are OR'd together
    - Returns ArtifactMetadata array (just name, id, type)
    - Supports pagination via offset parameter

    Args:
        queries: Array of ArtifactQuery objects with filters
        offset: Pagination offset (default 0)
        x_authorization: Bearer token for authentication

    Returns:
        List[ArtifactMetadata]: Array of matching artifacts

    Raises:
        HTTPException: 400 if invalid query, 403 if auth fails
    """
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    # if not x_authorization:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Missing X-Authorization header",
    #     )

    # try:
    #     get_current_user(x_authorization, None)
    # except HTTPException:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Authentication failed: Invalid or expired token",
    #     )

    # ========================================================================
    # VALIDATION
    # ========================================================================
    if not queries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one query is required",
        )

    # ========================================================================
    # BUILD QUERY FROM S3
    # ========================================================================
    try:
        offset_int = offset if offset is not None else 0
        page_size = 100

        results = []
        seen_ids = set()

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
        paginated_results = results[offset_int: offset_int + page_size]

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
# DELETE /reset - RESET REGISTRY (BASELINE)
# ============================================================================


@router.delete("/reset")
async def reset_registry(
    x_authorization: Optional[str] = Header(None),
) -> Dict[str, str]:
    """Reset the registry to system default state (admin only).

    Per OpenAPI v3.4.4 spec:
    - Requires admin authorization
    - Deletes all artifacts
    - Returns 200 on success, 401 if not admin

    Args:
        x_authorization: Bearer token for authentication

    Returns:
        Dict with success message

    Raises:
        HTTPException: 401 if not admin, 403 if auth fails
    """
    # if not x_authorization:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Missing X-Authorization header",
    #     )

    # try:
    #     current_user = get_current_user(x_authorization, None)
    # except HTTPException:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Authentication failed: Invalid or expired token",
    #     )

    # Check if user is admin
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="You do not have permission to reset the registry",
    #     )

    try:
        # Delete all artifacts
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=BUCKET_NAME)

        for page in pages:
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])

        return {"message": "Registry is reset."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reset registry: {str(e)}",
        )


# ============================================================================
# GET /artifact/{artifact_type}/{artifact_id}/cost - GET ARTIFACT COST (BASELINE)
# ============================================================================


@router.get("/artifact/{artifact_type}/{artifact_id}/cost")
async def get_artifact_cost(
    artifact_type: str,
    artifact_id: str,
    dependency: bool = Query(False),
    x_authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Get the cost of an artifact and optionally its dependencies.

    Per OpenAPI v3.4.4 spec:
    - Returns cost in MB (download size)
    - Includes dependency costs if dependency=true
    - Returns 404 if artifact not found

    Args:
        artifact_type: Artifact type (model, dataset, or code)
        artifact_id: Unique artifact identifier
        dependency: Include dependency costs (default: False)
        x_authorization: Bearer token for authentication

    Returns:
        Dict with cost information

    Raises:
        HTTPException: 403 if auth fails, 404 if not found
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
        key = _get_artifact_key(artifact_type, artifact_id)
        s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
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

    # For now, return placeholder cost
    cost_data = {artifact_id: {"total_cost": 100.0}}

    if dependency:
        cost_data[artifact_id]["standalone_cost"] = 100.0

    return cost_data


# ============================================================================
# GET /artifact/model/{artifact_id}/lineage - GET ARTIFACT LINEAGE (BASELINE)
# ============================================================================


@router.get(
    "/artifact/model/{artifact_id}/lineage", response_model=ArtifactLineageGraph
)
async def get_artifact_lineage(
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
) -> ArtifactLineageGraph:
    """Retrieve the lineage graph for an artifact.

    Per OpenAPI v3.4.4 spec:
    - Returns lineage graph extracted from structured metadata
    - Returns 404 if artifact not found

    Args:
        artifact_id: Unique artifact identifier
        x_authorization: Bearer token for authentication

    Returns:
        ArtifactLineageGraph with nodes and edges

    Raises:
        HTTPException: 403 if auth fails, 404 if not found
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
        key = _get_artifact_key("model", artifact_id)
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        artifact_envelope = json.loads(response["Body"].read().decode("utf-8"))

        # For now, return self as a single node with no edges
        nodes = [
            ArtifactLineageNode(
                artifact_id=artifact_id,
                name=artifact_envelope["metadata"]["name"],
                source="metadata",
            )
        ]

        return ArtifactLineageGraph(nodes=nodes, edges=[])

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact does not exist.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve artifact: {str(e)}",
        )


# ============================================================================
# POST /artifact/model/{artifact_id}/license-check - LICENSE COMPATIBILITY (BASELINE)
# ============================================================================


@router.post("/artifact/model/{artifact_id}/license-check")
async def check_license_compatibility(
    artifact_id: str,
    request_body: Dict[str, Any],
    x_authorization: Optional[str] = Header(None),
) -> bool:
    """Assess license compatibility for fine-tune and inference usage.

    Per OpenAPI v3.4.4 spec:
    - Takes github_url in request body
    - Evaluates GitHub project license
    - Returns JSON with boolean compatibility status
    - Returns 404 if artifact/GitHub project not found
    - Returns 502 if external license info unavailable

    Args:
        artifact_id: Unique model artifact identifier
        request_body: Request body with github_url
        x_authorization: Bearer token for authentication

    Returns:
        Dict with boolean license compatibility result

    Raises:
        HTTPException: 400 if malformed, 403 if auth fails, 404 if not found, 502 if external error
    """
    # if not x_authorization:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Authentication failed due to invalid or missing AuthenticationToken.",
    #     )

    # try:
    #     get_current_user(x_authorization, None)
    # except HTTPException:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Authentication failed due to invalid or missing AuthenticationToken.",
    #     )

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
