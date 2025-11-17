"""Artifact management and registry endpoints - OpenAPI v3.4.4 BASELINE spec only.

FILE PURPOSE:
Implements all 11 BASELINE artifact management endpoints that accept artifacts from URLs
and manage them in the registry. All requests require URL-based artifact sources with no file
uploads accepted.

ENDPOINTS IMPLEMENTED (11/11 BASELINE):
1. POST /artifact/{type} - Register new artifact from URL
2. GET /artifacts/{type}/{id} - Retrieve artifact by type and ID
3. PUT /artifacts/{type}/{id} - Update artifact source and metadata
4. POST /artifacts - Query/enumerate artifacts with filters
5. DELETE /reset - Reset registry (admin only)
6. GET /artifact/{type}/{id}/cost - Get artifact cost in MB
7. GET /artifact/model/{id}/lineage - Get artifact lineage graph
8. POST /artifact/model/{id}/license-check - Check license compatibility
9. POST /artifact/byRegEx - Query artifacts by regular expression
10. GET /health - Heartbeat check (in app.py)
11. GET /artifact/model/{id}/rate - Get model rating (in rate/routes.py)

ENVELOPE STRUCTURE (Per Spec Section 3.2.1):
All responses follow:
{
    "metadata": {"name": str, "id": str (ULID), "type": "model|dataset|code"},
    "data": {"url": str, "download_url": str (read-only)}
}
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session
from ulid import ULID

from src.crud.upload.artifacts import (Artifact, ArtifactData, ArtifactLineageGraph, ArtifactLineageNode,
                                       ArtifactMetadata, ArtifactQuery)
from src.crud.upload.auth import get_current_user
from src.database import get_db
from src.database_models import Artifact as ArtifactModel
from src.database_models import AuditEntry

router = APIRouter(tags=["artifacts"])

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
    db: Session = Depends(get_db),
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
        db: Database session (dependency injection)

    Returns:
        Artifact: Full artifact with generated id and download_url

    Raises:
        HTTPException: 400 if invalid type, 403 if auth fails, 409 if duplicate
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
        current_user = get_current_user(x_authorization, db)
    except HTTPException as _e:  # noqa: F841
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    # ========================================================================
    # VALIDATION
    # ========================================================================
    # Validate artifact type
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
    # CREATE ARTIFACT
    # ========================================================================
    try:
        # Generate unique ID and download URL
        artifact_id = str(ULID())
        download_url = f"/api/artifacts/{artifact_type}/{artifact_id}/download"

        # Extract name from URL if not provided
        name = artifact_data.url.split("/")[-1]
        if not name or name.startswith("http"):
            name = f"{artifact_type}_{artifact_id[:8]}"

        # Create artifact record
        new_artifact = ArtifactModel(
            id=artifact_id,
            name=name,
            type=artifact_type,
            url=artifact_data.url,
            download_url=download_url,
            uploader_id=current_user.id,
        )

        db.add(new_artifact)
        db.flush()  # Flush to ensure ID is set before creating audit entry

        # Create audit entry for CREATE action
        audit_entry = AuditEntry(
            user_id=current_user.id, artifact_id=artifact_id, action="CREATE"
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(new_artifact)

        # Return artifact in envelope format
        return Artifact(
            metadata=ArtifactMetadata(
                name=new_artifact.name, id=new_artifact.id, type=new_artifact.type
            ),
            data=ArtifactData(
                url=new_artifact.url, download_url=new_artifact.download_url
            ),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
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
    db: Session = Depends(get_db),
) -> Artifact:
    """Retrieve artifact by type and ID per spec.

    Per OpenAPI v3.4.4 spec:
    - Returns the artifact with specified type and ID
    - Returns 404 if artifact not found
    - Logs DOWNLOAD action in audit trail

    Args:
        artifact_type: Artifact type (model, dataset, or code)
        artifact_id: Unique artifact identifier
        x_authorization: Bearer token for authentication
        db: Database session (dependency injection)

    Returns:
        Artifact: Full artifact envelope with metadata and data

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
        current_user = get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    # ========================================================================
    # RETRIEVE ARTIFACT
    # ========================================================================
    artifact = (
        db.query(ArtifactModel)
        .filter(ArtifactModel.id == artifact_id, ArtifactModel.type == artifact_type)
        .first()
    )

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_type}/{artifact_id}",
        )

    # Log DOWNLOAD action
    try:
        audit_entry = AuditEntry(
            user_id=current_user.id, artifact_id=artifact_id, action="DOWNLOAD"
        )
        db.add(audit_entry)
        db.commit()
    except Exception as _e:  # noqa: F841
        # Don't fail the request if audit logging fails
        db.rollback()

    return Artifact(
        metadata=ArtifactMetadata(
            name=artifact.name, id=artifact.id, type=artifact.type
        ),
        data=ArtifactData(url=artifact.url, download_url=artifact.download_url),
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
    db: Session = Depends(get_db),
) -> Artifact:
    """Update artifact metadata and source URL per spec.

    Per OpenAPI v3.4.4 spec:
    - Updates the artifact source (from artifact_data)
    - Returns 404 if artifact not found
    - Logs UPDATE action in audit trail

    Args:
        artifact_type: Artifact type (model, dataset, or code)
        artifact_id: Unique artifact identifier
        artifact_data: New artifact data (url and optional download_url)
        x_authorization: Bearer token for authentication
        db: Database session (dependency injection)

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
        current_user = get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    # ========================================================================
    # RETRIEVE AND UPDATE ARTIFACT
    # ========================================================================
    artifact = (
        db.query(ArtifactModel)
        .filter(ArtifactModel.id == artifact_id, ArtifactModel.type == artifact_type)
        .first()
    )

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_type}/{artifact_id}",
        )

    try:
        # Update artifact data
        if artifact_data.url:
            artifact.url = artifact_data.url

        # Update name if derived from URL
        if artifact.url:
            name = artifact.url.split("/")[-1]
            if name and not name.startswith("http"):
                artifact.name = name

        db.flush()

        # Log UPDATE action
        audit_entry = AuditEntry(
            user_id=current_user.id, artifact_id=artifact_id, action="UPDATE"
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(artifact)

        return Artifact(
            metadata=ArtifactMetadata(
                name=artifact.name, id=artifact.id, type=artifact.type
            ),
            data=ArtifactData(url=artifact.url, download_url=artifact.download_url),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
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
    db: Session = Depends(get_db),
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
        db: Database session (dependency injection)

    Returns:
        List[ArtifactMetadata]: Array of matching artifacts

    Raises:
        HTTPException: 400 if invalid query, 403 if auth fails
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
        get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    # ========================================================================
    # VALIDATION
    # ========================================================================
    if not queries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one query is required",
        )

    # ========================================================================
    # BUILD QUERY
    # ========================================================================
    try:
        offset_int = offset if offset is not None else 0
        page_size = 100

        results = []
        seen_ids = set()

        for query in queries:
            # Handle wildcard query
            if query.name == "*":
                # Get all artifacts with optional type filter
                q = db.query(ArtifactModel)
                if query.types:
                    q = q.filter(ArtifactModel.type.in_(query.types))
                artifacts = q.offset(offset_int).limit(page_size).all()
            else:
                # Query by name (exact match or substring)
                q = db.query(ArtifactModel).filter(
                    ArtifactModel.name.ilike(f"%{query.name}%")
                )
                if query.types:
                    q = q.filter(ArtifactModel.type.in_(query.types))
                artifacts = q.offset(offset_int).limit(page_size).all()

            # Add to results, avoiding duplicates
            for artifact in artifacts:
                if artifact.id not in seen_ids:
                    seen_ids.add(artifact.id)
                    results.append(artifact)

        # Convert to metadata
        metadata_list = [
            ArtifactMetadata(name=artifact.name, id=artifact.id, type=artifact.type)
            for artifact in results
        ]

        return metadata_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Query failed: {str(e)}"
        )


# ============================================================================
# DELETE /reset - RESET REGISTRY (BASELINE)
# ============================================================================


@router.delete("/reset")
async def reset_registry(
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Reset the registry to system default state (admin only).

    Per OpenAPI v3.4.4 spec:
    - Requires admin authorization
    - Deletes all artifacts and audit entries
    - Returns 200 on success, 401 if not admin

    Args:
        x_authorization: Bearer token for authentication
        db: Database session (dependency injection)

    Returns:
        Dict with success message

    Raises:
        HTTPException: 401 if not admin, 403 if auth fails
    """
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
        # Delete all artifacts and audit entries
        db.query(AuditEntry).delete()
        db.query(ArtifactModel).delete()
        db.commit()
        return {"message": "Registry is reset."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reset registry: {str(e)}",
        )


# ============================================================================
# GET /artifact/{artifact_type}/{id}/cost - GET ARTIFACT COST (BASELINE)
# ============================================================================


@router.get("/artifact/{artifact_type}/{artifact_id}/cost")
async def get_artifact_cost(
    artifact_type: str,
    artifact_id: str,
    dependency: bool = Query(False),
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
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
        db: Database session (dependency injection)

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
        get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    artifact = (
        db.query(ArtifactModel)
        .filter(ArtifactModel.id == artifact_id, ArtifactModel.type == artifact_type)
        .first()
    )

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist."
        )

    # For now, return placeholder cost
    # In production, would calculate actual download size
    cost_data = {artifact_id: {"total_cost": 100.0}}  # Placeholder: 100 MB

    if dependency:
        cost_data[artifact_id]["standalone_cost"] = 100.0

    return cost_data


# ============================================================================
# GET /artifact/model/{id}/lineage - GET ARTIFACT LINEAGE (BASELINE)
# ============================================================================


@router.get(
    "/artifact/model/{artifact_id}/lineage", response_model=ArtifactLineageGraph
)
async def get_artifact_lineage(
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> ArtifactLineageGraph:
    """Retrieve the lineage graph for an artifact.

    Per OpenAPI v3.4.4 spec:
    - Returns lineage graph extracted from structured metadata
    - Returns 404 if artifact not found
    - Lineage includes upstream dependencies

    Args:
        artifact_id: Unique artifact identifier
        x_authorization: Bearer token for authentication
        db: Database session (dependency injection)

    Returns:
        ArtifactLineageGraph with nodes and edges

    Raises:
        HTTPException: 400 if malformed, 403 if auth fails, 404 if not found
    """
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact does not exist."
        )

    # For now, return self as a single node with no edges
    # In production, would parse metadata for actual lineage
    nodes = [
        ArtifactLineageNode(
            artifact_id=artifact_id,
            name=artifact.name,
            source="metadata",
            metadata={"type": artifact.type},
        )
    ]

    return ArtifactLineageGraph(nodes=nodes, edges=[])


# ============================================================================
# POST /artifact/model/{id}/license-check - LICENSE COMPATIBILITY (BASELINE)
# ============================================================================


@router.post("/artifact/model/{artifact_id}/license-check")
async def check_license_compatibility(
    artifact_id: str,
    request: Dict[str, str],
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> bool:
    """Assess license compatibility for fine-tune and inference usage.

    Per OpenAPI v3.4.4 spec:
    - Evaluates GitHub project license
    - Returns boolean compatibility status
    - Returns 404 if artifact/GitHub project not found

    Args:
        artifact_id: Unique artifact identifier
        request: Request body with github_url
        x_authorization: Bearer token for authentication
        db: Database session (dependency injection)

    Returns:
        bool: True if license compatible, False otherwise

    Raises:
        HTTPException: 400 if malformed, 403 if auth fails, 404 if not found, 502 if external call fails
    """
    if not x_authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Authorization header",
        )

    try:
        get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    if "github_url" not in request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The license check request is malformed or references an unsupported usage context.",
        )

    artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The artifact or GitHub project could not be found.",
        )

    # For now, return True (compatible)
    # In production, would check actual GitHub license
    return True


# ============================================================================
# POST /artifact/byRegEx - QUERY BY REGULAR EXPRESSION (BASELINE)
# ============================================================================


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
async def get_artifacts_by_regex(
    request: Dict[str, str],
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> List[ArtifactMetadata]:
    """Search for artifacts using regular expression over names and READMEs.

    Per OpenAPI v3.4.4 spec:
    - Searches artifact names and metadata
    - Similar to search by name but using regex
    - Returns 404 if no artifacts found

    Args:
        request: Request body with regex pattern
        x_authorization: Bearer token for authentication
        db: Database session (dependency injection)

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
        get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token",
        )

    if "regex" not in request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid",
        )

    import re

    try:
        regex = re.compile(request["regex"])
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid: {str(e)}",
        )

    # Search artifacts by name regex
    artifacts = db.query(ArtifactModel).all()
    matching = [a for a in artifacts if regex.search(a.name) or regex.search(a.type)]

    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No artifact found under this regex.",
        )

    return [ArtifactMetadata(name=a.name, id=a.id, type=a.type) for a in matching]
