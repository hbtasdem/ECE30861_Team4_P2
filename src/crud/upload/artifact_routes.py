"""Artifact management endpoints - OpenAPI v3.4.4 BASELINE endpoints.

FILE PURPOSE:
Implements Phase 2 core artifact CRUD operations per specification Section 3.2.

ENDPOINTS IMPLEMENTED (4/4 BASELINE):
1. POST /artifact/{type}
   - Path: POST /artifact/{artifact_type}
   - Purpose: Register new artifact from downloadable source URL
   - Response: 201 Created with full Artifact envelope
   - Spec Ref: Section 3.2.1 - ArtifactCreate

2. GET /artifacts/{type}/{id}
   - Path: GET /artifacts/{artifact_type}/{id}
   - Purpose: Retrieve artifact by type and ID
   - Response: 200 OK with full Artifact envelope
   - Spec Ref: Section 3.2.1 - ArtifactRetrieve

3. PUT /artifacts/{type}/{id}
   - Path: PUT /artifacts/{artifact_type}/{id}
   - Purpose: Update artifact source and metadata
   - Response: 200 OK with updated Artifact envelope
   - Spec Ref: Section 3.2.1 - ArtifactUpdate

4. POST /artifacts
   - Path: POST /artifacts
   - Purpose: Query/enumerate artifacts with name/type filters
   - Response: 200 OK with ArtifactMetadata array (NOT full envelope)
   - Spec Ref: Section 3.2.1 - ArtifactsList

ENVELOPE STRUCTURE (Per Spec Section 3.2.1):
All responses follow:
{
    "metadata": {"name": str, "id": str (ULID), "type": "model|dataset|code"},
    "data": {"url": str, "download_url": str (read-only)}
}
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session
from ulid import ULID

from src.crud.upload.artifacts import (Artifact, ArtifactData,
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
    status_code=status.HTTP_201_CREATED
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
            detail="Missing X-Authorization header"
        )

    try:
        current_user = get_current_user(x_authorization, db)
    except HTTPException as _e:  # noqa: F841
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token"
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
                   f"Must be one of: {', '.join(valid_types)}"
        )

    # Validate artifact data
    if not artifact_data.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Artifact data must contain 'url' field"
        )

    # ========================================================================
    # CREATE ARTIFACT
    # ========================================================================
    try:
        # Generate unique ID and download URL
        artifact_id = str(ULID())
        download_url = f"/api/artifacts/{artifact_type}/{artifact_id}/download"

        # Extract name from URL if not provided
        name = artifact_data.url.split('/')[-1]
        if not name or name.startswith('http'):
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
            user_id=current_user.id,
            artifact_id=artifact_id,
            action="CREATE"
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(new_artifact)

        # Return artifact in envelope format
        return Artifact(
            metadata=ArtifactMetadata(
                name=new_artifact.name,
                id=new_artifact.id,
                type=new_artifact.type
            ),
            data=ArtifactData(
                url=new_artifact.url,
                download_url=new_artifact.download_url
            )
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create artifact: {str(e)}"
        )


# ============================================================================
# GET /artifacts/{artifact_type}/{artifact_id} - RETRIEVE ARTIFACT (BASELINE)
# ============================================================================


@router.get(
    "/artifacts/{artifact_type}/{artifact_id}",
    response_model=Artifact
)
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
            detail="Missing X-Authorization header"
        )

    try:
        current_user = get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token"
        )

    # ========================================================================
    # RETRIEVE ARTIFACT
    # ========================================================================
    artifact = db.query(ArtifactModel).filter(
        ArtifactModel.id == artifact_id,
        ArtifactModel.type == artifact_type
    ).first()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_type}/{artifact_id}"
        )

    # Log DOWNLOAD action
    try:
        audit_entry = AuditEntry(
            user_id=current_user.id,
            artifact_id=artifact_id,
            action="DOWNLOAD"
        )
        db.add(audit_entry)
        db.commit()
    except Exception as _e:  # noqa: F841
        # Don't fail the request if audit logging fails
        db.rollback()

    return Artifact(
        metadata=ArtifactMetadata(
            name=artifact.name,
            id=artifact.id,
            type=artifact.type
        ),
        data=ArtifactData(
            url=artifact.url,
            download_url=artifact.download_url
        )
    )


# ============================================================================
# PUT /artifacts/{artifact_type}/{artifact_id} - UPDATE ARTIFACT (BASELINE)
# ============================================================================


@router.put(
    "/artifacts/{artifact_type}/{artifact_id}",
    response_model=Artifact
)
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
            detail="Missing X-Authorization header"
        )

    try:
        current_user = get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token"
        )

    # ========================================================================
    # RETRIEVE AND UPDATE ARTIFACT
    # ========================================================================
    artifact = db.query(ArtifactModel).filter(
        ArtifactModel.id == artifact_id,
        ArtifactModel.type == artifact_type
    ).first()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_type}/{artifact_id}"
        )

    try:
        # Update artifact data
        if artifact_data.url:
            artifact.url = artifact_data.url

        # Update name if derived from URL
        if artifact.url:
            name = artifact.url.split('/')[-1]
            if name and not name.startswith('http'):
                artifact.name = name

        db.flush()

        # Log UPDATE action
        audit_entry = AuditEntry(
            user_id=current_user.id,
            artifact_id=artifact_id,
            action="UPDATE"
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(artifact)

        return Artifact(
            metadata=ArtifactMetadata(
                name=artifact.name,
                id=artifact.id,
                type=artifact.type
            ),
            data=ArtifactData(
                url=artifact.url,
                download_url=artifact.download_url
            )
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update artifact: {str(e)}"
        )


# ============================================================================
# POST /artifacts - QUERY/ENUMERATE ARTIFACTS (BASELINE)
# ============================================================================


@router.post(
    "/artifacts",
    response_model=List[ArtifactMetadata]
)
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
            detail="Missing X-Authorization header"
        )

    try:
        get_current_user(x_authorization, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication failed: Invalid or expired token"
        )

    # ========================================================================
    # VALIDATION
    # ========================================================================
    if not queries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one query is required"
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
            ArtifactMetadata(
                name=artifact.name,
                id=artifact.id,
                type=artifact.type
            )
            for artifact in results
        ]

        return metadata_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query failed: {str(e)}"
        )
