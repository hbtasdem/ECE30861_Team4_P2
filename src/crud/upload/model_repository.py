"""Database repository layer - Phase 2 artifact CRUD data access.Per OpenAPI v3.4.4 Section 3.2.1 - Artifact Object Management

FILE PURPOSE:
Provides abstraction layer for artifact database operations using SQLAlchemy ORM.
Acts as bridge between FastAPI routes and database models per repository pattern.
Isolates data access logic from business logic for maintainability.

CORE OPERATIONS:

1. create_model(model_data: ModelCreate, uploader_id: int) → Artifact
   Purpose: Insert new artifact record into database
   Implementation:
   - Generates ULID string ID per spec pattern ^[a-zA-Z0-9\\-]+$
   - Creates Artifact ORM instance with all required metadata
   - Commits to database transaction
   - Returns created Artifact object with generated ID
   HTTP Context: Called by POST /api/models/upload endpoint (201 Created)

2. get_model_by_id(model_id: int) → Optional[Artifact]
   Purpose: Retrieve single artifact by ID from database
   Implementation:
   - Queries artifacts table for matching ID
   - Returns full Artifact ORM object if found
   - Returns None if not found (caller handles 404)
   - Used by GET /api/models/{id} and other retrieval endpoints

3. get_all_models(skip: int = 0, limit: int = 100) → List[Artifact]
   Purpose: Retrieve all artifacts with pagination support
   Implementation:
   - Queries artifacts table with OFFSET and LIMIT
   - Returns list of Artifact ORM objects
   - Used by GET /api/models/enumerate endpoint
   - Supports sorting and filtering at routes layer

ULID GENERATION:
- Library: ulid-py (ULID specification compliant)
- Format: 26 alphanumeric characters
- Uniqueness: Globally unique, collision probability < 1 in 2^80
- Timestamp: Embedded sortable timestamp (millisecond precision)
- Spec Compliance: Pattern "^[a-zA-Z0-9\\-]+$"

Example ULID: 01K9ZBPCEQM0CK4X2T984FX8CS
  └─ Timestamp (48 bits): 01K9ZBPC
  └─ Randomness (80 bits): EQM0CK4X2T984FX8CS

DATABASE INTEGRATION:
- ORM: SQLAlchemy declarative models (src/database_models.py)
- Session: SQLAlchemy Session injected via dependency (src/database.py)
- Transaction: Automatic commit/rollback via context manager
- Models: Artifact (PK: id STRING), User (FK), AuditEntry (FK)

ERROR HANDLING:
- SQLAlchemy IntegrityError: Caught and converted to HTTPException
- Constraint violations: Returned as 400/422 status codes
- Database unavailable: 500 Internal Server Error

SPEC SECTIONS REFERENCED:
- Section 3.2.1: Artifact object structure and requirements
- Section 3.2.2: User relationships and authentication
- Section 3.3: Database schema constraints and relationships
"""

from typing import Optional

from sqlalchemy.orm import Session
from ulid import ULID

from src.crud.upload.artifacts import ModelCreate
from src.database_models import Artifact


class ModelRepository:
    """Repository for upload operations (Create, Read)."""

    def __init__(self, db: Session):
        self.db = db

    def create_model(self, model_data: ModelCreate, uploader_id: int) -> Artifact:
        """Create a new model record in database with URL reference.

        Args:
            model_data: ModelCreate schema with model details and URL
            uploader_id: ID of the user uploading the model

        Returns:
            Created Artifact object
        """
        db_model = Artifact(
            id=str(ULID()),  # Generate ULID per spec - artifact ID must be string
            name=model_data.name,
            url=model_data.url,
            download_url=f"/api/artifacts/download/{str(ULID())}",  # Per spec: download endpoint
            type="model",  # Per spec: type constraint
            uploader_id=uploader_id,
        )

        self.db.add(db_model)
        self.db.commit()
        return db_model

    def get_model_by_id(self, model_id: int) -> Optional[Artifact]:
        """Get model by ID.

        Args:
            model_id: ID of the model

        Returns:
            Artifact object if found, None otherwise
        """
        return self.db.query(Artifact).filter(Artifact.id == model_id).first()

    def get_all_models(self, skip: int = 0, limit: int = 100) -> list[Artifact]:
        """Get all models with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Artifact objects
        """
        return self.db.query(Artifact).offset(skip).limit(limit).all()
