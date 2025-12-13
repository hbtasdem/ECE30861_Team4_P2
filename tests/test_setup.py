"""Test fixtures and setup for comprehensive test suite.

Per OpenAPI v3.4.4 - Testing Infrastructure

PURPOSE:
Provides pytest fixtures and configuration for testing all API endpoints.
Sets up test database, authentication, and FastAPI TestClient with dependencies.

FIXTURES PROVIDED:

1. test_db() → Session
   Purpose: Temporary SQLite database for each test
   Scope: Function (created/destroyed per test)
   Setup:
   - Creates temp file-based SQLAlchemy SQLite database
   - Runs all table migrations (Base.metadata.create_all)
   - Creates test user with hashed password
   - Yields session for test use
   Cleanup:
   - Closes session
   - Deletes temporary database file

   Usage in tests:
   def test_something(test_db: Session):
       artifact = Artifact(...)
       test_db.add(artifact)
       test_db.commit()

2. test_token() → str
   Purpose: Generate JWT authentication token
   Scope: Function
   Implementation:
   - Creates JWT token for user ID 1
   - Returns in bearer format: "bearer <JWT>"
   - Token valid for 30 minutes
   - Non-admin user

   Usage in tests:
   headers = {"X-Authorization": test_token}
   response = client.get("/protected", headers=headers)

3. client(test_db) → TestClient
   Purpose: FastAPI TestClient with dependency overrides
   Scope: Function
   Dependencies Overridden:
   - get_db() → test_db (test database session)
   - get_current_user() → test user (authenticated)

   Setup:
   - Loads FastAPI app from src.crud.app
   - Creates test user with ID 1
   - Registers dependency overrides
   - Creates TestClient instance
   Cleanup:
   - Clears all dependency overrides

   Usage in tests:
   def test_upload(client: TestClient):
       response = client.post("/api/models/upload", data={...})
       assert response.status_code == 200

4. db(test_db) → Session
   Purpose: Alias for test_db fixture
   Scope: Function
   Reason: Convenience for consistent naming

   Usage in tests:
   def test_query(db: Session):
       models = db.query(Artifact).all()

TEST USER CREDENTIALS:
    id: 1
    username: "testuser"
    email: "test@example.com"
    hashed_password: (bcrypt hash of "testpassword")
    is_admin: False

TEST DATABASE:
    Backend: SQLite (file-based)
    Path: Temporary file (auto-deleted)
    Thread Safety: Configured with check_same_thread=False
    Transactions: Full ACID guarantees

DEPENDENCY INJECTION PATTERN:

    Normal (Production):
    @app.get("/api/models")
    def get_models(db: Session = Depends(get_db)):
        return db.query(Artifact).all()

    Test (With Overrides):
    app.dependency_overrides[get_db] = lambda: test_db
    response = client.get("/api/models")
    # Uses test_db instead of production db

AUTHENTICATION IN TESTS:
    Option 1: Use client fixture (auto-authenticated)
        response = client.get("/protected")  # Works (authenticated)

    Option 2: Manual header with token
        headers = {"X-Authorization": test_token}
        response = client.get("/protected", headers=headers)

    Option 3: No auth (for public endpoints)
        response = client.get("/api/models/enumerate")  # No auth needed

BEST PRACTICES:
    1. Use fixture names in function signature
    2. Fixtures auto-injected by pytest
    3. Each test gets fresh database (isolation)
    4. No test data bleeds to other tests
    5. Use assertions for validation
    6. Clean up in fixture teardown

EXAMPLE TEST:
    def test_create_artifact(client: TestClient, db: Session):
        # Create artifact in test DB
        artifact = Artifact(
            id="test-id",
            name="test",
            type="model",
            url="https://example.com",
            download_url="http://localhost/download",
            uploader_id=1
        )
        db.add(artifact)
        db.commit()

        # Call API (uses test client)
        response = client.get("/api/models/enumerate")
        assert response.status_code == 200
        assert len(response.json()) >= 1

TROUBLESHOOTING:
    "fixture 'client' not found"
    - Ensure this file is in tests/ directory
    - Ensure pytest can find test_setup.py

    "ModuleNotFoundError: No module named 'src'"
    - Check sys.path manipulation at top of file
    - Verify project structure

    "Database is locked"
    - SQLite concurrency issue
    - Use mutex or queue for parallel tests
    - Or switch to PostgreSQL for testing

SPEC SECTIONS REFERENCED:
    Section 3.1: Authentication (test_token)
    Section 3.2: Model endpoints (client fixture)
    Section 3.3: Database schema (test_db fixture)
    Section 3.4: File upload (client + test_db)

RUN TESTS:
    pytest tests/ -v
    pytest tests/test_upload.py -v
    pytest tests/ -k "test_upload_success"
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Generator

# Set testing mode BEFORE any imports
os.environ["TESTING"] = "true"

# Add project root to path
project_root = Path(
    __file__
).parent.parent.parent.parent  # Go from tests to project root
sys.path.insert(0, str(project_root))

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from src.crud.upload.auth import create_access_token  # noqa: E402
from src.database_models import Base, User  # noqa: E402


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a temporary file-based SQLite database for each test."""
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db_path = temp_db.name
    temp_db.close()

    # Create file-based engine (more compatible with ThreadPoolExecutor used by TestClient)
    engine = create_engine(
        f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Create test user with hashed password
    # Using pre-computed bcrypt hash to avoid Windows bcrypt backend issues
    test_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # Pre-hashed 'testpassword'
        is_admin=False,
    )
    db.add(test_user)
    db.commit()

    yield db
    db.close()

    # Cleanup temporary database file
    try:
        os.remove(temp_db_path)
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_token() -> str:
    """Generate a test JWT token for authentication."""
    token = create_access_token(data={"sub": "1", "is_admin": False})
    return f"bearer {token}"


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[Any, None, None]:
    """Create a FastAPI TestClient with dependency overrides."""
    from fastapi.testclient import TestClient
    from src.crud.app import app
    from src.crud.upload.auth import get_current_user
    from src.database import get_db

    # Create test user with hashed_password to match database schema
    test_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # Pre-hashed 'testpassword'
        is_admin=False,
    )

    def override_get_db() -> Generator[Session, None, None]:
        yield test_db

    def override_get_current_user() -> User:
        return test_user

    # Apply overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create client
    client = TestClient(app)

    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def db(test_db: Session) -> Session:
    """Fixture to provide database session."""
    return test_db
