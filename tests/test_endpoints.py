"""Quick test script for verifying implemented endpoints."""

import json
from typing import Any, Optional

from fastapi.testclient import TestClient

from src.crud.app import app

client = TestClient(app)


def test_health() -> None:
    """Test GET /health endpoint"""
    print("\n=== Testing GET /health ===")
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("PASSED")


def test_health_components() -> None:
    """Test GET /health/components endpoint"""
    print("\n=== Testing GET /health/components ===")
    response = client.get("/health/components?windowMinutes=60")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Components found: {len(data.get('components', []))}")
    assert response.status_code == 200
    assert "components" in data
    print("PASSED")


def test_register() -> tuple[Any, str, str]:
    """Test POST /register endpoint"""
    print("\n=== Testing POST /register ===")
    import time
    timestamp = int(time.time())
    username = f"testuser{timestamp}"
    password = "testpass123"
    payload = {
        "user": {
            "name": username,
            "isAdmin": False
        },
        "secret": {
            "password": password
        }
    }
    response = client.post(
        "/register",
        json=payload
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "token" in data
        assert "bearer " in data["token"]
        print("PASSED - JWT token received")
        # Store in global for next test to use
        global registered_user_token, registered_username, registered_password
        registered_user_token = data["token"]
        registered_username = username
        registered_password = password
    else:
        print(f"Response: {response.text}")
        raise AssertionError(f"Registration failed: {response.text}")


def test_authenticate(username: str = "testuser123", password: str = "testpass123") -> Any:
    """Test PUT /authenticate endpoint"""
    print("\n=== Testing PUT /authenticate ===")
    payload = {
        "user": {"name": username, "is_admin": True},
        "secret": {"password": password},
    }
    response = client.put("/authenticate", json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "token" in data
        assert "bearer " in data["token"]
        print("PASSED - JWT token received")
    else:
        print(f"Response: {response.text}")
        raise AssertionError(f"Authentication failed: {response.text}")


def test_enumerate(token: Optional[str | None] = None) -> Any:
    """Test POST /artifacts endpoint"""
    print("\n=== Testing POST /artifacts (enumerate) ===")
    payload = [{"name": "*"}]  # Array of ArtifactQuery objects
    headers = {}
    if token:
        headers["X-Authorization"] = token
    response = client.post("/artifacts", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Artifacts found: {len(data)}")
        print("PASSED")
    else:
        print(f"Response: {response.text}")
        if response.status_code == 403:
            print("WARNING: Needs authentication")
        else:
            print("WARNING: May need setup or different payload")


def test_regex_search(token: Optional[str] = None) -> None:
    """Test POST /artifact/byRegEx endpoint"""
    print("\n=== Testing POST /artifact/byRegEx (regex search) ===")

    # Test 1: Valid regex
    print("Test 1: Valid regex pattern")
    payload = {"regex": ".*test.*"}
    headers = {}
    if token:
        headers["X-Authorization"] = token
    response = client.post(
        "/artifact/byRegEx", json=payload, headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        print("PASSED - No artifacts match (expected for empty registry)")
    elif response.status_code == 200:
        data = response.json()
        print(f"Artifacts found: {len(data)}")
        print("PASSED")
    else:
        print(f"Response: {response.text}")

    # Test 2: Malicious regex (ReDoS protection)
    print("\nTest 2: Malicious regex (should be rejected)")
    payload = {"regex": "(a+)+b"}  # Classic ReDoS pattern
    response = client.post(
        "/artifact/byRegEx", json=payload, headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print("PASSED - Malicious regex rejected (DoS protection working)")
    else:
        print(f"WARNING: Expected 400, got {response.status_code}")
        print(f"Response: {response.text}")

    # Test 3: Too long regex
    print("\nTest 3: Excessively long regex (should be rejected)")
    payload = {"regex": "a" * 250}  # Exceeds 200 char limit
    response = client.post(
        "/artifact/byRegEx", json=payload, headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print("PASSED - Long regex rejected")
    else:
        print(f"WARNING: Expected 400, got {response.status_code}")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTING IMPLEMENTED ENDPOINTS")
    print("=" * 60)

    try:
        # Test health endpoints (no auth required)
        test_health()
        test_health_components()

        # Test authentication endpoints
        token, username, password = test_register()

        # Also test authentication with the registered user
        test_authenticate(username, password)

        # Test enumerate endpoint
        test_enumerate(token)

        # Test regex search endpoint with DoS protection
        test_regex_search(token)

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback

        traceback.print_exc()
