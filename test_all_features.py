#!/usr/bin/env python3
"""
Comprehensive test script demonstrating all three implemented features:
1. Basic enumerate (GET /api/models/enumerate) - directory of all models
2. User registration (POST /auth/register) - create new user with hashed password
3. User authentication (PUT /authenticate) - login and get JWT token
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

os.environ["TESTING"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile

from crud.upload.app import app
from crud.upload.auth import create_access_token, verify_password
from src.models import Base, User
from src.database import get_db


def setup_test_db():
    """Create test database and return client."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db_path = temp_db.name
    temp_db.close()

    engine = create_engine(
        f"sqlite:///{temp_db_path}",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app), db, temp_db_path


def test_feature_1_enumerate():
    """Test Feature 1: Basic Enumerate (GET /api/models/enumerate)"""
    print("\n" + "="*70)
    print("FEATURE 1: Basic Enumerate - Directory of All Models")
    print("="*70)
    
    client, db, temp_db_path = setup_test_db()
    
    try:
        # Test enumerate empty list
        print("\n1a. Testing enumerate with no models...")
        response = client.get("/api/models/enumerate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 0, "Should be empty"
        print("✓ Enumerate returns empty list when no models exist")
        
        # Create a test user first
        print("\n1b. Uploading test models...")
        test_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # pre-hashed 'testpassword'
            is_admin=False
        )
        db.add(test_user)
        db.commit()
        print("✓ Test user created")
        
        # Generate test token
        token = create_access_token(data={"sub": "1", "is_admin": False})
        headers = {"X-Authorization": f"bearer {token}"}
        
        for i in range(3):
            response = client.post(
                "/api/models/upload",
                data={
                    "name": f"TestModel{i}",
                    "model_url": f"https://example.com/model{i}.zip",
                    "version": f"1.{i}.0",
                },
                headers=headers
            )
            assert response.status_code == 200, f"Upload failed: {response.text}"
            print(f"  ✓ Uploaded model {i}")
        
        # Test enumerate with models
        print("\n1c. Testing enumerate with models...")
        response = client.get("/api/models/enumerate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        models = response.json()
        assert len(models) == 3, f"Expected 3 models, got {len(models)}"
        print(f"✓ Enumerate returns all {len(models)} models")
        
        # Test pagination
        print("\n1d. Testing enumerate with pagination...")
        response = client.get("/api/models/enumerate?skip=0&limit=2")
        assert response.status_code == 200
        models = response.json()
        assert len(models) == 2, f"Expected 2 models with limit=2, got {len(models)}"
        print(f"✓ Enumerate respects pagination (limit=2 returned {len(models)} models)")
        
        # Test skip
        response = client.get("/api/models/enumerate?skip=1&limit=10")
        models = response.json()
        assert len(models) == 2, f"Expected 2 models after skip=1, got {len(models)}"
        print(f"✓ Enumerate respects skip parameter (skip=1 returned {len(models)} models)")
        
        print("\n✓ FEATURE 1 PASSED: Enumerate working correctly!")
        
    finally:
        try:
            os.remove(temp_db_path)
        except:
            pass


def test_feature_2_registration():
    """Test Feature 2: User Registration (POST /auth/register)"""
    print("\n" + "="*70)
    print("FEATURE 2: User Registration - Create New User")
    print("="*70)
    
    client, db, temp_db_path = setup_test_db()
    
    try:
        # Test registration with valid data
        print("\n2a. Testing user registration with valid credentials...")
        registration_data = {
            "user": {
                "name": "newuser",
                "is_admin": False
            },
            "secret": {
                "password": "securepassword123"
            }
        }
        
        response = client.post(
            "/auth/register",
            json=registration_data
        )
        assert response.status_code == 200, f"Registration failed: {response.text}"
        result = response.json()
        assert "token" in result, "Response should contain token"
        assert result["token"].startswith("bearer "), "Token should be in bearer format"
        print("✓ User registered successfully with bearer token returned")
        
        # Verify user was created in database
        print("\n2b. Verifying user was created in database...")
        user = db.query(User).filter(User.username == "newuser").first()
        assert user is not None, "User should be created in database"
        assert user.email == "newuser", "Email should match username"
        print(f"✓ User 'newuser' created in database with hashed password")
        
        # Verify password was hashed correctly
        print("\n2c. Verifying password was hashed...")
        assert verify_password("securepassword123", user.hashed_password), "Password verification failed"
        print("✓ Password hashed and verifiable")
        
        # Test registration with duplicate user (should fail)
        print("\n2d. Testing duplicate registration (should fail)...")
        response = client.post(
            "/auth/register",
            json=registration_data
        )
        assert response.status_code == 409, f"Expected 409, got {response.status_code}"
        print("✓ Duplicate registration correctly rejected with 409")
        
        print("\n✓ FEATURE 2 PASSED: User registration working correctly!")
        
    finally:
        try:
            os.remove(temp_db_path)
        except:
            pass


def test_feature_3_authentication():
    """Test Feature 3: User Authentication (PUT /authenticate)"""
    print("\n" + "="*70)
    print("FEATURE 3: User Authentication - Login and Get JWT Token")
    print("="*70)
    
    client, db, temp_db_path = setup_test_db()
    
    try:
        # Create a test user
        print("\n3a. Creating test user...")
        test_user = User(
            id=1,
            username="authtest",
            email="authtest@example.com",
            hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",  # pre-hashed 'testpassword'
            is_admin=False
        )
        db.add(test_user)
        db.commit()
        print("✓ Test user created")
        
        # Test authentication with valid credentials
        print("\n3b. Testing authentication with valid credentials...")
        auth_data = {
            "user": {
                "name": "authtest",
                "is_admin": False
            },
            "secret": {
                "password": "testpassword"  # UPDATED: Use same password as pre-hashed value
            }
        }
        
        response = client.put(
            "/authenticate",
            json=auth_data
        )
        assert response.status_code == 200, f"Authentication failed: {response.text}"
        result = response.json()
        assert "token" in result, "Response should contain token"
        token = result["token"]
        assert token.startswith("bearer "), "Token should be in bearer format"
        print("✓ Authentication successful, bearer token returned")
        
        # Extract and verify token
        print("\n3c. Verifying JWT token...")
        token_without_bearer = token[7:]  # Remove "bearer " prefix
        from crud.upload.auth import decode_access_token
        payload = decode_access_token(token_without_bearer)
        assert payload.get("sub") == "1", "Token sub claim should be user ID"
        assert "exp" in payload, "Token should have expiration"
        print(f"✓ JWT token valid with claims: sub={payload.get('sub')}, exp={payload.get('exp')}")
        
        # Test authentication with wrong password
        print("\n3d. Testing authentication with invalid password...")
        wrong_auth_data = {
            "user": {
                "name": "authtest",
                "is_admin": False
            },
            "secret": {
                "password": "wrongpassword"
            }
        }
        
        response = client.put(
            "/authenticate",
            json=wrong_auth_data
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid password correctly rejected with 401")
        
        # Test authentication with nonexistent user
        print("\n3e. Testing authentication with nonexistent user...")
        nonexistent_auth_data = {
            "user": {
                "name": "nonexistent",
                "is_admin": False
            },
            "secret": {
                "password": "anypassword"
            }
        }
        
        response = client.put(
            "/authenticate",
            json=nonexistent_auth_data
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Nonexistent user correctly rejected with 401")
        
        print("\n✓ FEATURE 3 PASSED: User authentication working correctly!")
        
    finally:
        try:
            os.remove(temp_db_path)
        except:
            pass


def main():
    """Run all feature tests."""
    print("\n" + "🚀 "*35)
    print("COMPREHENSIVE FEATURE TEST SUITE".center(70))
    print("🚀 "*35)
    
    try:
        test_feature_1_enumerate()
        test_feature_2_registration()
        test_feature_3_authentication()
        
        print("\n" + "="*70)
        print("✓ ALL FEATURES PASSED SUCCESSFULLY!".center(70))
        print("="*70)
        print("\nImplementation Summary:")
        print("  1. ✓ Basic Enumerate: GET /api/models/enumerate works with pagination")
        print("  2. ✓ User Registration: POST /auth/register creates users with hashed passwords")
        print("  3. ✓ User Authentication: PUT /authenticate validates credentials and returns JWT")
        print("\nAll features implemented per OpenAPI specification!")
        print("="*70 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
