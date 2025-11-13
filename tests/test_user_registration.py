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

# from ECE30861_Team4_P2.crud.app import app  # noqa: E402
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


# def test_feature_2_registration() -> None:
#     """Test Feature 2: User Registration (POST /auth/register)"""
#     print("\n" + "="*70)
#     print("FEATURE 2: User Registration - Create New User")
#     print("="*70)

#     client, db, temp_db_path = setup_test_db()

#     try:
#         # Test registration with valid data
#         print("\n2a. Testing user registration with valid credentials...")
#         registration_data = {
#             "user": {
#                 "name": "newuser",
#                 "is_admin": False
#             },
#             "secret": {
#                 "password": "securepassword123"
#             }
#         }

#         response = client.post(
#             "/auth/register",
#             json=registration_data
#         )
#         assert response.status_code == 200, f"Registration failed: {response.text}"
#         result = response.json()
#         assert "token" in result, "Response should contain token"
#         assert result["token"].startswith("bearer "), "Token should be in bearer format"
#         print("✓ User registered successfully with bearer token returned")

#         # Verify user was created in database
#         print("\n2b. Verifying user was created in database...")
#         user = db.query(User).filter(User.username == "newuser").first()
#         assert user is not None, "User should be created in database"
#         assert user.email == "newuser", "Email should match username"
#         print("✓ User 'newuser' created in database with hashed password")

#         # Verify password was hashed correctly
#         print("\n2c. Verifying password was hashed...")
#         assert verify_password("securepassword123", str(user.hashed_password)), "Password verification failed"
#         print("✓ Password hashed and verifiable")

#         # Test registration with duplicate user (should fail)
#         print("\n2d. Testing duplicate registration (should fail)...")
#         response = client.post(
#             "/auth/register",
#             json=registration_data
#         )
#         assert response.status_code == 409, f"Expected 409, got {response.status_code}"
#         print("✓ Duplicate registration correctly rejected with 409")

#         print("\n✓ FEATURE 2 PASSED: User registration working correctly!")

#     finally:
#         try:
#             os.remove(temp_db_path)
#         except OSError:
#             pass
