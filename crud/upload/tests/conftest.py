"""Pytest configuration and fixtures for the entire test suite."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Generator

# Set testing mode BEFORE any imports
os.environ["TESTING"] = "true"

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent  # Go from crud/upload/tests to project root
sys.path.insert(0, str(project_root))

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from src.models import Base, User  # noqa: E402


@pytest.fixture(scope="function")  # type: ignore[misc]
def test_db() -> Generator[Session, None, None]:
    """Create a temporary file-based SQLite database for each test."""
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db_path = temp_db.name
    temp_db.close()

    # Create file-based engine (more compatible with ThreadPoolExecutor used by TestClient)
    engine = create_engine(
        f"sqlite:///{temp_db_path}",
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Create test user
    test_user = User(id=1, username="testuser", email="test@example.com", is_admin=False)
    db.add(test_user)
    db.commit()

    yield db
    db.close()

    # Cleanup temporary database file
    try:
        os.remove(temp_db_path)
    except Exception:
        pass


@pytest.fixture(scope="function")  # type: ignore[misc]
def client(test_db: Session) -> Generator[Any, None, None]:
    """Create a FastAPI TestClient with dependency overrides."""
    from fastapi.testclient import TestClient

    from crud.upload.app import app
    from crud.upload.auth import get_current_user
    from src.database import get_db
    from src.models import User

    test_user = User(id=1, username="testuser", email="test@example.com", is_admin=False)

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
