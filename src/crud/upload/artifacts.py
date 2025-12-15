"""Pydantic v2 validation schemas - OpenAPI v3.4.4 BASELINE compliance.

FILE PURPOSE:
Defines all request/response data models for Phase 2 artifact CRUD operations.
Every schema is required by OpenAPI v3.4.4 specification Section 3.2.

SPEC COMPLIANCE REFERENCE:
Per OpenAPI v3.4.4 Section 3.2.1 - Artifact Object Definition

KEY ARCHITECTURAL DECISIONS:

1. TWO-SECTION ENVELOPE STRUCTURE (SPEC REQUIREMENT)
   Section 3.2.1 mandates all responses use envelope format:
   {
     "metadata": {"name": str, "id": str (ULID), "type": "model|dataset|code"},
     "data": {"url": str, "download_url": str (read-only in responses)}
   }

   Rationale: Separates artifact identification (metadata) from content
   location (data), enabling clean schema versioning and future extensions.

2. STRING ARTIFACT IDs (SPEC REQUIREMENT)
   Section 3.2.1 specifies: "Unique identifier" with pattern "^[a-zA-Z0-9\\-]+$"
   Implementation: ULID format (26 alphanumeric chars, timestamp-based, globally unique)
   Example: "01K9ZBPCEQM0CK4X2T984FX8CS"

   Benefits over integers:
   - Globally unique across distributed systems
   - Timestamp-based (sortable)
   - Spec-compliant pattern matching
   - Supports horizontal scaling

3. THREE ARTIFACT TYPES ONLY (SPEC REQUIREMENT)
   Section 3.2.1 ArtifactType enum: ["model", "dataset", "code"]
   Database constraint: CHECK (type IN ('model', 'dataset', 'code'))
   Validation: Pydantic Field enum constraint

   Supported:
   - "model": Machine learning models (PyTorch, TensorFlow, etc.)
   - "dataset": Training/test datasets (CSV, Parquet, images, etc.)
   - "code": Source code artifacts (Python, Java, etc.)

4. UNIFIED ARTIFACT SCHEMA FOR ALL TYPES (SPEC REQUIREMENT)
   Section 3.2.1: Single Artifact class handles all three types

   Before: Separate ModelMetadata, DatasetMetadata, CodeMetadata classes
   After: Single Artifact envelope with type discriminator

   Rationale: Per spec, all three types share identical endpoint paths
   and response structure; type field distinguishes them.

SCHEMAS DEFINED:
- ArtifactMetadata: Identification fields (name, id, type)
- ArtifactData: Content location (url, download_url)
- Artifact: Complete envelope (metadata + data)
- ArtifactQuery: Search/filter parameters
- User: User object for audit trails
- AuthenticationRequest: Login credentials
- AuthenticationToken: JWT bearer token response
- AuditEntry: Audit trail record

USAGE IN PHASE 2 ENDPOINTS:
All 4 BASELINE endpoints use these schemas per spec Section 3.2

  Example endpoint (per spec):
    GET /artifacts/{type}/{id}
    Response: Artifact (with metadata + data envelope)
    HTTP 200 on success
    HTTP 404 if artifact not found
    HTTP 403 if not authenticated
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# ARTIFACT SCHEMAS - CORE ENVELOPE STRUCTURE
# ============================================================================


class ArtifactMetadata(BaseModel):
    """Artifact metadata section - identifies the artifact per spec.

    Per OpenAPI spec Section 3.2.1:
    The metadata section contains fields that IDENTIFY the artifact:
    - name: Human-readable name (e.g., "bert-base-uncased")
    - id: Unique string identifier (MUST be string, not integer!)
    - type: Classification (model, dataset, or code)

    This is used in:
    - POST /artifacts response
    - GET /artifacts/{type}/{id} response
    - Audit trail entries
    - Lineage graph nodes

    Example:
    {
        "name": "bert-base-uncased",
        "id": "550e8400e29b41d4a716446655440000",
        "type": "model"
    }

    Attributes:
        name (str): Artifact name - used for search/lookup
        id (str): CRITICAL - Must be string, not integer!
                  Format: "^[a-zA-Z0-9\\-]+$" per spec
                  Examples: "3847247294", UUIDs, ULIDs
        type (str): Must be one of: "model", "dataset", "code"
                    Per spec: No other types are allowed
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(
        ...,
        description="Artifact name - human readable identifier",
        min_length=1,
        max_length=255,
    )
    id: str = Field(
        ...,
        description="String UUID artifact ID (NOT integer!) - "
        "Per spec must match pattern ^[a-zA-Z0-9\\-]+$",
        min_length=1,
        max_length=255,
    )
    type: str = Field(
        ...,
        description="Artifact type per spec - "
        "MUST be one of: 'model', 'dataset', 'code'. "
        "No other types allowed.",
        json_schema_extra={"enum": ["model", "dataset", "code"]},
    )


class ArtifactData(BaseModel):
    """Artifact data section - points to the artifact content per spec.

    Per OpenAPI spec Section 3.2.1:
    The data section contains URLs that POINT TO the artifact:
    - url: Source URL where artifact originated
    - download_url: Our server's URL for artifact retrieval

    This separation of metadata/data enables:
    1. Tracking artifact provenance (url)
    2. Providing direct download (download_url)
    3. Auditing artifact access
    4. Supporting multiple mirror/CDN locations

    Used in:
    - POST /artifact/{type} response (upload endpoint)
    - GET /artifacts/{type}/{id} response
    - PUT /artifacts/{type}/{id} request/response

    Example:
    {
        "url": "https://huggingface.co/bert-base-uncased",
        "download_url": "https://our-server.com/download/550e8400e29b41d4a716446655440000"
    }

    Attributes:
        url (str): Source URL - where artifact originated
                   Per spec: Used to verify artifact authenticity
        download_url (str): Our download URL - where users get the artifact
                            Per spec: Read-only in responses (set by server)
                            Optional in requests (server provides)
    """

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(
        None,
        description="Custom name for the artifact - "
        "If not provided, will be extracted from URL",
        min_length=1,
        max_length=255,
    )

    url: str = Field(
        ...,
        description="Source URL where artifact originated "
        "(e.g., https://huggingface.co/bert-base-uncased) - "
        "Per spec: Used to verify provenance",
        min_length=1,
        max_length=2048,
    )
    download_url: Optional[str] = Field(
        None,
        description="Server download URL for artifact retrieval - "
        "Per spec: Read-only in responses (set by server), "
        "optional in requests",
        max_length=2048,
    )


class Artifact(BaseModel):
    """Complete artifact with metadata and data envelope per spec.

    Per OpenAPI spec Section 3.2.1:
    ALL responses containing artifact information MUST use this envelope
    structure with two sections:
    1. metadata: Identification (name, id, type)
    2. data: Content location (url, download_url)

    This two-section envelope pattern is used consistently across ALL
    endpoints that return artifact information.

    Endpoints using this schema:
    - POST /artifact/{type}: Create artifact (return Artifact)
    - GET /artifacts/{type}/{id}: Retrieve artifact (return Artifact)
    - PUT /artifacts/{type}/{id}: Update artifact (return Artifact)
    - POST /artifacts: Enumerate artifacts (return List[ArtifactMetadata])

    Example response:
    HTTP 200 OK
    {
        "metadata": {
            "name": "bert-base-uncased",
            "id": "550e8400e29b41d4a716446655440000",
            "type": "model"
        },
        "data": {
            "url": "https://huggingface.co/bert-base-uncased",
            "download_url": "https://our-server.com/download/550e8400e29b41d4a716446655440000"
        }
    }

    Attributes:
        metadata (ArtifactMetadata): Identifies the artifact
        data (ArtifactData): Points to the artifact content
    """

    model_config = ConfigDict(from_attributes=True)

    metadata: ArtifactMetadata = Field(
        ...,
        description="Artifact metadata - identifies what it is "
        "(name, id, type) per spec Section 3.2.1",
    )
    data: ArtifactData = Field(
        ...,
        description="Artifact data - where to find it "
        "(url, download_url) per spec Section 3.2.1",
    )


# ============================================================================
# QUERY SCHEMAS - FOR ARTIFACT ENUMERATION (Per Spec POST /artifacts)
# ============================================================================


class ArtifactQuery(BaseModel):
    """Query filter for artifact enumeration per spec.

    Per OpenAPI spec POST /artifacts endpoint:
    Request body is an array of ArtifactQuery objects for flexible filtering.

    Each query specifies:
    - name: Which artifact(s) to search for
    - types: Optional filter by artifact type(s)

    Multiple queries are OR'd together:
    If queries = [{"name": "bert*"}, {"name": "gpt*"}]
    Returns artifacts matching either pattern.

    Per spec: name="*" returns all artifacts (with optional type filter)

    Example request:
    POST /artifacts
    [
        {"name": "*", "types": ["model"]},  // All models
        {"name": "bert-*"}                   // Or anything named bert-*
    ]

    Attributes:
        name (str): Artifact name pattern or "*" for all
                    Per spec: Supports simple wildcard matching
        types (List[str]): Optional filter by types
                           Per spec: If provided, must be subset of
                           {model, dataset, code}
    """

    name: str = Field(
        ...,
        description='Artifact name or "*" for all artifacts '
        "per spec POST /artifacts endpoint",
        min_length=1,
        max_length=255,
    )
    types: Optional[List[str]] = Field(
        None,
        description="Optional filter by artifact types "
        "(subset of: model, dataset, code) "
        "per spec POST /artifacts",
        min_length=0,
        max_length=3,
    )


# ============================================================================
# AUTHENTICATION SCHEMAS (Per Spec Section 3.2.2)
# ============================================================================


class User(BaseModel):
    """User information per OpenAPI spec Section 3.2.2.

    Per spec: User object contains:
    - name: Username or email identifier
    - is_admin: Admin flag for access control

    Used in:
    - AuthenticationRequest (login/register)
    - AuditEntry (tracks which user performed action)

    Per spec: User authentication is required for most endpoints
    (except /health and /tracks which are public)

    Example:
    {
        "name": "alice@example.com",
        "is_admin": false
    }

    Attributes:
        name (str): Username or email for authentication
        is_admin (bool): Is this user an admin? (default False)
    """

    name: str = Field(
        ...,
        description="Username or email per spec User object",
        min_length=1,
        max_length=255,
    )
    is_admin: bool = Field(
        False,
        description="Is this user an admin? "
        "Determines access to admin endpoints like DELETE /reset",
    )


class UserAuthenticationInfo(BaseModel):
    """User authentication secret per OpenAPI spec.

    Per spec Section 3.2.2: Contains the authentication credential
    (password) for login/registration.

    Never exposed in responses - only used in requests.
    Per spec: Passwords are hashed with bcrypt before storage.

    Used in: AuthenticationRequest during login/registration

    Example:
    {
        "password": "secure-password-here"
    }

    Attributes:
        password (str): User password for authentication
    """

    password: str = Field(
        ...,
        description="User password per spec - "
        "Per spec: Will be bcrypt hashed before storage",
        min_length=1,
        max_length=255,
    )


class AuthenticationRequest(BaseModel):
    """Authentication request per OpenAPI spec Section 3.2.2.

    Per spec AuthenticationRequest object:
    Used for both login and registration.
    Contains user info and authentication secret.

    Endpoints:
    - POST /auth/register: Register new user
    - PUT /auth/authenticate: Login with existing user

    Per spec response: Returns AuthenticationToken with bearer token

    Example request:
    {
        "user": {
            "name": "alice@example.com",
            "is_admin": false
        },
        "secret": {
            "password": "secure-password"
        }
    }

    Attributes:
        user (User): User identification and info
        secret (UserAuthenticationInfo): Authentication credential (password)
    """

    user: User = Field(
        ..., description="User object per spec - " "Contains name and is_admin flag"
    )
    secret: UserAuthenticationInfo = Field(
        ...,
        description="Authentication secret per spec - " "Contains password credential",
    )


class AuthenticationToken(BaseModel):
    """Authentication response token per OpenAPI spec.

    Per spec AuthenticationToken object:
    Returned from login/registration endpoints.
    Contains JWT bearer token for authenticated requests.

    Per spec: Token format is "bearer <jwt>"
    - Prefix "bearer " indicates authentication type
    - Followed by JWT token

    Usage: Include in X-Authorization header for subsequent requests
    Per spec: X-Authorization: bearer <token>

    Example response:
    {
        "token": "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }

    Attributes:
        token (str): JWT bearer token in "bearer <jwt>" format
                     Per spec: Must include "bearer " prefix
    """

    token: str = Field(
        ...,
        description='JWT Bearer token in format "bearer <jwt>" '
        "per spec AuthenticationToken object. "
        "Include in X-Authorization header for authenticated requests.",
    )


# ============================================================================
# AUDIT SCHEMAS (Per Spec GET /artifact/{type}/{id}/audit endpoint)
# ============================================================================


class AuditEntry(BaseModel):
    """Single audit trail entry per OpenAPI spec.

    Per spec: GET /artifact/{type}/{id}/audit returns paginated list
    of these entries showing mutation history.

    Per spec actions allowed:
    - CREATE: Artifact was registered
    - UPDATE: Artifact metadata/URL changed
    - DOWNLOAD: Artifact was downloaded
    - RATE: Artifact was rated (scoring endpoints)
    - AUDIT: Audit trail was queried

    Example response:
    {
        "user": {
            "name": "alice@example.com",
            "is_admin": false
        },
        "date": "2025-11-11T15:30:45Z",
        "artifact": {
            "name": "bert-base-uncased",
            "id": "550e8400e29b41d4a716446655440000",
            "type": "model"
        },
        "action": "DOWNLOAD"
    }

    Attributes:
        user (User): Who performed the action
        date (datetime): ISO-8601 UTC timestamp when action occurred
        artifact (ArtifactMetadata): Which artifact was affected
        action (str): Type of action (CREATE, UPDATE, DOWNLOAD, RATE, AUDIT)
    """

    model_config = ConfigDict(from_attributes=True)

    user: User = Field(..., description="User who performed the action")
    date: datetime = Field(
        ...,
        description="ISO-8601 UTC datetime when action occurred "
        "per spec audit trail format",
    )
    artifact: ArtifactMetadata = Field(
        ..., description="Artifact that was affected by this action"
    )
    action: str = Field(
        ...,
        description="Type of action per spec - "
        "Must be one of: CREATE, UPDATE, DOWNLOAD, RATE, AUDIT",
        json_schema_extra={"enum": ["CREATE", "UPDATE", "DOWNLOAD", "RATE", "AUDIT"]},
    )


# ============================================================================
# LINEAGE SCHEMAS (Per Spec GET /artifact/model/{id}/lineage endpoint)
# ============================================================================


class ArtifactLineageNode(BaseModel):
    """Node in artifact lineage graph per OpenAPI spec.

    Per spec: Represents a single artifact in the lineage dependency graph.
    Used to show how artifacts depend on and build upon each other.

    Example: ML model depends on dataset which depends on source data.

    Per spec lineage tracking:
    - artifact_id: Which artifact is this node
    - name: Artifact name (convenience field)
    - source: How was this artifact discovered (e.g., from config.json)
    - metadata: Additional context (optional)

    Example node:
    {
        "artifact_id": "550e8400e29b41d4a716446655440000",
        "name": "training-dataset",
        "source": "config_json",
        "metadata": {"version": "1.0", "source_url": "..."}
    }

    Attributes:
        artifact_id (str): ID of the artifact this node represents
        name (str): Artifact name
        source (str): How was artifact discovered
        metadata (dict): Optional additional context
    """

    model_config = ConfigDict(from_attributes=True)

    artifact_id: str = Field(..., description="Artifact ID for this lineage node")
    name: str = Field(..., description="Artifact name (from metadata)")
    source: str = Field(
        ..., description="How node was discovered (e.g., config_json, readme, etc.)"
    )
    metadata: Optional[dict] = Field(
        None, description="Optional additional metadata about this node"
    )


class ArtifactLineageEdge(BaseModel):
    """Edge in artifact lineage graph per OpenAPI spec.

    Per spec: Represents a dependency relationship between two artifacts.
    Shows that one artifact depends on or builds upon another.

    Example edges:
    - Model depends on Dataset
    - Dataset depends on Source Data
    - Code depends on Library

    Per spec lineage tracking:
    - from_node_artifact_id: Upstream artifact (dependency)
    - to_node_artifact_id: Downstream artifact (depends on)
    - relationship: Description of relationship

    Example edge:
    {
        "from_node_artifact_id": "550e8400e29b41d4a716446655440000",
        "to_node_artifact_id": "a4b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
        "relationship": "trained_on"
    }

    Attributes:
        from_node_artifact_id (str): Upstream dependency
        to_node_artifact_id (str): Downstream dependent
        relationship (str): Description of dependency
    """

    from_node_artifact_id: str = Field(
        ..., description="Upstream artifact ID (dependency)"
    )
    to_node_artifact_id: str = Field(
        ..., description="Downstream artifact ID (depends on upstream)"
    )
    relationship: str = Field(
        ..., description="Relationship description (e.g., trained_on, depends_on)"
    )


class ArtifactLineageGraph(BaseModel):
    """Complete lineage graph for artifact per OpenAPI spec.

    Per spec: GET /artifact/model/{id}/lineage returns this structure
    showing complete dependency graph for a model.

    Per spec lineage tracking:
    - nodes: List of all artifacts in the graph
    - edges: List of all dependencies between artifacts

    This enables:
    1. Tracking model provenance
    2. Understanding artifact dependencies
    3. Compliance auditing
    4. Impact analysis

    Example response:
    {
        "nodes": [
            {"artifact_id": "...", "name": "training-data", "source": "..."},
            {"artifact_id": "...", "name": "model", "source": "..."}
        ],
        "edges": [
            {
                "from_node_artifact_id": "...",
                "to_node_artifact_id": "...",
                "relationship": "trained_on"
            }
        ]
    }

    Attributes:
        nodes (List[ArtifactLineageNode]): All artifacts in graph
        edges (List[ArtifactLineageEdge]): All dependencies
    """

    nodes: List[ArtifactLineageNode] = Field(
        ..., description="Artifacts in lineage graph per spec"
    )
    edges: List[ArtifactLineageEdge] = Field(
        ..., description="Dependencies between artifacts per spec"
    )


# ============================================================================
# REGEX SEARCH SCHEMA (Per Spec POST /artifact/byRegEx endpoint)
# ============================================================================


class ArtifactRegEx(BaseModel):
    """Regular expression search request per OpenAPI spec.

    Per spec: POST /artifact/byRegEx endpoint accepts this schema
    for searching artifacts by regex pattern over names and READMEs.

    Example request:
    {
        "regex": ".*?(audience|bert).*"
    }

    Attributes:
        regex (str): Regular expression pattern for searching artifacts
    """

    regex: str


# ============================================================================
# LEGACY SCHEMAS (Deprecated - for backward compatibility during migration)
# ============================================================================

# These schemas were used by the old implementation and are kept for
# reference during the migration to the new spec-compliant schemas.
# NEW CODE SHOULD NOT USE THESE - use Artifact envelope instead.


class ModelResponse(BaseModel):
    """DEPRECATED: Use Artifact instead.

    This schema is from the old implementation that didn't follow spec.
    Kept only for reference during migration.

    Per NEW spec: Use Artifact envelope with metadata/data structure.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    url: str = Field(alias="model_url")
    type: str = Field(alias="artifact_type")


class UploadResponse(BaseModel):
    """DEPRECATED: Use Artifact instead.

    This schema is from the old implementation that didn't follow spec.
    Kept only for reference during migration.

    Per NEW spec: Use Artifact envelope with metadata/data structure.
    """

    message: str
    model_id: str
    model_url: str
    artifact_type: str