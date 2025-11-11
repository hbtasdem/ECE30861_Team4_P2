# """Pytest configuration and fixtures for the entire test suite."""

# import os
# import sys
# import tempfile
# from pathlib import Path
# from typing import Any, Generator

# # Set testing mode BEFORE any imports
# os.environ["TESTING"] = "true"

# # Add project root to path
# project_root = Path(__file__).parent.parent.parent.parent  # Go from crud/upload/tests to project root
# sys.path.insert(0, str(project_root))

# import pytest  # noqa: E402
# from sqlalchemy import create_engine  # noqa: E402
# from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

# from crud.upload.auth import create_access_token  # noqa: E402
# from ECE30861_Team4_P2.src.artifact_definitions import Base, User  # noqa: E402


# @pytest.fixture(scope="function")
# def test_db() -> Generator[Session, None, None]:
#     """Create a temporary file-based SQLite database for each test."""
#     # Create temporary database file
#     temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
#     temp_db_path = temp_db.name
#     temp_db.close()

#     # Create file-based engine (more compatible with ThreadPoolExecutor used by TestClient)
#     engine = create_engine(
#         f"sqlite:///{temp_db_path}",
#         connect_args={"check_same_thread": False}
#     )

#     # Create all tables
#     Base.metadata.create_all(engine)

#     # Create session
#     TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     db = TestingSessionLocal()

#     # Create test user with hashed password  # UPDATED: Add hashed_password
#     # UPDATED: Using pre-computed bcrypt hash to avoid Windows bcrypt backend issues
#     test_user = User(
#         id=1,
#         username="testuser",
#         email="test@example.com",
#         hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # UPDATED: Pre-hashed 'testpassword'
#         is_admin=False
#     )
#     db.add(test_user)
#     db.commit()

#     yield db
#     db.close()

#     # Cleanup temporary database file
#     try:
#         os.remove(temp_db_path)
#     except Exception:
#         pass


# @pytest.fixture(scope="function")
# def test_token() -> str:  # UPDATED: New fixture to generate test JWT token
#     """Generate a test JWT token for authentication."""
#     token = create_access_token(data={"sub": "1", "is_admin": False})
#     return f"bearer {token}"  # UPDATED: Return in bearer format


# @pytest.fixture(scope="function")
# def client(test_db: Session) -> Generator[Any, None, None]:
#     """Create a FastAPI TestClient with dependency overrides."""
#     from fastapi.testclient import TestClient

#     from crud.app import app
#     from crud.upload.auth import get_current_user
#     from crud.upload.routes import get_current_user_with_auth  # UPDATED: Import helper function
#     from src.database import get_db
#     from ECE30861_Team4_P2.src.artifact_definitions import User

#     # UPDATED: Create test user with hashed_password to match database schema
#     test_user = User(
#         id=1,
#         username="testuser",
#         email="test@example.com",
#         hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # UPDATED: Pre-hashed 'testpassword'
#         is_admin=False
#     )

#     def override_get_db() -> Generator[Session, None, None]:
#         yield test_db

#     def override_get_current_user() -> User:
#         return test_user

#     async def override_get_current_user_with_auth() -> User:  # UPDATED: Override helper function too
#         return test_user

#     # Apply overrides
#     app.dependency_overrides[get_db] = override_get_db
#     app.dependency_overrides[get_current_user] = override_get_current_user
#     app.dependency_overrides[get_current_user_with_auth] = override_get_current_user_with_auth  # UPDATED: Override helper

#     # Create client
#     client = TestClient(app)

#     yield client

#     # Cleanup
#     app.dependency_overrides.clear()
