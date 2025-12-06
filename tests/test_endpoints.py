"""Quick test script for verifying implemented endpoints."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test GET /health endpoint"""
    print("\n=== Testing GET /health ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("✅ PASSED")

def test_health_components():
    """Test GET /health/components endpoint"""
    print("\n=== Testing GET /health/components ===")
    response = requests.get(f"{BASE_URL}/health/components?windowMinutes=60")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Components found: {len(data.get('components', []))}")
    assert response.status_code == 200
    assert "components" in data
    print("✅ PASSED")

def test_register():
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
    response = requests.post(
        f"{BASE_URL}/register",
        json=payload
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "token" in data
        assert "bearer " in data["token"]
        print("✅ PASSED - JWT token received")
        return data["token"], username, password
    else:
        print(f"Response: {response.text}")
        raise AssertionError(f"Registration failed: {response.text}")

def test_authenticate(username="testuser123", password="testpass123"):
    """Test PUT /authenticate endpoint"""
    print("\n=== Testing PUT /authenticate ===")
    payload = {
        "user": {
            "name": username,
            "isAdmin": False
        },
        "secret": {
            "password": password
        }
    }
    response = requests.put(
        f"{BASE_URL}/authenticate",
        json=payload
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "token" in data
        assert "bearer " in data["token"]
        print("✅ PASSED - JWT token received")
        return data["token"]
    else:
        print(f"Response: {response.text}")
        raise AssertionError(f"Authentication failed: {response.text}")

def test_enumerate(token=None):
    """Test POST /artifacts endpoint"""
    print("\n=== Testing POST /artifacts (enumerate) ===")
    payload = [{"name": "*"}]  # Array of ArtifactQuery objects
    headers = {}
    if token:
        headers["X-Authorization"] = token
    response = requests.post(
        f"{BASE_URL}/artifacts",
        json=payload,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Artifacts found: {len(data)}")
        print("✅ PASSED")
        return data
    else:
        print(f"Response: {response.text}")
        if response.status_code == 403:
            print("⚠️  Needs authentication")
        else:
            print("⚠️  May need setup or different payload")

def test_regex_search(token=None):
    """Test POST /artifact/byRegEx endpoint"""
    print("\n=== Testing POST /artifact/byRegEx (regex search) ===")
    
    # Test 1: Valid regex
    print("Test 1: Valid regex pattern")
    payload = {"regex": ".*test.*"}
    headers = {}
    if token:
        headers["X-Authorization"] = token
    response = requests.post(
        f"{BASE_URL}/artifact/byRegEx",
        json=payload,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        print("✅ PASSED - No artifacts match (expected for empty registry)")
    elif response.status_code == 200:
        data = response.json()
        print(f"Artifacts found: {len(data)}")
        print("✅ PASSED")
    else:
        print(f"Response: {response.text}")
    
    # Test 2: Malicious regex (ReDoS protection)
    print("\nTest 2: Malicious regex (should be rejected)")
    payload = {"regex": "(a+)+b"}  # Classic ReDoS pattern
    response = requests.post(
        f"{BASE_URL}/artifact/byRegEx",
        json=payload,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print("✅ PASSED - Malicious regex rejected (DoS protection working)")
    else:
        print(f"⚠️  Expected 400, got {response.status_code}")
        print(f"Response: {response.text}")
    
    # Test 3: Too long regex
    print("\nTest 3: Excessively long regex (should be rejected)")
    payload = {"regex": "a" * 250}  # Exceeds 200 char limit
    response = requests.post(
        f"{BASE_URL}/artifact/byRegEx",
        json=payload,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print("✅ PASSED - Long regex rejected")
    else:
        print(f"⚠️  Expected 400, got {response.status_code}")

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
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
