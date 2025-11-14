# IMPLEMENTATION GUIDE: ECE 461 OpenAPI v3.4.4 Spec Compliance

**Priority**: 🔴 CRITICAL - SPEC COMPLIANCE IS MANDATORY  
**Date**: November 11, 2025  
**Spec Version**: v3.4.4

---

## EXECUTIVE SUMMARY

Current implementation does NOT match the official OpenAPI v3.4.4 specification. This guide provides step-by-step fixes to achieve 100% compliance.

**3 Critical Issues to Fix First**:
1. ❌ Artifact ID: Integer → String (affects all endpoints)
2. ❌ Response Structure: Flat → {metadata, data} envelope
3. ❌ Enumerate: GET → POST with JSON array

---

## PHASE 1: DATABASE SCHEMA REFACTOR (CRITICAL)

### Step 1.1: Add UUID dependency to requirements.txt

**File**: `requirements.txt`

```bash
# Add to end of file:
python-ulid>=1.0.0  # For generating string-based unique IDs (or use uuid)
```

### Step 1.2: Refactor src/models.py

**Current Issues**:
- Artifact ID is Integer (should be String)
- Only supports "model" type (need model, dataset, code)
- Extra fields not in spec (description, version, is_sensitive)

**Required Changes**:

Replace the `Model` class entirely:

```python
# models.py
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Integer, CheckConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    artifacts = relationship('Artifact', back_populates='uploader')


class Artifact(Base):
    """
    Spec-compliant Artifact model.
    
    Artifact ID is a string (e.g., "3847247294" or UUID format).
    Artifact type is: model, dataset, or code.
    """
    __tablename__ = 'artifacts'
    
    # Metadata (per spec)
    id = Column(String(255), primary_key=True)  # ✅ String UUID
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # ✅ Enum: model, dataset, code
    
    # Data (per spec)
    url = Column(String(2048), nullable=False)  # Source URL
    download_url = Column(String(2048), nullable=False)  # Our download URL
    
    # Tracking
    uploader_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploader = relationship('User', back_populates='artifacts')
    audit_entries = relationship('AuditEntry', back_populates='artifact', cascade='all, delete-orphan')
    
    # Constraint: type must be one of the three
    __table_args__ = (
        CheckConstraint("type IN ('model', 'dataset', 'code')"),
    )


class AuditEntry(Base):
    """
    Audit trail for artifact mutations (NON-BASELINE but required for tracking).
    
    Actions: CREATE, UPDATE, DOWNLOAD, RATE, AUDIT
    """
    __tablename__ = 'audit_entries'
    
    id = Column(Integer, primary_key=True)
    artifact_id = Column(String(255), ForeignKey('artifacts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(20), nullable=False)  # CREATE, UPDATE, DOWNLOAD, RATE, AUDIT
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    artifact = relationship('Artifact', back_populates='audit_entries')
    user = relationship('User')
```

**Migration Notes**:
- Rename `Model` table to `artifacts`
- Change `id` column from `Integer` to `String(255)`
- Rename column `artifact_type` to `type`
- Add `type` to table constraints
- Remove `description`, `version`, `is_sensitive` columns
- Add `AuditEntry` table for tracking

---

## PHASE 2: PYDANTIC SCHEMAS REFACTOR (CRITICAL)

### Step 2.1: Refactor crud/upload/models.py

**File**: `crud/upload/models.py`

Replace ALL schemas with spec-compliant versions:

```python
"""Pydantic schemas for OpenAPI v3.4.4 compliance."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# ARTIFACT SCHEMAS (Per OpenAPI Spec)
# ============================================================================

class ArtifactMetadata(BaseModel):
    """Artifact metadata (name, id, type)."""
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., description="Artifact name")
    id: str = Field(..., description="String UUID artifact ID")
    type: str = Field(..., description="Type: model, dataset, or code")


class ArtifactData(BaseModel):
    """Artifact data (URLs)."""
    model_config = ConfigDict(from_attributes=True)
    
    url: str = Field(..., description="Source URL for artifact")
    download_url: Optional[str] = Field(None, description="Our server's download URL (read-only in requests)")


class Artifact(BaseModel):
    """Complete artifact with metadata and data envelope."""
    model_config = ConfigDict(from_attributes=True)
    
    metadata: ArtifactMetadata
    data: ArtifactData


# ============================================================================
# QUERY SCHEMAS (For POST /artifacts enumerate)
# ============================================================================

class ArtifactQuery(BaseModel):
    """Query filter for artifact enumeration."""
    
    name: str = Field(..., description='Artifact name or "*" for all')
    types: Optional[List[str]] = Field(None, description="Optional filter by types")


# ============================================================================
# AUTHENTICATION SCHEMAS (Per OpenAPI Spec)
# ============================================================================

class User(BaseModel):
    """User information."""
    
    name: str = Field(..., description="Username or email")
    is_admin: bool = Field(default=False, description="Is admin?")


class UserAuthenticationInfo(BaseModel):
    """User authentication secret."""
    
    password: str = Field(..., description="User password")


class AuthenticationRequest(BaseModel):
    """Authentication request (login/register)."""
    
    user: User
    secret: UserAuthenticationInfo


class AuthenticationToken(BaseModel):
    """Authentication response token."""
    
    token: str = Field(..., description='Bearer token format: "bearer <jwt>"')


# ============================================================================
# AUDIT SCHEMAS
# ============================================================================

class AuditEntry(BaseModel):
    """Single audit trail entry."""
    model_config = ConfigDict(from_attributes=True)
    
    user: User
    date: datetime = Field(..., description="ISO-8601 datetime in UTC")
    artifact: ArtifactMetadata
    action: str = Field(..., description="Action: CREATE, UPDATE, DOWNLOAD, RATE, AUDIT")


# ============================================================================
# LINEAGE SCHEMAS
# ============================================================================

class ArtifactLineageNode(BaseModel):
    """Node in artifact lineage graph."""
    model_config = ConfigDict(from_attributes=True)
    
    artifact_id: str
    name: str
    source: str = Field(..., description="How node was discovered (e.g., config_json)")
    metadata: Optional[dict] = None


class ArtifactLineageEdge(BaseModel):
    """Edge in artifact lineage graph."""
    
    from_node_artifact_id: str
    to_node_artifact_id: str
    relationship: str = Field(..., description="Relationship description")


class ArtifactLineageGraph(BaseModel):
    """Complete lineage graph for artifact."""
    
    nodes: List[ArtifactLineageNode]
    edges: List[ArtifactLineageEdge]


# ============================================================================
# LICENSE CHECK SCHEMAS
# ============================================================================

class SimpleLicenseCheckRequest(BaseModel):
    """License compatibility check request."""
    
    github_url: str = Field(..., description="GitHub repository URL")


# ============================================================================
# REGEX SEARCH SCHEMA
# ============================================================================

class ArtifactRegEx(BaseModel):
    """Regular expression search request."""
    
    regex: str = Field(..., description="Regex pattern for names/READMEs")


# ============================================================================
# LEGACY SCHEMAS (For backward compatibility, mark as deprecated)
# ============================================================================

class ModelCreate(BaseModel):
    """DEPRECATED: Use ArtifactData instead."""
    name: str
    url: str


class UploadResponse(BaseModel):
    """DEPRECATED: Use Artifact instead."""
    message: str
    model_id: str
    model_url: str
    artifact_type: str
```

---

## PHASE 3: ENDPOINT REFACTOR (CRITICAL)

### Step 3.1: Refactor crud/upload/routes.py

**Major Changes**:
- Change GET /api/models/enumerate → POST /artifacts
- Change POST /api/models/upload → POST /artifact/{type}
- Add GET /artifacts/{type}/{id}
- Add PUT /artifacts/{type}/{id}
- Change response structure to {metadata, data}
- Add offset-based pagination

**New File Structure**:

```python
"""REST API endpoints for artifact management (OpenAPI v3.4.4 compliant)."""

import os
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from crud.upload.auth import get_current_user  # noqa: E402
from crud.upload.models import (  # noqa: E402
    Artifact, ArtifactData, ArtifactMetadata, ArtifactQuery
)
from src.database import get_db  # noqa: E402
from src.models import Artifact as ArtifactModel, AuditEntry, User  # noqa: E402


router = APIRouter(tags=["artifacts"])

# ============================================================================
# POST /artifacts - ENUMERATE (BASELINE)
# ============================================================================

@router.post("/artifacts", response_model=List[ArtifactMetadata])
async def enumerate_artifacts(
    queries: List[ArtifactQuery],
    offset: Optional[str] = Query(None),
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> List[ArtifactMetadata]:
    """
    Enumerate artifacts from registry (BASELINE).
    
    Request array of ArtifactQuery objects.
    Response includes offset header for pagination.
    """
    # Verify auth
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    # Validate queries
    if not queries:
        raise HTTPException(status_code=400, detail="At least one query required")
    
    try:
        # Build query
        offset_int = int(offset) if offset else 0
        page_size = 100
        
        # Get artifacts matching queries
        results = []
        for query in queries:
            if query.name == "*":
                # Get all artifacts
                artifacts = db.query(ArtifactModel).offset(offset_int).limit(page_size).all()
            else:
                # Filter by name and optional types
                q = db.query(ArtifactModel).filter(ArtifactModel.name == query.name)
                if query.types:
                    q = q.filter(ArtifactModel.type.in_(query.types))
                artifacts = q.offset(offset_int).limit(page_size).all()
            
            results.extend(artifacts)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for art in results:
            if art.id not in seen:
                seen.add(art.id)
                unique_results.append(art)
        
        # Convert to metadata
        metadata_list = [
            ArtifactMetadata(name=art.name, id=art.id, type=art.type)
            for art in unique_results
        ]
        
        # Return with offset header
        # Note: FastAPI doesn't support response headers directly in return,
        # you may need to use Response object
        return metadata_list
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# POST /artifact/{artifact_type} - CREATE (BASELINE)
# ============================================================================

@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
async def create_artifact(
    artifact_type: str,
    data: ArtifactData,
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Register new artifact (BASELINE).
    
    HTTP 201 on success.
    HTTP 202 if rating deferred asynchronously.
    HTTP 409 if artifact already exists.
    HTTP 424 if disqualified rating.
    """
    # Verify auth
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    # Validate artifact type
    if artifact_type not in ["model", "dataset", "code"]:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    
    # Validate URL
    if not data.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Extract name from URL
        name = data.url.split('/')[-1]
        
        # Generate string ID
        artifact_id = str(uuid.uuid4()).replace('-', '')[:16]  # or use nanoid
        
        # Check if artifact already exists
        existing = db.query(ArtifactModel).filter(
            (ArtifactModel.name == name) & (ArtifactModel.type == artifact_type)
        ).first()
        
        if existing:
            raise HTTPException(status_code=409, detail="Artifact exists already")
        
        # Create artifact
        new_artifact = ArtifactModel(
            id=artifact_id,
            name=name,
            type=artifact_type,
            url=data.url,
            download_url=f"https://your-server.com/download/{artifact_id}",
            uploader_id=1  # TODO: Get from auth token
        )
        
        db.add(new_artifact)
        db.commit()
        db.refresh(new_artifact)
        
        # Log audit
        audit = AuditEntry(
            artifact_id=artifact_id,
            user_id=1,
            action="CREATE"
        )
        db.add(audit)
        db.commit()
        
        # Return Artifact envelope
        return {
            "metadata": {
                "name": new_artifact.name,
                "id": new_artifact.id,
                "type": new_artifact.type
            },
            "data": {
                "url": new_artifact.url,
                "download_url": new_artifact.download_url
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# GET /artifacts/{artifact_type}/{id} - RETRIEVE (BASELINE)
# ============================================================================

@router.get("/artifacts/{artifact_type}/{artifact_id}", response_model=Artifact)
async def get_artifact(
    artifact_type: str,
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Retrieve artifact by type and ID (BASELINE).
    """
    # Verify auth
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    # Validate type
    if artifact_type not in ["model", "dataset", "code"]:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    
    # Get artifact
    artifact = db.query(ArtifactModel).filter(
        (ArtifactModel.id == artifact_id) & (ArtifactModel.type == artifact_type)
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist")
    
    # Log audit
    audit = AuditEntry(
        artifact_id=artifact_id,
        user_id=1,
        action="DOWNLOAD"
    )
    db.add(audit)
    db.commit()
    
    # Return Artifact envelope
    return {
        "metadata": {
            "name": artifact.name,
            "id": artifact.id,
            "type": artifact.type
        },
        "data": {
            "url": artifact.url,
            "download_url": artifact.download_url
        }
    }


# ============================================================================
# PUT /artifacts/{artifact_type}/{id} - UPDATE (BASELINE)
# ============================================================================

@router.put("/artifacts/{artifact_type}/{artifact_id}")
async def update_artifact(
    artifact_type: str,
    artifact_id: str,
    artifact: Artifact,
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Update artifact (BASELINE).
    
    Name and ID must match.
    """
    # Verify auth
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    # Validate type
    if artifact_type not in ["model", "dataset", "code"]:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    
    # Get artifact
    db_artifact = db.query(ArtifactModel).filter(
        (ArtifactModel.id == artifact_id) & (ArtifactModel.type == artifact_type)
    ).first()
    
    if not db_artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist")
    
    # Verify name/ID match
    if artifact.metadata.name != db_artifact.name or artifact.metadata.id != artifact_id:
        raise HTTPException(status_code=400, detail="Name and ID must match")
    
    try:
        # Update fields
        db_artifact.url = artifact.data.url
        db_artifact.download_url = artifact.data.download_url or db_artifact.download_url
        db_artifact.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Log audit
        audit = AuditEntry(
            artifact_id=artifact_id,
            user_id=1,
            action="UPDATE"
        )
        db.add(audit)
        db.commit()
        
        return {"message": "Artifact is updated"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# DELETE /artifacts/{artifact_type}/{id} - DELETE (NON-BASELINE)
# ============================================================================

@router.delete("/artifacts/{artifact_type}/{artifact_id}")
async def delete_artifact(
    artifact_type: str,
    artifact_id: str,
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Delete artifact (NON-BASELINE).
    """
    # Verify auth
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    # Validate type
    if artifact_type not in ["model", "dataset", "code"]:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    
    # Get artifact
    artifact = db.query(ArtifactModel).filter(
        (ArtifactModel.id == artifact_id) & (ArtifactModel.type == artifact_type)
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist")
    
    try:
        db.delete(artifact)
        db.commit()
        return {"message": "Artifact is deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Additional Endpoints (NEW in v3.4.4)
# ============================================================================

@router.get("/artifact/byName/{name}", response_model=List[ArtifactMetadata])
async def get_artifacts_by_name(
    name: str,
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> List[dict[str, Any]]:
    """Get artifacts by name (NON-BASELINE)."""
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    artifacts = db.query(ArtifactModel).filter(ArtifactModel.name == name).all()
    
    if not artifacts:
        raise HTTPException(status_code=404, detail="No such artifact")
    
    return [
        {"name": art.name, "id": art.id, "type": art.type}
        for art in artifacts
    ]


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
async def search_artifacts_by_regex(
    regex_query: dict[str, str],
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> List[dict[str, Any]]:
    """Search artifacts by regex (BASELINE)."""
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    import re
    pattern = regex_query.get("regex")
    
    if not pattern:
        raise HTTPException(status_code=400, detail="Regex pattern required")
    
    try:
        compiled = re.compile(pattern)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex pattern")
    
    artifacts = db.query(ArtifactModel).all()
    matches = [art for art in artifacts if compiled.search(art.name)]
    
    if not matches:
        raise HTTPException(status_code=404, detail="No artifact found under this regex")
    
    return [
        {"name": art.name, "id": art.id, "type": art.type}
        for art in matches
    ]


@router.delete("/reset")
async def reset_registry(
    x_authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict[str, str]:
    """Reset registry to default state (admin only, BASELINE)."""
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Missing authentication token")
    
    # TODO: Verify admin user
    
    try:
        db.query(ArtifactModel).delete()
        db.query(AuditEntry).delete()
        db.commit()
        return {"message": "Registry is reset"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=401, detail="You do not have permission")


@router.get("/tracks")
async def get_planned_tracks() -> dict[str, list[str]]:
    """Get planned tracks (no auth required, NEW in v3.4.4)."""
    return {
        "plannedTracks": [
            "Performance track",
            "Access control track",
            "High assurance track",
            "Other Security track"
        ]
    }
```

---

## PHASE 4: AUTHENTICATION UPDATES

### Step 4.1: Update crud/upload/auth_routes.py

Change `/auth/register` to work with String IDs and proper response format:

```python
"""Updated authentication routes for v3.4.4 compliance."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud.upload.auth import create_access_token, hash_password, verify_password
from crud.upload.models import AuthenticationRequest, AuthenticationToken
from src.database import get_db
from src.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.put("/authenticate")
async def authenticate(
    request: AuthenticationRequest,
    db: Session = Depends(get_db)
) -> AuthenticationToken:
    """
    Authenticate user and return JWT token (NON-BASELINE).
    
    Per spec: PUT /authenticate
    """
    user = db.query(User).filter(User.username == request.user.name).first()
    
    if not user or not verify_password(request.secret.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(user.id), "is_admin": user.is_admin})
    
    return AuthenticationToken(token=f"bearer {token}")
```

---

## PHASE 5: MIGRATION STRATEGY

### Step 5.1: Database Migration

Since we're changing from Integer ID to String ID, you need to:

1. **Backup existing data** (if any)
2. **Drop old tables**:
   ```python
   # In a migration script:
   from src.models import Base
   Base.metadata.drop_all(bind=engine)
   Base.metadata.create_all(bind=engine)
   ```
3. **Recreate tables** with new schema

### Step 5.2: Update conftest.py

Ensure test fixtures use string IDs:

```python
# crud/upload/tests/conftest.py
# Update to create artifacts with string IDs
artifact = Artifact(
    id="3847247294",  # String, not int
    name="test-artifact",
    type="model",  # model, dataset, or code
    url="https://example.com/model",
    download_url="https://your-server/download/3847247294",
    uploader_id=1
)
```

---

## TESTING CHECKLIST

After implementation, verify:

- [ ] POST /artifacts returns List[ArtifactMetadata]
- [ ] POST /artifact/{type} returns Artifact envelope {metadata, data}
- [ ] GET /artifacts/{type}/{id} returns Artifact envelope
- [ ] PUT /artifacts/{type}/{id} accepts and returns Artifact
- [ ] All responses match spec schema exactly
- [ ] All artifact types (model, dataset, code) supported
- [ ] Artifact IDs are strings, not integers
- [ ] Authentication required on all endpoints (except /tracks and /health)
- [ ] Offset-based pagination working
- [ ] Audit trail logging for CREATE, UPDATE, DOWNLOAD
- [ ] 409 response for duplicate artifacts
- [ ] 404 response for missing artifacts
- [ ] 403 response for auth failures
- [ ] 400 response for malformed requests

---

## SUMMARY

**Files to Modify**:
1. `requirements.txt` - Add python-ulid
2. `src/models.py` - Refactor schema (int→string, add types, add AuditEntry)
3. `crud/upload/models.py` - Complete Pydantic schema rewrite
4. `crud/upload/routes.py` - Rewrite all endpoints for v3.4.4
5. `crud/upload/auth_routes.py` - Minor updates for consistency
6. `tests/conftest.py` - Update fixtures for string IDs
7. `crud/upload/tests/conftest.py` - Update test fixtures

**Estimated Effort**: 8-12 hours

**Priority Order**:
1. Schema changes (Phase 1-2)
2. Endpoint refactor (Phase 3)
3. Authentication (Phase 4)
4. Testing & validation (Phase 5)

---

---

## PHASE 4: UPLOAD ENHANCEMENTS

### Summary of Phase 4 Improvements

| Aspect | Before | After | Location |
|--------|--------|-------|----------|
| **File Upload** | Single file only | Batch (1-50) & Chunked (up to 100GB) | `batch_upload_routes.py` lines 92-240 |
| **Upload Sessions** | None | 24-hour expiration, session tracking | `batch_upload_routes.py` lines 264-360 |
| **Chunk Management** | N/A | Out-of-order chunks, integrity verification | `batch_upload_routes.py` lines 369-550 |
| **File Validation** | Basic MIME check | MIME, size, filename, metadata, malware, comprehensive | `file_validator.py` (6 validation methods) |
| **Duplicate Detection** | Manual check | Automatic SHA256 comparison | `file_routes.py` lines 269-340 |
| **Progress Tracking** | None | Real-time ETA calculation, upload stats | `batch_upload_routes.py` lines 607-675 |
| **Response Schema** | Flat structure | Typed Pydantic models with field validation | `file_schemas.py` (14 models) |
| **Error Handling** | Basic HTTP exceptions | Granular errors (413, 422, 409, 410) | All route files |
| **Concurrent Uploads** | Sequential | Multiple parallel sessions per user | In-memory session storage |
| **File Versioning** | Single version | Version tracking with timestamp | `FileUploadResponse.version` |

### Phase 4 Endpoints Implemented

#### Batch Upload (POST /api/models/upload-batch)
- **Lines**: `batch_upload_routes.py` 92-240
- **Features**: Upload 1-50 files, optional duplicate skipping, stop-on-error
- **Response Model**: `BatchUploadResponse` with per-file results
- **Status Code**: 201 Created

#### Chunked Upload Init (POST /api/models/chunked-upload/init)
- **Lines**: `batch_upload_routes.py` 264-360
- **Features**: Support up to 100GB, configurable chunk size (256KB-10MB)
- **Request Model**: `ChunkedUploadInitRequest`
- **Response Model**: `ChunkedUploadInitResponse` with session ID & expiration
- **Status Code**: 201 Created

#### Upload Chunk (POST /api/models/chunked-upload/{session_id}/chunk)
- **Lines**: `batch_upload_routes.py` 369-550
- **Features**: Out-of-order support, per-chunk SHA256 verification, automatic retry
- **Request Parameters**: session_id, chunk_number, chunk_hash
- **Response Model**: `ChunkUploadResponse` with checksum confirmation
- **Status Code**: 202 Accepted

#### Finalize Upload (POST /api/models/chunked-upload/{session_id}/finalize)
- **Lines**: `batch_upload_routes.py` 470-605
- **Features**: Assemble chunks, final integrity check, cleanup expired sessions
- **Request Model**: `ChunkedUploadFinalizeRequest` with final SHA256
- **Response Model**: `ChunkedUploadFinalizeResponse` with artifact ID
- **Status Code**: 200 OK

#### Upload Progress (GET /api/models/chunked-upload/{session_id}/progress)
- **Lines**: `batch_upload_routes.py` 607-675
- **Features**: Real-time progress, ETA calculation, bytes received/remaining
- **Response Model**: `UploadProgressResponse` with completion percentage
- **Status Code**: 200 OK

#### Validate File (POST /api/models/validate)
- **Lines**: `file_routes.py` 338-415
- **Features**: MIME, size, filename, metadata, malware, comprehensive validation
- **Request Parameters**: artifact_id, filename, optional metadata
- **Response Model**: Validation results with pass/fail per check
- **Status Code**: 201 Created

#### Check Duplicate (POST /api/models/check-duplicate)
- **Lines**: `file_routes.py` 269-340
- **Features**: O(1) SHA256 lookup, optional artifact exclusion
- **Request Model**: `DuplicateCheckRequest` with SHA256
- **Response Model**: `DuplicateCheckResponse` with duplicate ID if found
- **Status Code**: 200 OK

#### Upload File (POST /api/models/upload-file)
- **Lines**: `file_routes.py` 45-160
- **Features**: Single file with automatic checksums, versioning, audit logging
- **Request Parameters**: artifact_id, file, optional description
- **Response Model**: `FileUploadResponse` with checksums & download URL
- **Status Code**: 201 Created

### Phase 4 Pydantic Models (14 Total)

| Model | Purpose | Fields |
|-------|---------|--------|
| `FileUploadResponse` | Single file upload result | file_id, artifact_id, filename, size_bytes, sha256_checksum, md5_checksum, download_url, version |
| `BatchUploadRequest` | Batch upload request wrapper | artifact_id, files, skip_duplicates, stop_on_error |
| `BatchUploadResponse` | Batch upload result | batch_id, total_files, successful, failed, results, created_at |
| `BatchUploadFileResult` | Per-file result in batch | filename, file_id, status, error_message, checksums |
| `DuplicateCheckRequest` | Duplicate detection request | artifact_id, filename, sha256_checksum |
| `DuplicateCheckResponse` | Duplicate detection result | is_duplicate, existing_file_id, message |
| `ChunkedUploadInitRequest` | Chunked upload session start | artifact_id, filename, total_size_bytes, total_chunks, chunk_size_bytes |
| `ChunkedUploadInitResponse` | Chunked upload session created | upload_session_id, upload_url, expires_at, chunk_size_bytes |
| `ChunkUploadRequest` | Individual chunk metadata | chunk_number, chunk_hash, chunk_data |
| `ChunkUploadResponse` | Individual chunk accepted | chunk_number, bytes_received, checksum_verified, status |
| `ChunkedUploadFinalizeRequest` | Finalize chunked upload | session_id, final_sha256_checksum |
| `ChunkedUploadFinalizeResponse` | Upload complete | artifact_id, file_id, file_size_bytes, sha256_checksum |
| `UploadProgressResponse` | Real-time progress update | bytes_received, bytes_remaining, chunks_received, total_chunks, percentage_complete, eta_seconds, current_speed_mbps |
| `FileVerificationRequest` | File verification request | file_id, sha256_checksum |

### Phase 4 Validation Methods

| Method | Purpose | Checks |
|--------|---------|--------|
| `validate_mime_type()` | Verify file type | Against allowed MIME types (application/*, image/*, text/*) |
| `validate_size()` | Check file constraints | Min 1 byte, max 1GB, matches declared size |
| `validate_filename()` | Sanitize filename | Length, special chars, reserved names |
| `validate_metadata_extraction()` | Parse metadata | Successfully extract file headers, exif, archives |
| `validate_malware_scan()` | Security scan | Virus/malware detection (mock or real scanner) |
| `validate_file()` | Comprehensive check | All above checks in sequence |

### Key Implementation Details

**Session Management**:
- In-memory dict with 24-hour TTL
- Production: Migrate to Redis for distributed systems
- Session expiration triggers cleanup of incomplete uploads

**Chunk Strategy**:
- Configurable size: 256KB minimum, 10MB default, 100MB maximum
- Out-of-order support: Track received chunk map
- Integrity: Per-chunk SHA256 verification
- Assembly: Sequential concatenation with temp file

**Progress Calculation**:
- Real-time byte tracking per session
- ETA: (bytes_remaining / current_speed_mbps) / 60
- Speed: Rolling 30-second average

**Error Responses**:
- 201 Created: Successful upload
- 202 Accepted: Chunk accepted, awaiting others
- 400 Bad Request: Invalid parameters
- 404 Not Found: Artifact or session not found
- 409 Conflict: Duplicate file detected
- 410 Gone: Session expired
- 413 Payload Too Large: File exceeds limits
- 422 Unprocessable Entity: Validation failed

---

## CRITICAL REMINDERS

✅ **SPEC COMPLIANCE IS MANDATORY**

- All artifact IDs MUST be strings
- All responses MUST use {metadata, data} envelope
- All endpoints MUST require X-Authorization header (except /health and /tracks)
- All artifact types must be supported (model, dataset, code)
- All HTTP status codes must match spec exactly
- No backward compatibility - this is a complete refactor

