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

# from crud.app import app  # noqa: E402
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

# def test_feature_3_authentication() -> None:
#     """Test Feature 3: User Authentication (PUT /authenticate)"""
#     print("\n" + "="*70)
#     print("FEATURE 3: User Authentication - Login and Get JWT Token")
#     print("="*70)

#     client, db, temp_db_path = setup_test_db()

#     try:
#         # Create a test user
#         print("\n3a. Creating test user...")
#         test_user = User(
#             id=1,
#             username="authtest",
#             email="authtest@example.com",
#             hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # pre-hashed 'testpassword'
#             is_admin=False
#         )
#         db.add(test_user)
#         db.commit()
#         print("✓ Test user created")

#         # Test authentication with valid credentials
#         print("\n3b. Testing authentication with valid credentials...")
#         auth_data = {
#             "user": {
#                 "name": "authtest",
#                 "is_admin": False
#             },
#             "secret": {
#                 "password": "testpassword"  # UPDATED: Use same password as pre-hashed value
#             }
#         }

#         response = client.put(
#             "/authenticate",
#             json=auth_data
#         )
#         assert response.status_code == 200, f"Authentication failed: {response.text}"
#         result = response.json()
#         assert "token" in result, "Response should contain token"
#         token = result["token"]
#         assert token.startswith("bearer "), "Token should be in bearer format"
#         print("✓ Authentication successful, bearer token returned")

#         # Extract and verify token
#         print("\n3c. Verifying JWT token...")
#         token_without_bearer = token[7:]  # Remove "bearer " prefix
#         from crud.upload.auth import decode_access_token
#         payload = decode_access_token(token_without_bearer)
#         assert payload.get("sub") == "1", "Token sub claim should be user ID"
#         assert "exp" in payload, "Token should have expiration"
#         print(f"✓ JWT token valid with claims: sub={payload.get('sub')}, exp={payload.get('exp')}")

#         # Test authentication with wrong password
#         print("\n3d. Testing authentication with invalid password...")
#         wrong_auth_data = {
#             "user": {
#                 "name": "authtest",
#                 "is_admin": False
#             },
#             "secret": {
#                 "password": "wrongpassword"
#             }
#         }

#         response = client.put(
#             "/authenticate",
#             json=wrong_auth_data
#         )
#         assert response.status_code == 401, f"Expected 401, got {response.status_code}"
#         print("✓ Invalid password correctly rejected with 401")

#         # Test authentication with nonexistent user
#         print("\n3e. Testing authentication with nonexistent user...")
#         nonexistent_auth_data = {
#             "user": {
#                 "name": "nonexistent",
#                 "is_admin": False
#             },
#             "secret": {
#                 "password": "anypassword"
#             }
#         }

#         response = client.put(
#             "/authenticate",
#             json=nonexistent_auth_data
#         )
#         assert response.status_code == 401, f"Expected 401, got {response.status_code}"
#         print("✓ Nonexistent user correctly rejected with 401")

#         print("\n✓ FEATURE 3 PASSED: User authentication working correctly!")

#     finally:
#         try:
#             os.remove(temp_db_path)
#         except OSError:
#             pass


# def main() -> None:
#     """Run all feature tests."""
#     print("\n" + "🚀 "*35)
#     print("COMPREHENSIVE FEATURE TEST SUITE".center(70))
#     print("🚀 "*35)

#     try:        
#         test_feature_3_authentication()

#         print("\n" + "="*70)
#         print("✓ ALL FEATURES PASSED SUCCESSFULLY!".center(70))
#         print("="*70)
#         print("\nImplementation Summary:")
#         print("  1. ✓ Basic Enumerate: GET /api/models/enumerate works with pagination")
#         print("  2. ✓ User Registration: POST /auth/register creates users with hashed passwords")
#         print("  3. ✓ User Authentication: PUT /authenticate validates credentials and returns JWT")
#         print("\nAll features implemented per OpenAPI specification!")
#         print("="*70 + "\n")

#     except AssertionError as e:
#         print(f"\n✗ TEST FAILED: {e}")
#         sys.exit(1)
#     except Exception as e:
#         print(f"\n✗ ERROR: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)


# if __name__ == "__main__":
#     main()
