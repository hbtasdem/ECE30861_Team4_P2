# tests/conftest.py
import pytest
import tempfile
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# IMPORTANT: Import database AFTER setting DATABASE_URL env var
import database
from database import get_db, engine, SessionLocal
from models import Base, User
from auth import set_test_user, clear_test_user
from upload.services.file_service import FileStorageService

# Mock the file service
from upload import routes as upload_routes


# Set testing flag and test database URL BEFORE importing app
os.environ["TESTING"] = "true"
# Use sqlite:///file: URI so multiple connections share the same in-memory DB
os.environ["DATABASE_URL"] = "sqlite:///file::memory:?uri=true&cache=shared"


# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test database tables once for entire session"""
    Base.metadata.create_all(bind=engine)
    yield
    # Note: Don't drop tables; keep DB for inspection after tests


@pytest.fixture
def clear_db_between_tests():
    """Clear data between tests (but keep schema)"""
    yield
    # Delete all data between tests
    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(text(f"DELETE FROM {table.name}"))
    db.commit()
    db.close()


@pytest.fixture
def temp_upload_dir():
    """Create a temporary directory for file uploads"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_db_session(clear_db_between_tests):
    """Create a fresh test database session for each test"""
    db = SessionLocal()

    # Create test user
    test_user = User(
        id=1, username="testuser", email="test@example.com", is_admin=False
    )
    db.add(test_user)
    db.commit()

    yield db, test_user

    # Cleanup
    db.rollback()
    db.close()


@pytest.fixture
def mock_file_service(temp_upload_dir):
    """Mock file service that uses temporary directory"""
    service = FileStorageService(upload_dir=temp_upload_dir)
    return service


@pytest.fixture
def client(test_db_session, mock_file_service, monkeypatch):
    """FastAPI test client with mocked dependencies"""
    db, test_user = test_db_session

    # Import app AFTER database is setup
    from app import app as fastapi_app

    def override_get_db():
        """Override to use test DB session"""
        try:
            yield db
        finally:
            pass  # Don't close - let fixture handle it

    fastapi_app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(upload_routes, "file_service", mock_file_service)

    # Set current user
    set_test_user(test_user)

    test_client = TestClient(fastapi_app)

    yield test_client

    # Clean up
    clear_test_user()
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Return authorization headers (mock)"""
    return {}
