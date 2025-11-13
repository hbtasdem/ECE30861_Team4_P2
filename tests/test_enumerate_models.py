# #!/usr/bin/env python3
# """
# Comprehensive test script demonstrating all three implemented features:
# 1. Basic enumerate (GET /api/models/enumerate) - directory of all models
# 2. User registration (POST /auth/register) - create new user with hashed password
# 3. User authentication (PUT /authenticate) - login and get JWT token
# """

# import os
# import sys
# import tempfile
# from pathlib import Path
# from typing import Generator, Tuple

# # Add project root to path
# project_root = Path(__file__).parent
# sys.path.insert(0, str(project_root))

# os.environ["TESTING"] = "true"

# from fastapi.testclient import TestClient  # noqa: E402
# from sqlalchemy import create_engine  # noqa: E402
# from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

# from crud.upload.app import app  # noqa: E402
# from crud.upload.auth import create_access_token, verify_password  # noqa: E402
# from src.database import get_db  # noqa: E402
# from ECE30861_Team4_P2.src.artifact_definitions import Base, User  # noqa: E402


# def setup_test_db() -> Tuple[TestClient, Session, str]:
#     """Create test database and return client."""
#     temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
#     temp_db_path = temp_db.name
#     temp_db.close()

#     engine = create_engine(
#         f"sqlite:///{temp_db_path}",
#         connect_args={"check_same_thread": False}
#     )
#     Base.metadata.create_all(engine)

#     TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     db = TestingSessionLocal()

#     def override_get_db() -> Generator[Session, None, None]:
#         yield db

#     app.dependency_overrides[get_db] = override_get_db

#     return TestClient(app), db, temp_db_path


# def test_feature_1_enumerate() -> None:
#     """Test Feature 1: Basic Enumerate (GET /api/models/enumerate)"""
#     print("\n" + "="*70)
#     print("FEATURE 1: Basic Enumerate - Directory of All Models")
#     print("="*70)

#     client, db, temp_db_path = setup_test_db()

#     try:
#         # Test enumerate empty list
#         print("\n1a. Testing enumerate with no models...")
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200, f"Expected 200, got {response.status_code}"
#         data = response.json()
#         assert isinstance(data, list), "Response should be a list"
#         assert len(data) == 0, "Should be empty"
#         print("✓ Enumerate returns empty list when no models exist")

#         # Create a test user first
#         print("\n1b. Uploading test models...")
#         test_user = User(
#             id=1,
#             username="testuser",
#             email="test@example.com",
#             hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # pre-hashed 'testpassword'
#             is_admin=False
#         )
#         db.add(test_user)
#         db.commit()
#         print("✓ Test user created")

#         # Generate test token
#         token = create_access_token(data={"sub": "1", "is_admin": False})
#         headers = {"X-Authorization": f"bearer {token}"}

#         for i in range(3):
#             response = client.post(
#                 "/api/models/upload",
#                 data={
#                     "name": f"TestModel{i}",
#                     "model_url": f"https://example.com/model{i}.zip",
#                     "version": f"1.{i}.0",
#                 },
#                 headers=headers
#             )
#             assert response.status_code == 200, f"Upload failed: {response.text}"
#             print(f"  ✓ Uploaded model {i}")

#         # Test enumerate with models
#         print("\n1c. Testing enumerate with models...")
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200, f"Expected 200, got {response.status_code}"
#         models = response.json()
#         assert len(models) == 3, f"Expected 3 models, got {len(models)}"
#         print(f"✓ Enumerate returns all {len(models)} models")

#         # Test pagination
#         print("\n1d. Testing enumerate with pagination...")
#         response = client.get("/api/models/enumerate?skip=0&limit=2")
#         assert response.status_code == 200
#         models = response.json()
#         assert len(models) == 2, f"Expected 2 models with limit=2, got {len(models)}"
#         print(f"✓ Enumerate respects pagination (limit=2 returned {len(models)} models)")

#         # Test skip
#         response = client.get("/api/models/enumerate?skip=1&limit=10")
#         models = response.json()
#         assert len(models) == 2, f"Expected 2 models after skip=1, got {len(models)}"
#         print(f"✓ Enumerate respects skip parameter (skip=1 returned {len(models)} models)")

#         print("\n✓ FEATURE 1 PASSED: Enumerate working correctly!")

#     finally:
#         try:
#             os.remove(temp_db_path)
#         except OSError:
#             pass
