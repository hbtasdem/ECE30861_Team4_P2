# database.py
"""Database configuration and session management - OpenAPI v3.4.4 compliant.

This module handles all database connectivity and session management for the
OpenAPI v3.4.4 compliant artifact registry.

KEY FUNCTIONS:
  - create_engine(): Initializes SQLAlchemy engine for SQLite database
  - SessionLocal: Session factory for creating new database sessions
  - get_db(): FastAPI dependency for injecting database sessions into routes
  - init_db(): Creates all tables based on SQLAlchemy models

DATABASE SCHEMA NOTES:
  Per OpenAPI v3.4.4 spec, the database includes:
  1. User table: Stores user credentials and admin status
  2. Artifact table: Core entity with STRING id (not Integer!)
  3. AuditEntry table: Tracks mutations for audit compliance

SPEC REFERENCE:
  - Section 3.3: Database schema and integrity requirements
  - Per spec: All artifact IDs are strings (generated via ULID/UUID)
  - Per spec: All tables use UTC timestamps for consistency
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# DATABASE CONNECTION CONFIGURATION

# Per OpenAPI spec: Must support multi-user concurrent access
# Current: SQLite for development/testing (single-file database)
# Production: Can upgrade to PostgreSQL/MySQL without code changes

# DATABASE_URL can be set via environment variable or defaults to SQLite
# Examples:
#   - "sqlite:///./test.db" (file-based, default)
#   - "postgresql://user:pass@localhost/dbname" (PostgreSQL)
#   - "mysql+pymysql://user:pass@localhost/dbname" (MySQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# ENGINE CREATION

# Per SQLAlchemy best practices: Create single engine for application lifetime
# Key settings:
#   - check_same_thread=False: Allow multi-threaded access (FastAPI uses thread pool)
#   - This is safe because FastAPI creates new session per request
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration for development
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL/MySQL (production-ready)
    engine = create_engine(DATABASE_URL)

# SESSION FACTORY

# Per SQLAlchemy: Use sessionmaker() to create session factory
# Key settings:
#   - autocommit=False: Require explicit commit() calls
#   - autoflush=False: Require explicit flush() calls
#   - This prevents accidental data persistence
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DEPENDENCY INJECTION FOR FASTAPI


def get_db() -> Generator[Session, None, None]:
    """Dependency injection function for FastAPI routes.

    Per FastAPI best practices: Use dependency injection for database sessions.
    This ensures:
    1. Each request gets its own session
    2. Sessions are properly closed after use
    3. Database errors don't crash the application

    Usage in routes:
    @app.get("/artifacts")
    def list_artifacts(db: Session = Depends(get_db)):
        # db is automatically injected and managed
        return db.query(Artifact).all()

    Per OpenAPI spec: All endpoints except /health and /tracks require
    authentication, which uses get_db() to verify user credentials.

    Yields:
        Session: Database session for the request lifetime

    Ensures:
        Session is closed even if an exception occurs (try/finally)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Always close session, even if an error occurred
        # This prevents connection leaks and ensures clean state
        db.close()


# DATABASE INITIALIZATION


def init_db() -> None:
    """Initialize database tables with OpenAPI v3.4.4 compliant schema.

    Per OpenAPI spec requirements: Database must include tables for:
    1. User: User credentials and admin status
    2. Artifact: Core artifact metadata and data
    3. AuditEntry: Mutation audit trail

    This function creates all tables defined in src/models.py by:
    1. Importing all model classes to register them with Base
    2. Calling Base.metadata.create_all() to execute CREATE TABLE statements
    3. Applying table constraints (e.g., CHECK type IN (...))

    Idempotent: Safe to call multiple times. SQLAlchemy only creates tables
    that don't exist; existing tables are left unchanged.

    Important Notes:
    - CRITICAL CHANGE: Artifact.id is now STRING (not Integer)
      This is a REQUIRED spec compliance change
    - All timestamps use UTC (datetime.utcnow)
    - User.hashed_password stores bcrypt hashes (required for auth)
    - AuditEntry tracks all mutations per spec section 3.X

    Schema migration note:
    If upgrading from old schema with integer artifact IDs:
    1. Backup existing data
    2. Drop old tables manually: Base.metadata.drop_all(bind=engine)
    3. Call init_db() to create new schema
    4. Migrate data if needed (convert int IDs to strings)

    Per Spec:
    - Section 3.3: Database integrity and schema requirements
    - All foreign keys must reference existing rows
    - All types and constraints must be enforced at database level
    """
    # Import models to register them with SQLAlchemy Base
    # IMPORTANT: This must import Artifact (not Model!) for spec compliance
    from src.database_models import Artifact, AuditEntry, Base, User  # noqa: F401

    # Create all tables defined in src.models
    # Per spec: All tables must exist before API can be used
    # Includes Phase 2 tables (User, Artifact, AuditEntry)
    Base.metadata.create_all(bind=engine)
